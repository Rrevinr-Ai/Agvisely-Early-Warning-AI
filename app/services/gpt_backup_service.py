import json
from datetime import datetime
from typing import Optional

from openai import OpenAI

from app.config import settings

FARMING_AGENT_SYSTEM = (
    "You are Agvisely AI — an experienced Bangladeshi Krishibid / krishi extension officer. "
    "Speak to farmers on the phone in simple, warm, practical Bangla. "
    "Never mention Knowledge Base, Excel, Database, RAG, GPT, AI, or that data is unavailable. "
    "If crop-specific verified advisory is not provided, silently give weather-aware agronomic "
    "best practices from crop, weather, season, location, and stage. "
    "Use weather TRENDS (not only today). Never recommend fertilizer/spray before or during heavy rain. "
    "Prefer structure: আবহাওয়া → ফসল → ঝুঁকি → কী করবেন → কখন → কেন. "
    "Reply with valid JSON only. All farmer-facing text must be in Bangla."
)


class GPTBackupService:
    def __init__(self) -> None:
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
        self.model = settings.LLM_MODEL

    def _chat_json(self, prompt: str) -> dict:
        if not self.client:
            raise ValueError("OPENAI_API_KEY is not configured")

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": FARMING_AGENT_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            temperature=0.5,
            max_tokens=450,
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)

    def _location_label(
        self,
        district: Optional[str],
        upazila: Optional[str],
    ) -> str:
        return ", ".join(part for part in (upazila, district) if part) or "Bangladesh"

    async def weather_backup(
        self,
        district: Optional[str] = None,
        upazila: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> dict:
        location = self._location_label(district, upazila)
        today = datetime.now().strftime("%Y-%m-%d")
        coords = ""
        if latitude is not None and longitude is not None:
            coords = f" Coordinates: {latitude}, {longitude}."

        prompt = (
            f"Today is {today}.{coords}\n"
            f"Farmer location: {location}, Bangladesh.\n"
            "Agvisely live weather API is unavailable. Act as a real human farming agent on a phone call.\n\n"
            "IMPORTANT: Focus on WEATHER only. Do NOT invent planting other crops or harvest advice "
            "unless the farmer's crop/stage is unknown. Keep crop tips generic and cautious.\n\n"
            "Return JSON with these keys:\n"
            "- agent_speech: 4-6 sentences of natural spoken Bangla about area weather/temperature "
            "and rainfall outlook for the coming days. Do not tell them to plant মুগ/পপি or harvest "
            "unless clearly season-appropriate and no specific crop was already named.\n"
            "- temperature: estimated temperature range for the area now, e.g. '২৮-৩৪°সে'\n"
            "- season_bn: current agricultural season in Bangla\n"
            "- weather_condition: brief Bangla weather outlook for coming days\n"
            "- rainfall_outlook: brief Bangla rainfall expectation\n"
            "- crops_to_plant: Bangla — optional general note, or empty string\n"
            "- crops_to_harvest: Bangla — optional, or empty string\n"
            "- urgent_actions: Bangla — weather-related farm precautions this week\n"
            "- disclaimer: one short Bangla line saying this is general guidance, not live Agvisely data\n"
        )
        data = self._chat_json(prompt)
        disclaimer = data.get(
            "disclaimer",
            "এটি সাধারণ নির্দেশনা, Agvisely-র লাইভ পূর্বাভাস নয়।",
        )
        agent_speech = data.get("agent_speech", "")

        return {
            "source": "gpt_backup",
            "district": district,
            "upazila": upazila,
            "latitude": latitude,
            "longitude": longitude,
            "agent_speech": agent_speech,
            "summary": agent_speech,
            "temperature": data.get("temperature", ""),
            "season_bn": data.get("season_bn", ""),
            "weather_condition": data.get("weather_condition", ""),
            "rainfall_outlook": data.get("rainfall_outlook", ""),
            "crops_to_plant": data.get("crops_to_plant", ""),
            "crops_to_harvest": data.get("crops_to_harvest", ""),
            "urgent_actions": data.get("urgent_actions", ""),
            "disclaimer": disclaimer,
        }

    async def advisory_backup(
        self,
        crop: str,
        district: Optional[str] = None,
        upazila: Optional[str] = None,
    ) -> dict:
        location = self._location_label(district, upazila)
        today = datetime.now().strftime("%Y-%m-%d")

        prompt = (
            f"Today is {today}.\n"
            f"Farmer location: {location}, Bangladesh. Crop: {crop}.\n"
            "Agvisely live advisory API is unavailable. Act as a real human farming agent.\n\n"
            "Return JSON with:\n"
            "- agent_speech: natural spoken Bangla advice for this crop and season (5-6 sentences)\n"
            "- planting_advice: Bangla\n"
            "- harvest_advice: Bangla — when/how to harvest if relevant now\n"
            "- care_tips: Bangla — irrigation, pest, fertilizer tips for this week\n"
            "- disclaimer: one short Bangla line — general guidance, not live Agvisely data\n"
        )
        data = self._chat_json(prompt)
        agent_speech = data.get("agent_speech", "")

        return {
            "source": "gpt_backup",
            "crop": crop,
            "district": district,
            "upazila": upazila,
            "agent_speech": agent_speech,
            "message": agent_speech,
            "planting_advice": data.get("planting_advice", ""),
            "harvest_advice": data.get("harvest_advice", ""),
            "care_tips": data.get("care_tips", ""),
            "disclaimer": data.get(
                "disclaimer",
                "এটি সাধারণ নির্দেশনা, Agvisely-র লাইভ পরামর্শ নয়।",
            ),
        }


gpt_backup_service = GPTBackupService()
