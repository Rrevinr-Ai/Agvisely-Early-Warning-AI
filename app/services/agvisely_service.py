from typing import Optional

import httpx

from app.config import settings
from app.services.demo_forecast_service import lookup_demo_forecast
from app.services.excel_advisory_service import excel_advisory_service
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

    async def _gpt_advisory_fallback(
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
            "message": f"Crop advisory for {crop} is temporarily unavailable.",
            "district": district,
            "upazila": upazila,
        }

    async def _excel_then_gpt_advisory(
        self,
        crop: str,
        district: Optional[str],
        upazila: Optional[str],
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        stage: Optional[str] = None,
        include_weather: bool = False,
    ) -> dict:
        """Two-tier selection: Excel rules first, GPT fallback second.

        Weather is only fetched when Agvisely live API is configured (trusted
        thresholds) or include_weather=True. Skipping GPT weather backup here
        saves several seconds on the hot path.
        """
        weather: dict = {"source": "skipped"}
        if self._is_configured():
            weather = await self.get_weather(
                latitude=latitude,
                longitude=longitude,
                district=district,
                upazila=upazila,
            )
        elif include_weather:
            weather = await self.get_weather(
                latitude=latitude,
                longitude=longitude,
                district=district,
                upazila=upazila,
            )

        try:
            excel_hit = excel_advisory_service.lookup(
                crop=crop,
                weather=weather,
                district=district,
                upazila=upazila,
                stage=stage,
            )
        except Exception:
            excel_hit = None

        if excel_hit:
            weather_clean = {
                k: v
                for k, v in (weather or {}).items()
                if k not in {"agent_speech", "summary"}
            }
            excel_hit["weather"] = weather_clean
            return excel_hit

        return await self._gpt_advisory_fallback(crop, district, upazila)

    async def get_weather(
        self,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        district: Optional[str] = None,
        upazila: Optional[str] = None,
    ) -> dict:
        # Interview/pilot demo forecasts take priority when enabled
        if settings.DEMO_FORECAST_ENABLED:
            demo = lookup_demo_forecast(district=district, upazila=upazila)
            if demo:
                if latitude is not None:
                    demo["latitude"] = latitude
                if longitude is not None:
                    demo["longitude"] = longitude
                return demo

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
        stage: Optional[str] = None,
        include_weather: bool = False,
    ) -> dict:
        # Preferred path: Excel matrix → GPT fallback (2-tier selection).
        # When demo forecasts exist for the location, always pull weather so Excel thresholds match.
        if settings.EXCEL_ADVISORY_ENABLED:
            use_weather = include_weather
            if settings.DEMO_FORECAST_ENABLED and lookup_demo_forecast(
                district=district, upazila=upazila
            ):
                use_weather = True
            return await self._excel_then_gpt_advisory(
                crop=crop,
                district=district,
                upazila=upazila,
                latitude=latitude,
                longitude=longitude,
                stage=stage,
                include_weather=use_weather,
            )

        if not self._is_configured():
            return await self._gpt_advisory_fallback(crop, district, upazila)

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
            return await self._gpt_advisory_fallback(crop, district, upazila)


agvisely_service = AgviselyService()
