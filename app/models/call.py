from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database.connection import Base


class Call(Base):
    __tablename__ = "calls"

    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=True)
    phone_number = Column(String(15), nullable=False, index=True)
    question_text = Column(Text)
    response_text = Column(Text)
    intent = Column(String(50))
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)

    farmer = relationship("Farmer", backref="calls")
