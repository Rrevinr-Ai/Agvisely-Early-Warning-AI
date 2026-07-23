"""Short Bangla speak step after advisory bullet filter (no tools)."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from openai import OpenAI

from app.config import settings

_RULES_PATH = Path(__file__).resolve().parents[1] / "prompts" / "krishibid_rules.txt"

_LEAK_PATTERNS = (
    re.compile(r"(?i)knowledge\s*base"),
    re.compile(r"(?i)\bexcel\b"),
    re.compile(r"(?i)\brag\b"),
    re.compile(r"(?i)vector\s*database"),
    re.compile(r"(?i)\bgpt\b"),
    re.compile(r"(?i)database"),
    re.compile(r"নলেজ\s*বেস"),
    re.compile(r"ভেরিফাইড\s*পরামর্শ\s*নেই"),
    re.compile(r"সাধারণ\s*কৃষিবিদ্যাভিত্তিক"),
    re.compile(r"তথ্য\s*নেই"),
    re.compile(r"unavailable", re.I),
)


def _load_krishibid_rules() -> str:
    try:
        return _RULES_PATH.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


SPEAK_SYSTEM = (
    (_load_krishibid_rules() + "\n\n" if _RULES_PATH.exists() else "")
    + "PHONE REPLY MODE:\n"
    "Reply in natural spoken Bangla. Prefer the section structure from the rules "
    "(আবহাওয়া → ফসল → ঝুঁকি → কী করবেন → কখন → কেন → অতিরিক্ত), "
    "compressed for a phone call.\n"
    "Internal context uses advisory_source=verified|general — NEVER say these words to the farmer.\n"
    "If advisory_source=verified: use the provided advisory bullets as facts; do not contradict.\n"
    "If advisory_source=general or bullets empty: give practical weather-aware agronomic advice "
    "from crop + weather + season + location + stage. Do not mention missing data.\n"
    "Never mention Knowledge Base, Excel, Database, RAG, GPT, AI, or internal systems.\n"
    "If Constraints include no_money_for_soil_test: "
    "NEVER insist on মাটি পরীক্ষা; say মাটি পরীক্ষা ছাড়াই চলবে and recommend "
    "লিফ কালার চার্ট (এলসিসি) and/or গুটি ইউরিয়া / পরিমিত ইউরিয়া when relevant.\n"
    "Do not repeat points already covered in recent conversation.\n"
    "When verified bullets exist, do not invent pesticides/fertilizers not in those bullets.\n"
    "Weather safety: no fertilizer/spray before or during heavy rain; suggest safest timing.\n"
    "If weather summary is provided, start with আবহাওয়ার বিশ্লেষণ."
)


def sanitize_farmer_speech(text: str) -> str:
    """Strip accidental internal/leak lines from farmer-facing text."""
    if not text:
        return text
    kept: list[str] = []
    for line in text.splitlines():
        if any(p.search(line) for p in _LEAK_PATTERNS):
            continue
        kept.append(line)
    cleaned = "\n".join(kept).strip()
    # Collapse leftover blank lines
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned or text.strip()


class SpeakService:
    def __init__(self) -> None:
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
        self.model = settings.LLM_MODEL

    def speak(
        self,
        *,
        user_message: str,
        intent: str,
        constraints: list[str],
        crop: str,
        stage: str,
        bullets: list[dict],
        recent: list[dict],
        weather_summary: Optional[str] = None,
        location_label: Optional[str] = None,
        advisory_source: Optional[str] = None,
        knowledge_source: Optional[str] = None,  # backward-compatible alias
    ) -> Optional[str]:
        if not settings.EXCEL_SPEAK_LLM or not self.client:
            return None
        if not bullets and not weather_summary:
            return None

        bullet_lines = "\n".join(f"- {b.get('text')}" for b in bullets)
        history_lines = "\n".join(
            f"{m.get('role')}: {m.get('content')}" for m in (recent or [])[-6:]
        )
        source = advisory_source or knowledge_source
        if not source:
            source = "verified" if bullets else "general"
        if source in {"excel", "cimmyt"}:
            source = "verified"

        prompt = (
            f"Current datetime (Asia/Dhaka): "
            f"{datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
            f"crop: {crop}\n"
            f"location: {location_label or 'Bangladesh'}\n"
            f"stage: {stage or 'unknown'}\n"
            f"intent: {intent}\n"
            f"advisory_source: {source}\n"
            f"constraints: {', '.join(constraints) or 'none'}\n"
            f"Farmer said: {user_message}\n\n"
            f"Recent conversation:\n{history_lines or '(none)'}\n\n"
            f"weather:\n{weather_summary or '(none)'}\n\n"
            f"advisory:\n{bullet_lines or 'null'}\n\n"
            "Write the Krishibid phone reply in Bangla. "
            "Never mention advisory_source or any internal system."
        )
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SPEAK_SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.35,
                max_tokens=520,
            )
            text = (response.choices[0].message.content or "").strip()
            return sanitize_farmer_speech(text) if text else None
        except Exception:
            return None


speak_service = SpeakService()
