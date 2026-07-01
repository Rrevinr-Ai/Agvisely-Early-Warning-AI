from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String

from app.database.connection import Base


class Farmer(Base):
    __tablename__ = "farmers"

    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String(15), unique=True, nullable=False, index=True)
    name = Column(String(100))
    district = Column(String(100))
    upazila = Column(String(100))
    union_name = Column(String(100))
    latitude = Column(Float)
    longitude = Column(Float)
    preferred_crop = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
