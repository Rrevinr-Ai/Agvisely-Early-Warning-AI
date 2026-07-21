"""Interview / pilot demo forecasts by location (CIMMYT scenario numbers)."""

from __future__ import annotations

import re
import unicodedata
from typing import Optional


def _norm(text: str) -> str:
    cleaned = unicodedata.normalize("NFKC", (text or "").strip().lower())
    return re.sub(r"[^\w\u0980-\u09FF\-]", "", cleaned)


# CIMMYT interview Scenario 1 numbers
DEMO_FORECASTS: dict[str, dict] = {
    # Babuganj: 44 mm/day rain, temp exceeds 35°C next 5 days
    "babuganj": {
        "upazila": "Babuganj",
        "district": "Barishal",
        "temperature_c": 36.0,
        "rainfall_mm": 44.0,
        "temperature": "৩৫°সে এর উপরে",
        "rainfall_outlook": "প্রতিদিন প্রায় ৪৪ মিমি বৃষ্টি (ভারী)",
        "weather_condition": "আগামী পাঁচ দিনে উচ্চ তাপমাত্রা ও ভারী বৃষ্টির সম্ভাবনা",
        "default_stage": "Booting Stage",
        "agent_speech": (
            "বাবুগঞ্জে আগামী পাঁচ দিনে তাপমাত্রা ৩৫ ডিগ্রি সেলসিয়াসের উপরে থাকতে পারে "
            "এবং দৈনিক প্রায় ৪৪ মিলিমিটার ভারী বৃষ্টির সম্ভাবনা রয়েছে।"
        ),
    },
    "বাবুগঞ্জ": {
        "upazila": "Babuganj",
        "district": "Barishal",
        "temperature_c": 36.0,
        "rainfall_mm": 44.0,
        "temperature": "৩৫°সে এর উপরে",
        "rainfall_outlook": "প্রতিদিন প্রায় ৪৪ মিমি বৃষ্টি (ভারী)",
        "weather_condition": "আগামী পাঁচ দিনে উচ্চ তাপমাত্রা ও ভারী বৃষ্টির সম্ভাবনা",
        "default_stage": "Booting Stage",
        "agent_speech": (
            "বাবুগঞ্জে আগামী পাঁচ দিনে তাপমাত্রা ৩৫ ডিগ্রি সেলসিয়াসের উপরে থাকতে পারে "
            "এবং দৈনিক প্রায় ৪৪ মিলিমিটার ভারী বৃষ্টির সম্ভাবনা রয়েছে।"
        ),
    },
    # Rangpur Sadar: 10 mm/day next 5 days
    "rangpursadar": {
        "upazila": "Rangpur Sadar",
        "district": "Rangpur",
        "temperature_c": 32.0,
        "rainfall_mm": 10.0,
        "temperature": "৩০-৩৩°সে",
        "rainfall_outlook": "প্রতিদিন প্রায় ১০ মিমি হালকা থেকে মাঝারি বৃষ্টি",
        "weather_condition": "আগামী পাঁচ দিনে হালকা বৃষ্টির সম্ভাবনা",
        "default_stage": "Maximum Tillering Stage",
        "agent_speech": (
            "রংপুর সদরে আগামী পাঁচ দিনে দৈনিক প্রায় ১০ মিলিমিটার বৃষ্টির সম্ভাবনা রয়েছে।"
        ),
    },
    "rangpur": {
        "upazila": "Rangpur Sadar",
        "district": "Rangpur",
        "temperature_c": 32.0,
        "rainfall_mm": 10.0,
        "temperature": "৩০-৩৩°সে",
        "rainfall_outlook": "প্রতিদিন প্রায় ১০ মিমি হালকা থেকে মাঝারি বৃষ্টি",
        "weather_condition": "আগামী পাঁচ দিনে হালকা বৃষ্টির সম্ভাবনা",
        "default_stage": "Maximum Tillering Stage",
        "agent_speech": (
            "রংপুরে আগামী পাঁচ দিনে দৈনিক প্রায় ১০ মিলিমিটার বৃষ্টির সম্ভাবনা রয়েছে।"
        ),
    },
    "রংপুর": {
        "upazila": "Rangpur Sadar",
        "district": "Rangpur",
        "temperature_c": 32.0,
        "rainfall_mm": 10.0,
        "temperature": "৩০-৩৩°সে",
        "rainfall_outlook": "প্রতিদিন প্রায় ১০ মিমি হালকা থেকে মাঝারি বৃষ্টি",
        "weather_condition": "আগামী পাঁচ দিনে হালকা বৃষ্টির সম্ভাবনা",
        "default_stage": "Maximum Tillering Stage",
        "agent_speech": (
            "রংপুরে আগামী পাঁচ দিনে দৈনিক প্রায় ১০ মিলিমিটার বৃষ্টির সম্ভাবনা রয়েছে।"
        ),
    },
    "রংপুরসদর": {
        "upazila": "Rangpur Sadar",
        "district": "Rangpur",
        "temperature_c": 32.0,
        "rainfall_mm": 10.0,
        "temperature": "৩০-৩৩°সে",
        "rainfall_outlook": "প্রতিদিন প্রায় ১০ মিমি হালকা থেকে মাঝারি বৃষ্টি",
        "weather_condition": "আগামী পাঁচ দিনে হালকা বৃষ্টির সম্ভাবনা",
        "default_stage": "Maximum Tillering Stage",
        "agent_speech": (
            "রংপুর সদরে আগামী পাঁচ দিনে দৈনিক প্রায় ১০ মিলিমিটার বৃষ্টির সম্ভাবনা রয়েছে।"
        ),
    },
}


def lookup_demo_forecast(
    district: Optional[str] = None,
    upazila: Optional[str] = None,
) -> Optional[dict]:
    """Return demo forecast dict if location matches interview scenarios."""
    candidates = []
    for part in (upazila, district):
        if not part:
            continue
        key = _norm(part)
        candidates.append(key)
        # also try without spaces already handled by _norm
        if key in DEMO_FORECASTS:
            data = dict(DEMO_FORECASTS[key])
            return _as_weather_payload(data, district=district, upazila=upazila)

    # fuzzy contains
    blob = _norm(f"{upazila or ''}{district or ''}")
    for key, data in DEMO_FORECASTS.items():
        if key in blob or blob in key:
            return _as_weather_payload(dict(data), district=district, upazila=upazila)
    return None


def default_stage_for_location(
    district: Optional[str] = None,
    upazila: Optional[str] = None,
) -> Optional[str]:
    forecast = lookup_demo_forecast(district=district, upazila=upazila)
    if not forecast:
        return None
    return forecast.get("default_stage")


def _as_weather_payload(
    data: dict,
    district: Optional[str],
    upazila: Optional[str],
) -> dict:
    return {
        "source": "demo_forecast",
        "district": district or data.get("district"),
        "upazila": upazila or data.get("upazila"),
        "temperature_c": data["temperature_c"],
        "rainfall_mm": data["rainfall_mm"],
        "temperature": data.get("temperature", ""),
        "rainfall_outlook": data.get("rainfall_outlook", ""),
        "weather_condition": data.get("weather_condition", ""),
        "default_stage": data.get("default_stage"),
        "agent_speech": data.get("agent_speech", ""),
        "summary": data.get("agent_speech", ""),
        "disclaimer": "এটি CIMMYT interview/demo পূর্বাভাস সংখ্যা (Excel মিলানোর জন্য)।",
    }
