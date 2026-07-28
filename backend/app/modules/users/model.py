from sqlalchemy import Boolean, Column, DateTime, Integer, String, func

from app.database.connection import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    mobile = Column(String(20), unique=True, nullable=False, index=True)
    messenger_user_id = Column(String(100), unique=True, nullable=True, index=True)
    role = Column(String(30), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
