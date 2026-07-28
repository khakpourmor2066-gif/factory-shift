from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, func

from app.database.connection import Base


class WebhookLog(Base):
    __tablename__ = "webhook_logs"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(30), nullable=False, index=True)
    messenger_user_id = Column(String(100), nullable=False, index=True)
    direction = Column(String(20), nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    request_text = Column(Text, nullable=True)
    response_status = Column(String(50), nullable=True, index=True)
    response_text = Column(Text, nullable=True)
    sent_status = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
