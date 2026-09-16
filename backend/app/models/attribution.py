import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, Enum, JSON, Index
from sqlalchemy.orm import relationship
from app.db.session import Base

class PriorityLevel(str, enum.Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class VesselCandidate(Base):
    __tablename__ = "vessel_candidates"

    id = Column(Integer, primary_key=True, index=True)
    spill_event_id = Column(Integer, ForeignKey("spill_events.id", ondelete="CASCADE"), nullable=False, index=True)
    vessel_id = Column(Integer, ForeignKey("vessels.id", ondelete="CASCADE"), nullable=False, index=True)
    spatial_score = Column(Float, nullable=False, default=0.0)
    temporal_score = Column(Float, nullable=False, default=0.0)
    trajectory_score = Column(Float, nullable=False, default=0.0)
    behaviour_score = Column(Float, nullable=False, default=0.0)
    data_quality_score = Column(Float, nullable=False, default=0.0)
    overall_score = Column(Float, nullable=False, default=0.0, index=True)
    priority = Column(Enum(PriorityLevel), default=PriorityLevel.LOW, nullable=False, index=True)
    explanation_json = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    spill_event = relationship("SpillEvent", back_populates="candidates")
    vessel = relationship("Vessel", back_populates="candidates")

    __table_args__ = (
        Index("idx_candidate_spill_overall", "spill_event_id", "overall_score"),
    )
