from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.farmer import Farmer
from app.schemas import FarmerCreate, FarmerResponse

router = APIRouter(prefix="/farmers", tags=["farmers"])


@router.post("/", response_model=FarmerResponse)
def register_farmer(payload: FarmerCreate, db: Session = Depends(get_db)):
    existing = db.query(Farmer).filter(Farmer.phone_number == payload.phone_number).first()
    if existing:
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(existing, field, value)
        db.commit()
        db.refresh(existing)
        return existing

    farmer = Farmer(**payload.model_dump())
    db.add(farmer)
    db.commit()
    db.refresh(farmer)
    return farmer


@router.get("/{phone_number}", response_model=FarmerResponse)
def get_farmer(phone_number: str, db: Session = Depends(get_db)):
    farmer = db.query(Farmer).filter(Farmer.phone_number == phone_number).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")
    return farmer
