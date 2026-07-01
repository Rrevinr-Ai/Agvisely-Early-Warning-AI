from typing import Optional

import httpx

from app.config import settings
from app.services.gpt_backup_service import gpt_backup_service

_PLACEHOLDER_MARKERS = ("example", "your-", "placeholder", "real-agvisely")


class AgviselyService:
    def __init__(self) -> None:
        self.base_url = settings.AGVISELY_API_URL.rstrip("/")
        self.api_key = settings.AGVISELY_API_KEY
        self.timeout = httpx.Timeout(settings.AGVISELY_TIMEOUT, connect=2.0)

    def _is_configured(self) -> bool:
        if not self.api_key:
            return False
        url = self.base_url.lower()
        return not any(marker in url for marker in _PLACEHOLDER_MARKERS)

    def _headers(self) -> dict:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def _weather_fallback(
        self,
        district: Optional[str],
        upazila: Optional[str],
        latitude: Optional[float],
        longitude: Optional[float],
    ) -> dict:
        if settings.GPT_BACKUP_ENABLED:
            try:
                return await gpt_backup_service.weather_backup(
                    district=district,
                    upazila=upazila,
                    latitude=latitude,
                    longitude=longitude,
                )
            except ValueError:
                pass

        return {
            "source": "fallback",
            "summary": "Weather data temporarily unavailable from Agvisely.",
            "district": district,
            "latitude": latitude,
            "longitude": longitude,
        }

    async def _advisory_fallback(
        self,
        crop: str,
        district: Optional[str],
        upazila: Optional[str],
    ) -> dict:
        if settings.GPT_BACKUP_ENABLED:
            try:
                return await gpt_backup_service.advisory_backup(
                    crop=crop,
                    district=district,
                    upazila=upazila,
                )
            except ValueError:
                pass

        return {
            "source": "fallback",
            "crop": crop,
            "message": f"Crop advisory for {crop} is temporarily unavailable from Agvisely.",
            "district": district,
            "upazila": upazila,
        }

    async def get_weather(
        self,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        district: Optional[str] = None,
        upazila: Optional[str] = None,
    ) -> dict:
        if not self._is_configured():
            return await self._weather_fallback(district, upazila, latitude, longitude)

        params = {}
        if latitude is not None and longitude is not None:
            params["lat"] = latitude
            params["lon"] = longitude
        if district:
            params["district"] = district

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/weather",
                    params=params,
                    headers=self._headers(),
                )
                response.raise_for_status()
                return response.json()
        except (httpx.HTTPError, httpx.TimeoutException):
            return await self._weather_fallback(district, upazila, latitude, longitude)

    async def get_crop_advisory(
        self,
        crop: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        district: Optional[str] = None,
        upazila: Optional[str] = None,
    ) -> dict:
        if not self._is_configured():
            return await self._advisory_fallback(crop, district, upazila)

        params = {"crop": crop}
        if latitude is not None and longitude is not None:
            params["lat"] = latitude
            params["lon"] = longitude
        if district:
            params["district"] = district
        if upazila:
            params["upazila"] = upazila

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/advisory",
                    params=params,
                    headers=self._headers(),
                )
                response.raise_for_status()
                return response.json()
        except (httpx.HTTPError, httpx.TimeoutException):
            return await self._advisory_fallback(crop, district, upazila)


agvisely_service = AgviselyService()
