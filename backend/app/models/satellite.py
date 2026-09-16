from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, JSON
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.db.spatial import GeoJSONGeometry

class SatelliteImage(Base):
    __tablename__ = "satellite_images"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(String(255), unique=True, index=True, nullable=False)
    satellite = Column(String(100), default="Sentinel-1", nullable=False)
    sensor = Column(String(100), default="C-SAR", nullable=False)
    acquisition_time = Column(DateTime, nullable=False, index=True)
    polarization = Column(String(50), default="VV", nullable=False)
    orbit = Column(String(50), default="DESCENDING", nullable=False)
    file_path = Column(String(500), nullable=False)
    thumbnail_path = Column(String(500), nullable=True)
    metadata_json = Column(JSON, nullable=True)
    bounding_geometry = Column(GeoJSONGeometry, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    spill_events = relationship("SpillEvent", back_populates="satellite_image", cascade="all, delete-orphan")
