from pathlib import Path

from openai import OpenAI

from app.config import settings


class LLMService:
    def __init__(self) -> None:
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
        self.model = settings.LLM_MODEL
        self.system_prompt = self._load_system_prompt()

    def _load_system_prompt(self) -> str:
        path = Path(settings.SYSTEM_PROMPT_PATH)
        if path.exists():
            return path.read_text(encoding="utf-8").strip()
        return (
            "You are a Bangla agricultural advisory assistant for Bangladeshi farmers. "
            "Answer only using the provided Agvisely data. If data is missing, say so clearly in Bangla."
        )

    def generate_advisory_response(
        self,
        question: str,
        weather_data: dict,
        advisory_data: dict,
        disease_data: dict | None = None,
        location_label: str = "Bangladesh",
    ) -> tuple[str, str]:
        if not self.client:
            raise ValueError("OPENAI_API_KEY is not configured")

        context = (
            f"Location: {location_label}\n"
            f"Weather data: {weather_data}\n"
            f"Crop advisory data: {advisory_data}\n"
        )
        if disease_data:
            context += f"Wheat disease data: {disease_data}\n"

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {
                    "role": "user",
                    "content": (
                        f"{context}\n"
                        f"Farmer question (Bangla or mixed): {question}\n"
                        "Respond in clear, simple Bangla suitable for voice playback."
                    ),
                },
            ],
            temperature=0.3,
        )

        answer = response.choices[0].message.content.strip()
        intent = self._detect_intent(question)
        return answer, intent

    def _detect_intent(self, question: str) -> str:
        lowered = question.lower()
        if any(word in lowered for word in ("রোগ", "disease", "rust", "blight")):
            return "disease"
        if any(word in lowered for word in ("আবহাওয়া", "weather", "বৃষ্টি", "rain")):
            return "weather"
        return "advisory"


llm_service = LLMService()
