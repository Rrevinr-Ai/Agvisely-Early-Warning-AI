from fastapi import APIRouter

from app.schemas import AdvisoryRequest, AdvisoryResponse
from app.services.agvisely_service import agvisely_service
from app.services.location_service import resolve_location

router = APIRouter(prefix="/advisory", tags=["advisory"])


@router.post("/", response_model=AdvisoryResponse)
async def get_advisory(payload: AdvisoryRequest):
    location = resolve_location(
        district=payload.district,
        upazila=payload.upazila,
        latitude=payload.latitude,
        longitude=payload.longitude,
    )

    weather = await agvisely_service.get_weather(
        latitude=payload.latitude,
        longitude=payload.longitude,
        district=payload.district,
        upazila=payload.upazila,
    )
    advisory = await agvisely_service.get_crop_advisory(
        crop=payload.crop,
        latitude=payload.latitude,
        longitude=payload.longitude,
        district=payload.district,
        upazila=payload.upazila,
    )

    return AdvisoryResponse(
        crop=payload.crop,
        location=location["label"],
        weather=weather,
        advisory=advisory,
    )
