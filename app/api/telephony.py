from urllib.parse import urljoin

from fastapi import APIRouter, Depends, Form
from fastapi.responses import Response
from sqlalchemy.orm import Session
from twilio.twiml.voice_response import Gather, VoiceResponse

from app.config import settings
from app.database.connection import get_db
from app.models.call import Call
from app.models.call_session import CallSession
from app.models.farmer import Farmer
from app.services.call_agent_service import call_agent_service
from app.services.location_service import extract_location_from_message, merge_location_context
from app.services.telephony_audio_cache import get_audio, store_audio
from app.services.tts_service import tts_service

router = APIRouter(prefix="/telephony", tags=["telephony"])

WELCOME = (
    "আগভাইজেলি কৃষি সহায়তায় স্বাগতম। "
    "আপনি আবহাওয়া, ফসল পরামর্শ, বা গম রোগ সম্পর্কে জিজ্ঞাসা করতে পারেন। "
    "আপনার প্রশ্ন বলুন।"
)
REPEAT = "আর কিছু জানতে চান? আপনার প্রশ্ন বলুন।"
NO_INPUT = "আমি আপনার কথা শুনতে পাইনি। অনুগ্রহ করে আবার বলুন।"
GOODBYE = "ধন্যবাদ। Agvisely কৃষি সহায়তা ব্যবহার করার জন্য ধন্যবাদ।"
ERROR_MSG = "দুঃখিত, একটি সমস্যা হয়েছে। অনুগ্রহ করে আবার চেষ্টা করুন।"


def _webhook(path: str) -> str:
    return urljoin(settings.PUBLIC_BASE_URL.rstrip("/") + "/", path.lstrip("/"))


def _twiml(response: VoiceResponse) -> Response:
    return Response(content=str(response), media_type="application/xml")


def _normalize_phone(value: str) -> str:
    return value.replace("whatsapp:", "").strip()


def _farmer_context(farmer: Farmer | None) -> dict:
    if not farmer:
        return {}
    return {
        "phone_number": farmer.phone_number,
        "name": farmer.name,
        "district": farmer.district,
        "upazila": farmer.upazila,
        "latitude": farmer.latitude,
        "longitude": farmer.longitude,
        "preferred_crop": farmer.preferred_crop,
    }


def _is_goodbye(message: str) -> bool:
    text = message.strip()
    if any(word in text for word in ("বিদায়", "কল শেষ", "রাখছি", "থামুন")):
        return True
    normalized = text.rstrip("।").strip().lower()
    return len(normalized) <= 20 and normalized in {"ধন্যবাদ", "thank you", "thanks"}


def _apply_spoken_location(
    db: Session,
    farmer: Farmer | None,
    phone_number: str,
    spoken_location: dict,
) -> Farmer | None:
    if not spoken_location:
        return farmer

    if farmer:
        if spoken_location.get("district"):
            farmer.district = spoken_location["district"]
        if spoken_location.get("upazila"):
            farmer.upazila = spoken_location["upazila"]
        db.commit()
        db.refresh(farmer)
        return farmer

    if not spoken_location.get("district") and not spoken_location.get("upazila"):
        return farmer

    farmer = Farmer(
        phone_number=phone_number,
        district=spoken_location.get("district"),
        upazila=spoken_location.get("upazila"),
    )
    db.add(farmer)
    db.commit()
    db.refresh(farmer)
    return farmer


def _get_or_create_session(db: Session, call_sid: str, phone_number: str) -> CallSession:
    session = db.query(CallSession).filter(CallSession.external_call_id == call_sid).first()
    if session:
        return session

    farmer = db.query(Farmer).filter(Farmer.phone_number == phone_number).first()
    session = CallSession(
        external_call_id=call_sid,
        phone_number=phone_number,
        farmer_id=farmer.id if farmer else None,
        status="active",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def _append_gather(response: VoiceResponse, action_path: str, prompt: str) -> None:
    gather = Gather(
        input="speech",
        action=_webhook(action_path),
        method="POST",
        language=settings.TWILIO_SPEECH_LANGUAGE,
        speech_timeout="auto",
        timeout=5,
    )
    gather.say(prompt, language=settings.TWILIO_SAY_LANGUAGE)
    response.append(gather)
    response.say(NO_INPUT, language=settings.TWILIO_SAY_LANGUAGE)
    response.redirect(_webhook("/telephony/incoming"))


async def _play_answer(response: VoiceResponse, answer: str, action_path: str) -> None:
    try:
        audio_bytes = await tts_service.synthesize_bytes_async(answer)
        token = store_audio(audio_bytes)
        response.play(_webhook(f"/telephony/audio/{token}"))
    except Exception:
        response.say(answer, language=settings.TWILIO_SAY_LANGUAGE)

    _append_gather(response, action_path, REPEAT)


@router.post("/incoming")
async def incoming_call(
    CallSid: str = Form(...),
    From: str = Form(...),
    db: Session = Depends(get_db),
):
    phone_number = _normalize_phone(From)
    _get_or_create_session(db, CallSid, phone_number)

    response = VoiceResponse()
    _append_gather(response, "/telephony/respond", WELCOME)
    return _twiml(response)


@router.post("/respond")
async def respond_to_call(
    CallSid: str = Form(...),
    From: str = Form(...),
    SpeechResult: str = Form(default=""),
    db: Session = Depends(get_db),
):
    phone_number = _normalize_phone(From)
    session = _get_or_create_session(db, CallSid, phone_number)
    farmer = db.query(Farmer).filter(Farmer.phone_number == phone_number).first()
    if not farmer and session.farmer_id:
        farmer = db.query(Farmer).filter(Farmer.id == session.farmer_id).first()

    user_message = SpeechResult.strip()
    response = VoiceResponse()

    if not user_message:
        _append_gather(response, "/telephony/respond", NO_INPUT)
        return _twiml(response)

    if _is_goodbye(user_message):
        session.status = "completed"
        db.commit()
        response.say(GOODBYE, language=settings.TWILIO_SAY_LANGUAGE)
        response.hangup()
        return _twiml(response)

    context = _farmer_context(farmer)
    spoken_location = extract_location_from_message(user_message)
    context = merge_location_context(context, spoken_location)
    farmer = _apply_spoken_location(db, farmer, phone_number, spoken_location)
    if farmer and not session.farmer_id:
        session.farmer_id = farmer.id
        db.commit()

    try:
        answer, messages, intent = await call_agent_service.handle_turn(
            user_message=user_message,
            messages=session.get_messages(),
            farmer_context=context,
        )
    except Exception:
        _append_gather(response, "/telephony/respond", ERROR_MSG)
        return _twiml(response)

    session.set_messages(messages)
    db.add(
        Call(
            farmer_id=farmer.id if farmer else None,
            phone_number=phone_number,
            question_text=user_message,
            response_text=answer,
            intent=intent,
            status="completed",
        )
    )
    db.commit()

    await _play_answer(response, answer, "/telephony/respond")
    return _twiml(response)


@router.post("/status")
async def call_status(
    CallSid: str = Form(...),
    CallStatus: str = Form(...),
    db: Session = Depends(get_db),
):
    session = db.query(CallSession).filter(CallSession.external_call_id == CallSid).first()
    if session and CallStatus in {"completed", "busy", "failed", "no-answer", "canceled"}:
        session.status = "completed"
        db.commit()
    return {"status": "ok"}


@router.get("/audio/{token}")
def get_call_audio(token: str):
    audio_bytes = get_audio(token)
    if not audio_bytes:
        return Response(status_code=404)
    return Response(content=audio_bytes, media_type="audio/mpeg")
