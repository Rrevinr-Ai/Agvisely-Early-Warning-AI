from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship

from app.database.connection import Base


class Survey(Base):
    __tablename__ = "surveys"

    id = Column(Integer, primary_key=True, index=True)
    call_id = Column(Integer, ForeignKey("calls.id"), nullable=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=True)
    comprehension_score = Column(Integer)
    trust_score = Column(Integer)
    adopted_practice = Column(Boolean)
    feedback_text = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    call = relationship("Call", backref="surveys")
    farmer = relationship("Farmer", backref="surveys")
