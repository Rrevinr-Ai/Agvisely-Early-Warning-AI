from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class FarmerCreate(BaseModel):
    phone_number: str = Field(..., min_length=10, max_length=15)
    name: Optional[str] = None
    district: Optional[str] = None
    upazila: Optional[str] = None
    union_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    preferred_crop: Optional[str] = None


class FarmerResponse(FarmerCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class CallCreate(BaseModel):
    phone_number: str
    question_text: Optional[str] = None
    audio_base64: Optional[str] = None
    web_session_id: Optional[str] = None
    district: Optional[str] = None
    upazila: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    crop: Optional[str] = None


class CallResponse(BaseModel):
    id: int
    farmer_id: Optional[int]
    phone_number: str
    question_text: Optional[str]
    response_text: Optional[str]
    intent: Optional[str]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class AdvisoryRequest(BaseModel):
    crop: str
    district: Optional[str] = None
    upazila: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class AdvisoryResponse(BaseModel):
    crop: str
    location: str
    weather: dict
    advisory: dict


class WeatherRequest(BaseModel):
    district: Optional[str] = None
    upazila: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class WeatherResponse(BaseModel):
    location: str
    weather: dict


class SpeechTranscribeRequest(BaseModel):
    audio_base64: str
    language: Optional[str] = None


class SpeechTranscribeResponse(BaseModel):
    text: str
    language: str


class SpeechSpeakRequest(BaseModel):
    text: str


class SpeechSpeakResponse(BaseModel):
    audio_base64: str
    format: str = "mp3"


class SurveyCreate(BaseModel):
    call_id: Optional[int] = None
    farmer_id: Optional[int] = None
    comprehension_score: Optional[int] = Field(None, ge=1, le=5)
    trust_score: Optional[int] = Field(None, ge=1, le=5)
    adopted_practice: Optional[bool] = None
    feedback_text: Optional[str] = None


class SurveyResponse(SurveyCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
