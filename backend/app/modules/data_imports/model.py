from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func

from app.database.connection import Base


class ImportJob(Base):
    __tablename__ = "import_jobs"

    id = Column(Integer, primary_key=True, index=True)
    import_type = Column(String(30), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    status = Column(String(30), nullable=False, default="PENDING", index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    total_rows = Column(Integer, nullable=False, default=0)
    valid_rows = Column(Integer, nullable=False, default=0)
    imported_rows = Column(Integer, nullable=False, default=0)
    rejected_rows = Column(Integer, nullable=False, default=0)
    payload_json = Column(Text, nullable=False, default="[]")
    snapshot_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)


class ImportError(Base):
    __tablename__ = "import_errors"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("import_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    row_number = Column(Integer, nullable=False)
    field_name = Column(String(100), nullable=True)
    error_code = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    raw_data_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
