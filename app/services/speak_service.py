"""Short Bangla speak step after Excel bullet filter (no tools)."""

from __future__ import annotations

from typing import Any, Optional

from openai import OpenAI

from app.config import settings

SPEAK_SYSTEM = (
    "You are a Bangla-speaking krishi extension officer on a phone call. "
    "Reply in natural spoken Bangla only (4-7 short sentences). "
    "Use ONLY the provided Excel advisory bullets as facts. "
    "If Constraints include no_money_for_soil_test: "
    "NEVER tell them to do মাটি পরীক্ষা; NEVER say they must spend money on soil testing. "
    "Explicitly say মাটি পরীক্ষা ছাড়াই চলবে and recommend লিফ কালার চার্ট (এলসিসি) and/or "
    "গুটি ইউরিয়া / পরিমিত ইউরিয়া from the bullets. "
    "Do not repeat points already covered in recent conversation. "
    "Do not invent new pesticides or fertilizers not in the bullets. "
    "If weather summary is provided, mention it briefly first."
)


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
    ) -> Optional[str]:
        if not settings.EXCEL_SPEAK_LLM or not self.client:
            return None
        if not bullets and not weather_summary:
            return None

        bullet_lines = "\n".join(f"- {b.get('text')}" for b in bullets)
        history_lines = "\n".join(
            f"{m.get('role')}: {m.get('content')}" for m in (recent or [])[-6:]
        )
        prompt = (
            f"Location: {location_label or 'Bangladesh'}\n"
            f"Crop: {crop}\n"
            f"Stage: {stage}\n"
            f"Intent: {intent}\n"
            f"Constraints: {', '.join(constraints) or 'none'}\n"
            f"Farmer just said: {user_message}\n\n"
            f"Recent conversation:\n{history_lines or '(none)'}\n\n"
            f"Weather note (optional):\n{weather_summary or '(none)'}\n\n"
            f"Excel advisory bullets to use:\n{bullet_lines or '(none)'}\n\n"
            "Write the phone reply now in Bangla."
        )
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SPEAK_SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.4,
                max_tokens=280,
            )
            text = (response.choices[0].message.content or "").strip()
            return text or None
        except Exception:
            return None


speak_service = SpeakService()
