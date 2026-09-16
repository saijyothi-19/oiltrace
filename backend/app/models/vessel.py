from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, Index, JSON
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.db.spatial import GeoJSONGeometry

class Vessel(Base):
    __tablename__ = "vessels"

    id = Column(Integer, primary_key=True, index=True)
    mmsi = Column(String(20), unique=True, index=True, nullable=False)
    imo = Column(String(20), nullable=True, index=True)
    name = Column(String(150), nullable=False, default="UNKNOWN VESSEL")
    ship_type = Column(String(80), nullable=False, default="Tanker")
    flag = Column(String(80), nullable=True, default="Unknown")
    length = Column(Float, nullable=True)
    width = Column(Float, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    positions = relationship("AisPosition", back_populates="vessel", cascade="all, delete-orphan")
    candidates = relationship("VesselCandidate", back_populates="vessel", cascade="all, delete-orphan")


class AisPosition(Base):
    __tablename__ = "ais_positions"

    id = Column(Integer, primary_key=True, index=True)
    vessel_id = Column(Integer, ForeignKey("vessels.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    position = Column(GeoJSONGeometry, nullable=False)
    speed = Column(Float, nullable=True)  # knots (SOG)
    course = Column(Float, nullable=True)  # degrees (COG)
    heading = Column(Float, nullable=True)  # degrees True Heading
    navigation_status = Column(String(80), nullable=True, default="Under way using engine")

    vessel = relationship("Vessel", back_populates="positions")

    __table_args__ = (
        Index("idx_ais_vessel_timestamp", "vessel_id", "timestamp"),
        Index("idx_ais_timestamp", "timestamp"),
    )
