import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.db.spatial import GeoJSONGeometry

class SpillStatus(str, enum.Enum):
    NOT_ANALYZED = "NOT ANALYZED"
    ANALYZING = "ANALYZING"
    DETECTED = "DETECTED"
    NO_SPILL = "NO SPILL"
    REVIEW_REQUIRED = "REVIEW REQUIRED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"

class SpillEvent(Base):
    __tablename__ = "spill_events"

    id = Column(Integer, primary_key=True, index=True)
    satellite_image_id = Column(Integer, ForeignKey("satellite_images.id", ondelete="SET NULL"), nullable=True)
    detected_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    confidence = Column(Float, nullable=False, default=0.0)
    area_km2 = Column(Float, nullable=False, default=0.0)
    perimeter_km = Column(Float, nullable=False, default=0.0)
    centroid = Column(GeoJSONGeometry, nullable=True)
    bounding_box = Column(GeoJSONGeometry, nullable=True)
    spill_geometry = Column(GeoJSONGeometry, nullable=False)
    status = Column(Enum(SpillStatus), default=SpillStatus.DETECTED, nullable=False, index=True)
    model_version = Column(String(100), default="unet-v1.0-baseline", nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    satellite_image = relationship("SatelliteImage", back_populates="spill_events")
    detections = relationship("SpillDetection", back_populates="spill_event", cascade="all, delete-orphan")
    drift_simulations = relationship("DriftSimulation", back_populates="spill_event", cascade="all, delete-orphan")
    candidates = relationship("VesselCandidate", back_populates="spill_event", cascade="all, delete-orphan")
    investigation = relationship("Investigation", back_populates="spill_event", uselist=False, cascade="all, delete-orphan")


class SpillDetection(Base):
    __tablename__ = "spill_detections"

    id = Column(Integer, primary_key=True, index=True)
    spill_event_id = Column(Integer, ForeignKey("spill_events.id", ondelete="CASCADE"), nullable=False)
    model_name = Column(String(100), default="U-Net", nullable=False)
    model_version = Column(String(50), default="v1.0", nullable=False)
    confidence = Column(Float, nullable=False)
    mask_path = Column(String(500), nullable=True)
    polygon = Column(GeoJSONGeometry, nullable=False)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    spill_event = relationship("SpillEvent", back_populates="detections")
