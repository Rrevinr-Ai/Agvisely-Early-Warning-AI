import json
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from app.database.connection import Base


class CallSession(Base):
    __tablename__ = "call_sessions"

    id = Column(Integer, primary_key=True, index=True)
    external_call_id = Column(String(64), unique=True, nullable=False, index=True)
    phone_number = Column(String(20), nullable=False, index=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=True)
    messages_json = Column(Text, default="[]")
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def get_messages(self) -> list[dict]:
        return json.loads(self.messages_json or "[]")

    def set_messages(self, messages: list[dict]) -> None:
        self.messages_json = json.dumps(messages, ensure_ascii=False)
