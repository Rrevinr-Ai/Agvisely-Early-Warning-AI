from fastapi import APIRouter

from app.schemas import WeatherRequest, WeatherResponse
from app.services.agvisely_service import agvisely_service
from app.services.location_service import resolve_location

router = APIRouter(prefix="/weather", tags=["weather"])


@router.post("/", response_model=WeatherResponse)
async def get_weather(payload: WeatherRequest):
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

    return WeatherResponse(location=location["label"], weather=weather)
