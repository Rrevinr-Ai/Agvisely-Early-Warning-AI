import json
import re
from pathlib import Path

from openai import OpenAI

from app.config import settings
from app.services.agvisely_service import agvisely_service
from app.services.dialog_service import (
    detect_intent,
    load_dialog_state,
    recent_conversation_snippets,
    update_dialog_state_from_turn,
    upsert_dialog_state_message,
)
from app.services.disease_service import get_wheat_disease_advisory
from app.services.excel_advisory_service import (
    detect_crop_from_text,
    detect_stage_from_text,
    excel_advisory_service,
)
from app.services.location_service import resolve_location
from app.services.speak_service import speak_service


AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Fetch location-specific weather forecast. Use district and upazila from farmer context.",
            "parameters": {
                "type": "object",
                "properties": {
                    "district": {"type": "string"},
                    "upazila": {"type": "string"},
                    "latitude": {"type": "number"},
                    "longitude": {"type": "number"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_crop_advisory",
            "description": (
                "Fetch crop advisory for the farmer's crop and growth stage. "
                "Uses Excel stage/weather rules first (e.g. Aman rice কুশি/থোড়), "
                "then GPT fallback if no Excel match. "
                "ALWAYS call this when the farmer names a crop or stage, or asks what to do in the field."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "crop": {
                        "type": "string",
                        "description": "Crop name e.g. aman rice, rice, wheat, maize",
                    },
                    "stage": {
                        "type": "string",
                        "description": (
                            "Growth stage from farmer speech if mentioned. "
                            "Examples: Maximum Tillering Stage, Booting Stage, কুশি, কষি, কুষি, থোড়"
                        ),
                    },
                    "district": {"type": "string"},
                    "upazila": {"type": "string"},
                    "latitude": {"type": "number"},
                    "longitude": {"type": "number"},
                },
                "required": ["crop"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_wheat_disease_forecast",
            "description": "Fetch pre-season wheat disease forecast (static advisory).",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


def _needs_crop_advisory(user_message: str) -> bool:
    text = user_message or ""
    markers = (
        "ধান",
        "আমন",
        "ফসল",
        "পর্যায়",
        "পর্যায়",
        "কুশি",
        "কষি",
        "কুষি",
        "থোড়",
        "থোড়",
        "কী করতে",
        "কি করতে",
        "করতে হবে",
        "পরামর্শ",
        "পেস্টিসাইড",
        "বালাইনাশক",
        "কীটনাশক",
        "লক্ষণ",
        "চাষ",
        "মাটি",
        "টাকা",
        "rice",
        "crop",
        "tillering",
        "booting",
        "pesticide",
    )
    return any(m in text or m in text.lower() for m in markers)


def _wants_weather(user_message: str) -> bool:
    text = user_message or ""
    lowered = text.lower()
    markers = (
        "আবহাওয়া",
        "আবহাওয়া",
        "আবহাও",
        "আবাস",
        "বৃষ্টি",
        "তাপমাত্রা",
        "weather",
        "rain",
        "ইউকে",
    )
    return any(m in text or m in lowered for m in markers)


class CallAgentService:
    def __init__(self) -> None:
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
        self.model = settings.LLM_MODEL
        self.system_prompt = self._load_system_prompt()

    def _load_system_prompt(self) -> str:
        path = Path(settings.SYSTEM_PROMPT_PATH)
        if path.exists():
            return path.read_text(encoding="utf-8").strip()
        return "You are a Bangla agricultural call agent for Bangladeshi farmers."

    def _enrich_context_from_message(self, user_message: str, farmer_context: dict) -> None:
        stage = detect_stage_from_text(user_message)
        if stage:
            farmer_context["crop_stage"] = stage
        crop = detect_crop_from_text(user_message)
        if crop:
            farmer_context["preferred_crop"] = crop

    def _recover_stage_from_messages(self, messages: list[dict], farmer_context: dict) -> None:
        if farmer_context.get("crop_stage"):
            return
        state = load_dialog_state(messages)
        if state.get("stage"):
            farmer_context["crop_stage"] = state["stage"]
            if state.get("crop"):
                farmer_context["preferred_crop"] = state["crop"]
            return
        for message in reversed(messages or []):
            content = str(message.get("content") or "")
            if "Excel fast-path used." in content and "stage=" in content:
                match = re.search(r"stage=(.+?)(?:\s+stage_bn=|$)", content)
                if match:
                    farmer_context["crop_stage"] = match.group(1).strip()
                    return
            stage = detect_stage_from_text(content)
            if stage:
                farmer_context["crop_stage"] = stage
                return

    async def _excel_fast_path(
        self,
        user_message: str,
        messages: list[dict],
        farmer_context: dict,
        dialog_state: dict,
        intent: str,
    ) -> tuple[str, list[dict], str] | None:
        """Excel retrieve → filter by dialog → speak LLM (or template)."""
        if not settings.EXCEL_FAST_PATH or not settings.EXCEL_ADVISORY_ENABLED:
            return None

        # Pure weather without crop context → let main agent / weather tool handle
        if intent == "weather" and not (
            dialog_state.get("crop") or dialog_state.get("stage") or _needs_crop_advisory(user_message)
        ):
            return None

        if intent not in {
            "general_crop",
            "more_advice",
            "constraint",
            "pest",
            "weather_crop",
        } and not _needs_crop_advisory(user_message):
            return None

        crop = (
            farmer_context.get("preferred_crop")
            or dialog_state.get("crop")
            or detect_crop_from_text(user_message)
        )
        stage = (
            farmer_context.get("crop_stage")
            or dialog_state.get("stage")
            or detect_stage_from_text(user_message)
        )
        if not crop and not stage:
            return None
        if not crop:
            crop = "aman rice"

        advisory = await agvisely_service.get_crop_advisory(
            crop=crop,
            district=farmer_context.get("district"),
            upazila=farmer_context.get("upazila"),
            latitude=farmer_context.get("latitude"),
            longitude=farmer_context.get("longitude"),
            stage=stage,
            include_weather=False,
        )
        if advisory.get("source") != "excel":
            return None

        constraints = list(dialog_state.get("farmer_constraints") or [])
        said_ids = list(dialog_state.get("said_bullet_ids") or [])
        filter_intent = intent if intent != "weather_crop" else "weather_crop"
        max_bullets = 3 if intent in {"weather", "weather_crop"} else 6

        picked = excel_advisory_service.select_bullets_for_dialog(
            advisory,
            intent=filter_intent,
            constraints=constraints,
            said_bullet_ids=said_ids,
            max_bullets=max_bullets,
        )

        weather_summary = None
        if intent in {"weather", "weather_crop"} or _wants_weather(user_message):
            weather = await agvisely_service.get_weather(
                latitude=farmer_context.get("latitude"),
                longitude=farmer_context.get("longitude"),
                district=farmer_context.get("district"),
                upazila=farmer_context.get("upazila"),
            )
            weather_summary = (
                weather.get("agent_speech")
                or weather.get("summary")
                or weather.get("weather_condition")
                or ""
            )
            if weather.get("temperature"):
                weather_summary = (
                    f"তাপমাত্রা {weather.get('temperature')}. " + (weather_summary or "")
                ).strip()

        location = resolve_location(
            district=farmer_context.get("district"),
            upazila=farmer_context.get("upazila"),
            latitude=farmer_context.get("latitude"),
            longitude=farmer_context.get("longitude"),
        )
        recent = recent_conversation_snippets(messages, limit=6)

        speech = speak_service.speak(
            user_message=user_message,
            intent=intent,
            constraints=constraints,
            crop=advisory.get("crop_bn") or crop,
            stage=advisory.get("stage_bn") or stage or "",
            bullets=picked,
            recent=recent,
            weather_summary=weather_summary,
            location_label=location.get("label"),
        )
        used_ids = [b["id"] for b in picked]
        if not speech:
            speech, used_ids = excel_advisory_service.compose_spoken_advisory(
                advisory,
                user_message=user_message,
                intent=filter_intent,
                constraints=constraints,
                said_bullet_ids=said_ids,
                max_bullets=max_bullets,
            )
            if weather_summary and intent in {"weather", "weather_crop"}:
                speech = weather_summary.strip()[:220] + " " + speech

        # Safety net: constraint answers must not push soil testing
        if "no_money_for_soil_test" in constraints:
            if "মাটি পরীক্ষা" in speech and "ছাড়া" not in speech and "ছাড়া" not in speech:
                speech, used_ids = excel_advisory_service.compose_spoken_advisory(
                    advisory,
                    user_message=user_message,
                    intent="constraint",
                    constraints=constraints,
                    said_bullet_ids=[],  # allow alts again
                    max_bullets=5,
                )

        # Update dialog memory
        dialog_state["crop"] = advisory.get("crop") or crop
        dialog_state["stage"] = advisory.get("stage") or stage
        dialog_state["district"] = farmer_context.get("district")
        dialog_state["upazila"] = farmer_context.get("upazila")
        merged_ids = list(dict.fromkeys(said_ids + used_ids))
        dialog_state["said_bullet_ids"] = merged_ids[-40:]
        dialog_state["last_intent"] = intent
        upsert_dialog_state_message(messages, dialog_state)

        messages.append({"role": "assistant", "content": speech})
        messages.append(
            {
                "role": "system",
                "content": (
                    "Excel fast-path used. "
                    f"crop={advisory.get('crop')} stage={advisory.get('stage')} "
                    f"stage_bn={advisory.get('stage_bn')} intent={intent}"
                ),
            }
        )
        out_intent = "weather" if intent == "weather" else "advisory"
        return speech, messages, out_intent

    def _build_context_message(self, farmer_context: dict) -> str:
        source = farmer_context.get("location_source", "profile")
        priority = (
            " The farmer stated this location in their message — ALWAYS use it for weather/advisory tools, "
            "not any old profile default."
            if source == "message"
            else ""
        )
        payload = {
            "district": farmer_context.get("district"),
            "upazila": farmer_context.get("upazila"),
            "latitude": farmer_context.get("latitude"),
            "longitude": farmer_context.get("longitude"),
            "preferred_crop": farmer_context.get("preferred_crop"),
            "crop_stage": farmer_context.get("crop_stage"),
        }
        stage_note = ""
        if payload.get("crop_stage"):
            stage_note = (
                f" Farmer stated growth stage={payload['crop_stage']}. "
                "Pass this as stage to get_crop_advisory. Do NOT invent harvest or other crops."
            )
        return (
            f"Known farmer context:{priority}{stage_note} "
            f"{json.dumps(payload, ensure_ascii=False)}"
        )

    async def _execute_tool(self, name: str, arguments: dict, farmer_context: dict) -> dict:
        district = arguments.get("district") or farmer_context.get("district")
        upazila = arguments.get("upazila") or farmer_context.get("upazila")
        latitude = arguments.get("latitude") or farmer_context.get("latitude")
        longitude = arguments.get("longitude") or farmer_context.get("longitude")

        if name == "get_weather":
            return await agvisely_service.get_weather(
                latitude=latitude,
                longitude=longitude,
                district=district,
                upazila=upazila,
            )

        if name == "get_crop_advisory":
            crop = (
                arguments.get("crop")
                or farmer_context.get("preferred_crop")
                or "aman rice"
            )
            stage = arguments.get("stage") or farmer_context.get("crop_stage")
            return await agvisely_service.get_crop_advisory(
                crop=crop,
                latitude=latitude,
                longitude=longitude,
                district=district,
                upazila=upazila,
                stage=stage,
            )

        if name == "get_wheat_disease_forecast":
            return get_wheat_disease_advisory()

        return {"error": f"Unknown tool: {name}"}

    def _sync_farmer_context(self, messages: list[dict], farmer_context: dict) -> None:
        context_message = {
            "role": "system",
            "content": self._build_context_message(farmer_context),
        }
        for index, message in enumerate(messages):
            if message.get("role") == "system" and str(message.get("content", "")).startswith(
                "Known farmer context:"
            ):
                messages[index] = context_message
                return

        insert_at = 1 if messages and messages[0].get("role") == "system" else 0
        messages.insert(insert_at, context_message)

    async def handle_turn(
        self,
        user_message: str,
        messages: list[dict],
        farmer_context: dict,
    ) -> tuple[str, list[dict], str]:
        if not self.client:
            raise ValueError("OPENAI_API_KEY is not configured")

        self._enrich_context_from_message(user_message, farmer_context)

        if not messages:
            messages = [{"role": "system", "content": self.system_prompt}]
        else:
            self._recover_stage_from_messages(messages, farmer_context)

        dialog_state = load_dialog_state(messages)
        intent = detect_intent(user_message)
        dialog_state = update_dialog_state_from_turn(
            dialog_state, user_message, farmer_context, intent
        )

        self._sync_farmer_context(messages, farmer_context)
        messages.append({"role": "user", "content": user_message})

        # Conversation-aware Excel path (filter + speak).
        fast = await self._excel_fast_path(
            user_message, messages, farmer_context, dialog_state, intent
        )
        if fast is not None:
            return fast

        for _ in range(5):
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=AGENT_TOOLS,
                tool_choice="auto",
                temperature=0.3,
            )
            assistant_message = response.choices[0].message

            if assistant_message.tool_calls:
                messages.append(
                    {
                        "role": "assistant",
                        "content": assistant_message.content,
                        "tool_calls": [
                            {
                                "id": tool_call.id,
                                "type": "function",
                                "function": {
                                    "name": tool_call.function.name,
                                    "arguments": tool_call.function.arguments,
                                },
                            }
                            for tool_call in assistant_message.tool_calls
                        ],
                    }
                )

                tool_results: list[dict] = []
                called_names = []
                for tool_call in assistant_message.tool_calls:
                    args = json.loads(tool_call.function.arguments or "{}")
                    result = await self._execute_tool(
                        tool_call.function.name,
                        args,
                        farmer_context,
                    )
                    called_names.append(tool_call.function.name)
                    tool_results.append(result)
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(result, ensure_ascii=False),
                        }
                    )

                if (
                    _needs_crop_advisory(user_message)
                    and "get_crop_advisory" not in called_names
                ):
                    advisory = await self._execute_tool(
                        "get_crop_advisory",
                        {
                            "crop": farmer_context.get("preferred_crop") or "aman rice",
                            "stage": farmer_context.get("crop_stage"),
                        },
                        farmer_context,
                    )
                    tool_results.append(advisory)
                    messages.append(
                        {
                            "role": "system",
                            "content": (
                                "Extra crop advisory (auto-fetched because farmer named crop/stage "
                                "or asked what to do). Prefer source=excel. "
                                f"{json.dumps(advisory, ensure_ascii=False)}"
                            ),
                        }
                    )

                if len(tool_results) == 1:
                    only = tool_results[0]
                    speech = (only.get("agent_speech") or "").strip()
                    if (
                        only.get("source") == "gpt_backup"
                        and called_names == ["get_crop_advisory"]
                        and speech
                    ):
                        messages.append({"role": "assistant", "content": speech})
                        upsert_dialog_state_message(messages, dialog_state)
                        return speech, messages, self._detect_intent(user_message, messages)

                continue

            answer = (assistant_message.content or "").strip()
            messages.append({"role": "assistant", "content": answer})
            upsert_dialog_state_message(messages, dialog_state)
            return answer, messages, self._detect_intent(user_message, messages)

        fallback = "দুঃখিত, আমি এখন উত্তর দিতে পারছি না। একটু পরে আবার চেষ্টা করুন।"
        messages.append({"role": "assistant", "content": fallback})
        return fallback, messages, "error"

    def _detect_intent(self, user_message: str, messages: list[dict]) -> str:
        dialog_intent = detect_intent(user_message)
        if dialog_intent in {"weather", "weather_crop"}:
            return "weather"
        if dialog_intent == "pest" and "গম" in (user_message or ""):
            return "disease"

        tool_names = []
        for message in messages:
            for tool_call in message.get("tool_calls") or []:
                tool_names.append(tool_call["function"]["name"])

        if "get_wheat_disease_forecast" in tool_names or (
            "গম" in (user_message or "") and "রোগ" in (user_message or "")
        ):
            return "disease"
        if "get_crop_advisory" in tool_names or _needs_crop_advisory(user_message):
            return "advisory"
        if "get_weather" in tool_names or _wants_weather(user_message):
            return "weather"
        return "conversation"


call_agent_service = CallAgentService()
