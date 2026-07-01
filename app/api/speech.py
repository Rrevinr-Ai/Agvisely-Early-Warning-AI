from fastapi import APIRouter, HTTPException

from app.schemas import (
    SpeechSpeakRequest,
    SpeechSpeakResponse,
    SpeechTranscribeRequest,
    SpeechTranscribeResponse,
)
from app.services.tts_service import tts_service
from app.services.whisper_service import whisper_service

router = APIRouter(prefix="/speech", tags=["speech"])


@router.post("/transcribe", response_model=SpeechTranscribeResponse)
def transcribe_speech(payload: SpeechTranscribeRequest):
    try:
        text = whisper_service.transcribe(payload.audio_base64, payload.language)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Failed to transcribe audio") from exc

    return SpeechTranscribeResponse(text=text, language=payload.language or "auto")


@router.post("/speak", response_model=SpeechSpeakResponse)
def speak_text(payload: SpeechSpeakRequest):
    try:
        audio_base64 = tts_service.synthesize(payload.text)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Failed to synthesize speech") from exc

    return SpeechSpeakResponse(audio_base64=audio_base64)
