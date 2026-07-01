from fastapi import APIRouter

from app.services.disease_service import get_wheat_disease_advisory

router = APIRouter(prefix="/disease", tags=["disease"])


@router.get("/wheat")
def wheat_disease_advisory():
    return get_wheat_disease_advisory()
