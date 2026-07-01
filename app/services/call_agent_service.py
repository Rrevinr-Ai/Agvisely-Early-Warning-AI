import json
from pathlib import Path

from openai import OpenAI

from app.config import settings
from app.services.agvisely_service import agvisely_service
from app.services.disease_service import get_wheat_disease_advisory


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
            "description": "Fetch crop advisory from Agvisely for a specific crop and location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "crop": {"type": "string", "description": "Crop name e.g. rice, wheat, maize"},
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
        }
        return f"Known farmer context:{priority} {json.dumps(payload, ensure_ascii=False)}"

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
            crop = arguments.get("crop") or farmer_context.get("preferred_crop") or "rice"
            return await agvisely_service.get_crop_advisory(
                crop=crop,
                latitude=latitude,
                longitude=longitude,
                district=district,
                upazila=upazila,
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

        if not messages:
            messages = [{"role": "system", "content": self.system_prompt}]

        self._sync_farmer_context(messages, farmer_context)
        messages.append({"role": "user", "content": user_message})

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
                for tool_call in assistant_message.tool_calls:
                    args = json.loads(tool_call.function.arguments or "{}")
                    result = await self._execute_tool(
                        tool_call.function.name,
                        args,
                        farmer_context,
                    )
                    tool_results.append(result)
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(result, ensure_ascii=False),
                        }
                    )

                # GPT backup already returns spoken Bangla — skip a second LLM round trip.
                if len(tool_results) == 1:
                    speech = (tool_results[0].get("agent_speech") or "").strip()
                    if tool_results[0].get("source") == "gpt_backup" and speech:
                        messages.append({"role": "assistant", "content": speech})
                        intent = self._detect_intent(user_message, messages)
                        return speech, messages, intent

                continue

            answer = (assistant_message.content or "").strip()
            messages.append({"role": "assistant", "content": answer})
            intent = self._detect_intent(user_message, messages)
            return answer, messages, intent

        fallback = "দুঃখিত, আমি এখন উত্তর দিতে পারছি না। একটু পরে আবার চেষ্টা করুন।"
        messages.append({"role": "assistant", "content": fallback})
        return fallback, messages, "error"

    def _detect_intent(self, user_message: str, messages: list[dict]) -> str:
        lowered = user_message.lower()
        tool_names = []
        for message in messages:
            for tool_call in message.get("tool_calls") or []:
                tool_names.append(tool_call["function"]["name"])

        if "get_wheat_disease_forecast" in tool_names or any(
            word in lowered for word in ("রোগ", "disease", "গম")
        ):
            return "disease"
        if "get_weather" in tool_names or any(
            word in lowered for word in ("আবহাওয়া", "weather", "বৃষ্টি", "rain")
        ):
            return "weather"
        if "get_crop_advisory" in tool_names:
            return "advisory"
        return "conversation"


call_agent_service = CallAgentService()
