"""Conversation dialog state + rule-based intent for advisory fast path."""

from __future__ import annotations

import json
from typing import Any, Optional

from app.services.excel_advisory_service import detect_crop_from_text, detect_stage_from_text
from app.services.location_service import extract_location_from_message

DIALOG_STATE_PREFIX = "DialogState:"

WEATHER_MARKERS = (
    "আবহাওয়া",
    "আবহাওয়া",
    "আবহাও",
    "আবাস",  # STT garble
    "আবহাওয়ার",
    "বৃষ্টি",
    "তাপমাত্রা",
    "weather",
    "weather advisory",
    "rain",
    "rainfall",
    "ইউকে",  # STT garble for আবহাওয়া-ish
)

MORE_MARKERS = (
    "এছাড়া",
    "এছাড়া",
    "আরও",
    "অতিরিক্ত",
    "আরো",
    "আর কোনো",
    "আর কিছু",
    "অন্য কিছু",
    "অন্যান্য",
    "other information",
    "any other",
    "more information",
    "more advice",
)

PEST_MARKERS = (
    "পেস্টিসাইড",
    "বালাইনাশক",
    "কীটনাশক",
    "পোকা",
    "রোগ",
    "লক্ষণ",
    "মাজরা",
    "ফড়িং",
    "ফড়িং",
    "pesticide",
)

SOIL_COST_MARKERS = (
    "মাটি পরীক্ষা",
    "মাটি পরীক্ষ",
    "টাকা নেই",
    "টাকা নাই",
    "টাকা লাগে",
    "টাকা সাথে",
    "ব্যয়",
    "খরচ",
    "পারব না",
    "পারছি না",
    "কিনতে পার",
    "টাকা নেই",
    "বেলে না",  # STT: বলে না / পারে না
)


def empty_dialog_state() -> dict[str, Any]:
    return {
        "crop": None,
        "stage": None,
        "district": None,
        "upazila": None,
        "said_bullet_ids": [],
        "farmer_constraints": [],
        "last_intent": None,
    }


def load_dialog_state(messages: list[dict]) -> dict[str, Any]:
    state = empty_dialog_state()
    for message in reversed(messages or []):
        content = str(message.get("content") or "")
        if content.startswith(DIALOG_STATE_PREFIX):
            raw = content[len(DIALOG_STATE_PREFIX) :].strip()
            try:
                loaded = json.loads(raw)
                if isinstance(loaded, dict):
                    state.update({k: loaded.get(k, state.get(k)) for k in state})
                    state["said_bullet_ids"] = list(loaded.get("said_bullet_ids") or [])
                    state["farmer_constraints"] = list(loaded.get("farmer_constraints") or [])
                    return state
            except json.JSONDecodeError:
                continue
    return state


def dump_dialog_state_message(state: dict[str, Any]) -> dict:
    payload = {
        "crop": state.get("crop"),
        "stage": state.get("stage"),
        "district": state.get("district"),
        "upazila": state.get("upazila"),
        "said_bullet_ids": list(state.get("said_bullet_ids") or [])[-40:],
        "farmer_constraints": list(state.get("farmer_constraints") or []),
        "last_intent": state.get("last_intent"),
    }
    return {
        "role": "system",
        "content": DIALOG_STATE_PREFIX + " " + json.dumps(payload, ensure_ascii=False),
    }


def upsert_dialog_state_message(messages: list[dict], state: dict[str, Any]) -> None:
    content = dump_dialog_state_message(state)
    for index, message in enumerate(messages):
        if str(message.get("content") or "").startswith(DIALOG_STATE_PREFIX):
            messages[index] = content
            return
    messages.append(content)


def detect_intent(user_message: str) -> str:
    text = user_message or ""
    lowered = text.lower()

    if any(m in text or m in lowered for m in WEATHER_MARKERS):
        # Mixed weather + crop care
        if any(
            m in text or m in lowered
            for m in (
                "ধান",
                "আমন",
                "rice",
                "farmer",
                "করণীয়",
                "করতে",
                "পরামর্শ",
                "কুশি",
                "কষি",
                "advisory",
            )
        ):
            return "weather_crop"
        return "weather"

    if any(m in text or m in lowered for m in PEST_MARKERS):
        return "pest"

    if any(m in text for m in SOIL_COST_MARKERS) or (
        "মাটি" in text and any(x in text for x in ("টাকা", "খরচ", "পার"))
    ):
        return "constraint"

    if any(m in text for m in MORE_MARKERS):
        return "more_advice"

    if any(
        m in text
        for m in (
            "ধান",
            "আমন",
            "পাট",
            "পাঠ",
            "জুট",
            "পরামর্শ",
            "করতে",
            "করণীয়",
            "কুশি",
            "কষি",
            "কুষি",
            "ফসল",
            "চাষ",
        )
    ):
        return "general_crop"

    return "conversation"


def extract_constraints(user_message: str, existing: Optional[list[str]] = None) -> list[str]:
    constraints = list(existing or [])
    text = user_message or ""
    if any(m in text for m in SOIL_COST_MARKERS) or (
        "মাটি" in text and any(x in text for x in ("টাকা", "খরচ", "পার", "লাগে"))
    ):
        if "no_money_for_soil_test" not in constraints:
            constraints.append("no_money_for_soil_test")
    return constraints


def update_dialog_state_from_turn(
    state: dict[str, Any],
    user_message: str,
    farmer_context: dict,
    intent: str,
) -> dict[str, Any]:
    state = dict(state)
    state.setdefault("said_bullet_ids", [])
    state.setdefault("farmer_constraints", [])

    stage = detect_stage_from_text(user_message)
    if stage:
        state["stage"] = stage

    crop = detect_crop_from_text(user_message)
    if crop:
        state["crop"] = crop
        # পাট/পাঠ must not inherit rice কুশি/থোড় from form/session
        if crop == "jute" and not stage:
            if state.get("stage") in {"Maximum Tillering Stage", "Booting Stage"}:
                state["stage"] = None
            farmer_context.pop("crop_stage", None)
    elif farmer_context.get("preferred_crop"):
        state["crop"] = farmer_context.get("preferred_crop")

    if (
        not state.get("stage")
        and farmer_context.get("crop_stage")
        and state.get("crop") not in {"jute"}
    ):
        state["stage"] = farmer_context.get("crop_stage")

    spoken = extract_location_from_message(user_message)
    if spoken.get("district"):
        state["district"] = spoken["district"]
        farmer_context["district"] = spoken["district"]
        farmer_context["location_source"] = "message"
    if spoken.get("upazila"):
        state["upazila"] = spoken["upazila"]
        farmer_context["upazila"] = spoken["upazila"]
        farmer_context["location_source"] = "message"

    # Prefer dialog location into farmer_context when form is empty/stale
    if state.get("district"):
        farmer_context["district"] = state["district"]
    if state.get("upazila"):
        farmer_context["upazila"] = state["upazila"]
    if state.get("crop"):
        farmer_context["preferred_crop"] = state["crop"]
    if state.get("stage"):
        farmer_context["crop_stage"] = state["stage"]

    state["farmer_constraints"] = extract_constraints(
        user_message, state.get("farmer_constraints")
    )
    state["last_intent"] = intent
    return state


def recent_conversation_snippets(messages: list[dict], limit: int = 6) -> list[dict]:
    """Last user/assistant turns for speak LLM context."""
    snippets = []
    for message in messages or []:
        role = message.get("role")
        if role not in {"user", "assistant"}:
            continue
        content = str(message.get("content") or "").strip()
        if not content:
            continue
        snippets.append({"role": role, "content": content[:500]})
    return snippets[-limit:]
