from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.call import Call
from app.models.call_session import CallSession
from app.models.farmer import Farmer
from app.schemas import CallCreate, CallResponse
from app.services.call_agent_service import call_agent_service
from app.services.location_service import extract_location_from_message, merge_location_context
from app.services.whisper_service import whisper_service

router = APIRouter(prefix="/calls", tags=["calls"])


def _get_or_create_farmer(db: Session, payload: CallCreate) -> Farmer | None:
    farmer = db.query(Farmer).filter(Farmer.phone_number == payload.phone_number).first()
    if farmer:
        if payload.district:
            farmer.district = payload.district
        if payload.upazila:
            farmer.upazila = payload.upazila
        if payload.latitude is not None:
            farmer.latitude = payload.latitude
        if payload.longitude is not None:
            farmer.longitude = payload.longitude
        if payload.crop:
            farmer.preferred_crop = payload.crop
        db.commit()
        db.refresh(farmer)
        return farmer

    if not any([payload.district, payload.upazila, payload.latitude, payload.longitude]):
        return None

    farmer = Farmer(
        phone_number=payload.phone_number,
        district=payload.district,
        upazila=payload.upazila,
        latitude=payload.latitude,
        longitude=payload.longitude,
        preferred_crop=payload.crop,
    )
    db.add(farmer)
    db.commit()
    db.refresh(farmer)
    return farmer


def _get_web_session(db: Session, session_id: str, phone_number: str, farmer_id: int | None) -> CallSession:
    key = f"web-{session_id}"
    session = db.query(CallSession).filter(CallSession.external_call_id == key).first()
    if session:
        return session

    session = CallSession(
        external_call_id=key,
        phone_number=phone_number,
        farmer_id=farmer_id,
        status="active",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def _apply_spoken_location(
    db: Session,
    farmer: Farmer | None,
    phone_number: str,
    spoken_location: dict,
    crop: str | None = None,
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
        preferred_crop=crop,
    )
    db.add(farmer)
    db.commit()
    db.refresh(farmer)
    return farmer


def _farmer_context(farmer: Farmer | None) -> dict:
    if not farmer:
        return {
            "district": None,
            "upazila": None,
            "latitude": None,
            "longitude": None,
            "preferred_crop": None,
        }
    return {
        "district": farmer.district,
        "upazila": farmer.upazila,
        "latitude": farmer.latitude,
        "longitude": farmer.longitude,
        "preferred_crop": farmer.preferred_crop,
    }


@router.post("/", response_model=CallResponse)
async def process_call(payload: CallCreate, db: Session = Depends(get_db)):
    question = payload.question_text

    if not question and payload.audio_base64:
        try:
            question = whisper_service.transcribe(payload.audio_base64)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Failed to transcribe audio") from exc

    if not question:
        raise HTTPException(status_code=400, detail="Provide question_text or audio_base64")

    farmer = _get_or_create_farmer(db, payload)
    context = _farmer_context(farmer)
    if payload.district:
        context["district"] = payload.district
    if payload.upazila:
        context["upazila"] = payload.upazila
    if payload.latitude is not None:
        context["latitude"] = payload.latitude
    if payload.longitude is not None:
        context["longitude"] = payload.longitude
    if payload.crop:
        context["preferred_crop"] = payload.crop

    spoken_location = extract_location_from_message(question)
    context = merge_location_context(context, spoken_location)
    farmer = _apply_spoken_location(
        db,
        farmer,
        payload.phone_number,
        spoken_location,
        payload.crop,
    )

    messages: list[dict] = []
    web_session = None
    if payload.web_session_id:
        web_session = _get_web_session(
            db,
            payload.web_session_id,
            payload.phone_number,
            farmer.id if farmer else None,
        )
        if farmer and not web_session.farmer_id:
            web_session.farmer_id = farmer.id
            db.commit()
        messages = web_session.get_messages()

    try:
        answer, messages, intent = await call_agent_service.handle_turn(
            user_message=question,
            messages=messages,
            farmer_context=context,
        )
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if web_session:
        web_session.set_messages(messages)
        db.add(web_session)

    call = Call(
        farmer_id=farmer.id if farmer else None,
        phone_number=payload.phone_number,
        question_text=question,
        response_text=answer,
        intent=intent,
        status="completed",
    )
    db.add(call)
    db.commit()
    db.refresh(call)
    return call


@router.get("/{call_id}", response_model=CallResponse)
def get_call(call_id: int, db: Session = Depends(get_db)):
    call = db.query(Call).filter(Call.id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    return call
