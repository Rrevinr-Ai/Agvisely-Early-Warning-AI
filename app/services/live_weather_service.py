"""Live weather via Open-Meteo (no API key) when Agvisely is not configured."""

from __future__ import annotations

from typing import Optional

import httpx

from app.config import settings

# Approximate centroids for pilot / interview locations
_PLACE_COORDS: dict[str, tuple[float, float]] = {
    "faridpur": (23.607, 89.841),
    "ফরিদপুর": (23.607, 89.841),
    "bhanga": (23.383, 89.983),
    "vanga": (23.383, 89.983),
    "ভাঙা": (23.383, 89.983),
    "ভাঙ্গা": (23.383, 89.983),
    "modhukhali": (23.550, 89.700),
    "madhukhali": (23.550, 89.700),
    "মধুখালি": (23.550, 89.700),
    "মধুখালী": (23.550, 89.700),
    "মদুখালি": (23.550, 89.700),
    "মধুকাতি": (23.550, 89.700),
    "মধুকালি": (23.550, 89.700),
    "madhukati": (23.550, 89.700),
    "modhukati": (23.550, 89.700),
    "babuganj": (22.819, 90.322),
    "babugang": (22.819, 90.322),
    "babugunj": (22.819, 90.322),
    "বাবুগঞ্জ": (22.819, 90.322),
    "বাবুগন্জ": (22.819, 90.322),
    "barishal": (22.701, 90.353),
    "barisal": (22.701, 90.353),
    "বরিশাল": (22.701, 90.353),
    "rangpur sadar": (25.744, 89.275),
    "rangpursadar": (25.744, 89.275),
    "rangpur": (25.744, 89.275),
    "রংপুর": (25.744, 89.275),
    "রংপুর সদর": (25.744, 89.275),
    "dhaka": (23.810, 90.412),
    "ঢাকা": (23.810, 90.412),
    "khulna": (22.845, 89.540),
    "খুলনা": (22.845, 89.540),
    "rajshahi": (24.374, 88.604),
    "রাজশাহী": (24.374, 88.604),
    "sylhet": (24.894, 91.869),
    "সিলেট": (24.894, 91.869),
    "mymensingh": (24.747, 90.420),
    "ময়মনসিংহ": (24.747, 90.420),
    "chattogram": (22.356, 91.783),
    "chittagong": (22.356, 91.783),
    "চট্টগ্রাম": (22.356, 91.783),
}


def _norm(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


def resolve_coords(
    *,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    district: Optional[str] = None,
    upazila: Optional[str] = None,
) -> Optional[tuple[float, float]]:
    if latitude is not None and longitude is not None:
        return float(latitude), float(longitude)

    for key in (upazila, district, f"{upazila} {district}" if upazila and district else None):
        if not key:
            continue
        n = _norm(key)
        compact = n.replace(" ", "")
        if n in _PLACE_COORDS:
            return _PLACE_COORDS[n]
        if compact in _PLACE_COORDS:
            return _PLACE_COORDS[compact]
        for alias, coords in _PLACE_COORDS.items():
            if alias in n or n in alias:
                return coords
    return None


def _bn_temp(c: float) -> str:
    return f"{c:.0f}°সে"


def _bn_rain_label(mm: float) -> str:
    if mm < 1:
        return "শুষ্ক / বৃষ্টি প্রায় নেই"
    if mm < 10:
        return f"হালকা বৃষ্টি (প্রায় {mm:.0f} মিমি/দিন)"
    if mm < 44:
        return f"মাঝারি বৃষ্টি (প্রায় {mm:.0f} মিমি/দিন)"
    if mm < 88:
        return f"ভারী বৃষ্টি (প্রায় {mm:.0f} মিমি/দিন)"
    return f"অতি ভারী বৃষ্টি (প্রায় {mm:.0f} মিমি/দিন)"


async def fetch_live_forecast(
    *,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    district: Optional[str] = None,
    upazila: Optional[str] = None,
    forecast_days: int = 5,
) -> Optional[dict]:
    """Return live 5-day outlook with numeric temperature_c / rainfall_mm for Excel."""
    coords = resolve_coords(
        latitude=latitude,
        longitude=longitude,
        district=district,
        upazila=upazila,
    )
    if not coords:
        return None

    lat, lon = coords
    days = max(1, min(int(forecast_days or 5), 7))
    url = settings.LIVE_WEATHER_API_URL.rstrip("/")
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
        "timezone": "Asia/Dhaka",
        "forecast_days": days,
    }
    timeout = httpx.Timeout(settings.LIVE_WEATHER_TIMEOUT, connect=3.0)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, httpx.TimeoutException, ValueError):
        return None

    daily = data.get("daily") or {}
    tmax = [float(x) for x in (daily.get("temperature_2m_max") or []) if x is not None]
    tmin = [float(x) for x in (daily.get("temperature_2m_min") or []) if x is not None]
    rain = [float(x) for x in (daily.get("precipitation_sum") or []) if x is not None]
    if not tmax and not rain:
        return None

    max_temp = max(tmax) if tmax else None
    avg_temp = (sum(tmax) / len(tmax)) if tmax else None
    avg_rain = (sum(rain) / len(rain)) if rain else 0.0
    # Excel matching uses a representative daily rainfall / peak heat
    temperature_c = max_temp if max_temp is not None else avg_temp
    rainfall_mm = round(avg_rain, 1)

    place = upazila or district or f"{lat:.2f},{lon:.2f}"
    temp_txt = _bn_temp(temperature_c) if temperature_c is not None else "অজানা"
    rain_txt = _bn_rain_label(rainfall_mm)
    speech = (
        f"{place}-এ আগামী {days} দিনে সর্বোচ্চ তাপমাত্রা প্রায় {temp_txt} "
        f"এবং গড়ে {rain_txt} থাকতে পারে (লাইভ পূর্বাভাস)।"
    )

    return {
        "source": "open_meteo",
        "provider": "open-meteo",
        "district": district,
        "upazila": upazila,
        "latitude": lat,
        "longitude": lon,
        "temperature_c": round(float(temperature_c), 1) if temperature_c is not None else None,
        "rainfall_mm": rainfall_mm,
        "temperature": temp_txt if temperature_c is not None else None,
        "rainfall_outlook": rain_txt,
        "weather_condition": speech,
        "agent_speech": speech,
        "summary": speech,
        "forecast_days": days,
        "daily_max_temp_c": tmax,
        "daily_min_temp_c": tmin,
        "daily_rainfall_mm": rain,
        "disclaimer": "লাইভ আবহাওয়া Open-Meteo থেকে; Agvisely API কনফিগার হলে সেটা অগ্রাধিকার পাবে।",
    }
