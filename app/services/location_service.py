import re
import unicodedata
from typing import Optional

# Alias -> {district, upazila} — extend as needed for pilot areas.
KNOWN_PLACES: dict[str, dict[str, str]] = {
    "modhukhali": {"upazila": "Modhukhali", "district": "Faridpur"},
    "madhukhali": {"upazila": "Modhukhali", "district": "Faridpur"},
    "modukhali": {"upazila": "Modhukhali", "district": "Faridpur"},
    "মধুখালি": {"upazila": "Modhukhali", "district": "Faridpur"},
    "মদুখালি": {"upazila": "Modhukhali", "district": "Faridpur"},
    "faridpur": {"district": "Faridpur"},
    "ফরিদপুর": {"district": "Faridpur"},
    "dhaka": {"district": "Dhaka"},
    "ঢাকা": {"district": "Dhaka"},
    "netrokona": {"district": "Netrokona"},
    "নেত্রকোনা": {"district": "Netrokona"},
    "mymensingh": {"district": "Mymensingh"},
    "ময়মনসিংহ": {"district": "Mymensingh"},
    "sylhet": {"district": "Sylhet"},
    "সিলেট": {"district": "Sylhet"},
    "rajshahi": {"district": "Rajshahi"},
    "রাজশাহী": {"district": "Rajshahi"},
    "khulna": {"district": "Khulna"},
    "খুলনা": {"district": "Khulna"},
    "barishal": {"district": "Barishal"},
    "barisal": {"district": "Barishal"},
    "বরিশাল": {"district": "Barishal"},
    "rangpur": {"district": "Rangpur", "upazila": "Rangpur Sadar"},
    "রংপুর": {"district": "Rangpur", "upazila": "Rangpur Sadar"},
    "rangpur sadar": {"district": "Rangpur", "upazila": "Rangpur Sadar"},
    "rangpursadar": {"district": "Rangpur", "upazila": "Rangpur Sadar"},
    "রংপুর সদর": {"district": "Rangpur", "upazila": "Rangpur Sadar"},
    "রংপুরসদর": {"district": "Rangpur", "upazila": "Rangpur Sadar"},
    "babuganj": {"upazila": "Babuganj", "district": "Barishal"},
    "babugunj": {"upazila": "Babuganj", "district": "Barishal"},
    "বাবুগঞ্জ": {"upazila": "Babuganj", "district": "Barishal"},
    "বাবুগন্জ": {"upazila": "Babuganj", "district": "Barishal"},
    "bhanga": {"upazila": "Bhanga", "district": "Faridpur"},
    "ভাঙা": {"upazila": "Bhanga", "district": "Faridpur"},
    "shariatpur": {"district": "Shariatpur"},
    "শরীয়তপুর": {"district": "Shariatpur"},
    "শরিয়তপুর": {"district": "Shariatpur"},
    "শৈতপুর": {"district": "Shariatpur"},  # STT variant
    "chattogram": {"district": "Chattogram"},
    "chittagong": {"district": "Chattogram"},
    "চট্টগ্রাম": {"district": "Chattogram"},
}

_LOCATION_PATTERNS = [
    re.compile(r"([\u0980-\u09FFa-zA-Z\-]{3,})\s*(?:থেকে|তেকে)\s*বল", re.IGNORECASE),
    re.compile(r"([\u0980-\u09FFa-zA-Z\-]{3,})\s*(?:তে|এ)\s*(?:আবহাও|আবহাওয়া|weather)", re.IGNORECASE),
    re.compile(r"([\u0980-\u09FFa-zA-Z\-]{3,})\s*(?:তে|এ)\s*ক(?:ি|ী)?\s*ম(?:া|া)?\s*ন", re.IGNORECASE),
]


def _normalize_key(text: str) -> str:
    cleaned = unicodedata.normalize("NFKC", text.strip().lower())
    cleaned = re.sub(r"[^\w\u0980-\u09FF\-]", "", cleaned)
    return cleaned


def _title_place(name: str) -> str:
    if re.search(r"[\u0980-\u09FF]", name):
        return name.strip()
    return name.strip().title()


def extract_location_from_message(text: str) -> dict:
    """Extract district/upazila mentioned in farmer speech or text."""
    if not text or not text.strip():
        return {}

    lowered = text.lower()
    normalized_full = _normalize_key(text)

    for alias, location in KNOWN_PLACES.items():
        alias_key = _normalize_key(alias)
        if alias_key in normalized_full or alias.lower() in lowered or alias in text:
            return {**location, "source": "message"}

    for pattern in _LOCATION_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        raw_place = match.group(1).strip()
        place_key = _normalize_key(raw_place)

        for alias, location in KNOWN_PLACES.items():
            if _normalize_key(alias) == place_key or _normalize_key(alias) in place_key:
                return {**location, "source": "message"}

        # Unknown place name — treat as upazila/area the farmer said.
        titled = _title_place(raw_place)
        if len(titled) >= 3:
            return {"upazila": titled, "source": "message"}

    return {}


def merge_location_context(base: dict, extracted: dict) -> dict:
    """Message location overrides form/profile defaults."""
    merged = dict(base)
    if not extracted:
        return merged

    if extracted.get("district"):
        merged["district"] = extracted["district"]
    if extracted.get("upazila"):
        merged["upazila"] = extracted["upazila"]
    merged["location_source"] = extracted.get("source", "message")
    return merged


def resolve_location(
    district: Optional[str] = None,
    upazila: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
) -> dict:
    parts = [p for p in (upazila, district) if p]
    label = ", ".join(parts) if parts else "Bangladesh"

    return {
        "district": district,
        "upazila": upazila,
        "latitude": latitude,
        "longitude": longitude,
        "label": label,
    }
