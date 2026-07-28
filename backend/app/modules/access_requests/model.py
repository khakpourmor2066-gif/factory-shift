from sqlalchemy import Column, DateTime, Integer, String, Text, func

from app.database.connection import Base


class AccessRequest(Base):
    __tablename__ = "access_requests"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(30), nullable=False, index=True)
    messenger_user_id = Column(String(100), nullable=False, index=True)
    latest_text = Column(Text, nullable=True)
    status = Column(String(30), nullable=False, default="pending", index=True)
    request_count = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
