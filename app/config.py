import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    AGVISELY_API_URL: str = os.getenv("AGVISELY_API_URL", "https://api.agvisely.example/v1")
    AGVISELY_API_KEY: str = os.getenv("AGVISELY_API_KEY", "")
    AGVISELY_TIMEOUT: float = float(os.getenv("AGVISELY_TIMEOUT", "3"))

    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "gpt-4o-mini-transcribe")

    SYSTEM_PROMPT_PATH: str = os.getenv(
        "SYSTEM_PROMPT_PATH",
        os.path.join(os.path.dirname(__file__), "prompts", "system_prompt.txt"),
    )

    GPT_BACKUP_ENABLED: bool = os.getenv("GPT_BACKUP_ENABLED", "true").lower() == "true"

    # TTS: use "edge" for Bangladeshi Bangla (bn-BD), or "openai" for OpenAI voices
    TTS_PROVIDER: str = os.getenv("TTS_PROVIDER", "edge")
    TTS_MODEL: str = os.getenv("TTS_MODEL", "tts-1")
    TTS_VOICE: str = os.getenv("TTS_VOICE", "bn-BD-PradeepNeural")

    # Telephony (real phone calls)
    PUBLIC_BASE_URL: str = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000")
    TELEPHONY_PROVIDER: str = os.getenv("TELEPHONY_PROVIDER", "twilio")
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_PHONE_NUMBER: str = os.getenv("TWILIO_PHONE_NUMBER", "")
    TWILIO_SPEECH_LANGUAGE: str = os.getenv("TWILIO_SPEECH_LANGUAGE", "bn-BD")
    TWILIO_SAY_LANGUAGE: str = os.getenv("TWILIO_SAY_LANGUAGE", "bn-IN")


settings = Settings()
