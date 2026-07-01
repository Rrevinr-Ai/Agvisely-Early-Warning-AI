from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.survey import Survey
from app.schemas import SurveyCreate, SurveyResponse

router = APIRouter(prefix="/surveys", tags=["surveys"])


@router.post("/", response_model=SurveyResponse)
def submit_survey(payload: SurveyCreate, db: Session = Depends(get_db)):
    survey = Survey(**payload.model_dump())
    db.add(survey)
    db.commit()
    db.refresh(survey)
    return survey


@router.get("/{survey_id}", response_model=SurveyResponse)
def get_survey(survey_id: int, db: Session = Depends(get_db)):
    survey = db.query(Survey).filter(Survey.id == survey_id).first()
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    return survey
