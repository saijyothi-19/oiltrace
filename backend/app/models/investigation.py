import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
from app.db.session import Base

class InvestigationStatus(str, enum.Enum):
    NEW = "NEW"
    UNDER_REVIEW = "UNDER REVIEW"
    HIGH_PRIORITY = "HIGH PRIORITY"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"

class Investigation(Base):
    __tablename__ = "investigations"

    id = Column(Integer, primary_key=True, index=True)
    spill_event_id = Column(Integer, ForeignKey("spill_events.id", ondelete="CASCADE"), unique=True, nullable=False)
    assigned_to = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status = Column(Enum(InvestigationStatus), default=InvestigationStatus.NEW, nullable=False, index=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    spill_event = relationship("SpillEvent", back_populates="investigation")
    assignee = relationship("User", back_populates="investigations")
