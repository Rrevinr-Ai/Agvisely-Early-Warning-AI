from fastapi import FastAPI

from app.api import advisory, call, disease, farmer, speech, survey, telephony, weather
from app.database.connection import Base, engine
from app.models import call as call_model  # noqa: F401
from app.models import call_session as call_session_model  # noqa: F401
from app.models import farmer as farmer_model  # noqa: F401
from app.models import survey as survey_model  # noqa: F401

app = FastAPI(
    title="Agvisely Service Agent",
    description="Bangla voice-based agricultural advisory system for farmers",
    version="0.1.0",
)

app.include_router(farmer.router)
app.include_router(call.router)
app.include_router(telephony.router)
app.include_router(speech.router)
app.include_router(weather.router)
app.include_router(advisory.router)
app.include_router(disease.router)
app.include_router(survey.router)


@app.on_event("startup")
async def startup_event():
    Base.metadata.create_all(bind=engine)


@app.on_event("shutdown")
async def shutdown_event():
    engine.dispose()


@app.get("/")
async def root():
    return {"message": "Farming Agent is working properly"}
