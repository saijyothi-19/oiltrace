from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, String, DateTime, JSON
from app.db.session import Base
from app.db.spatial import GeoJSONGeometry

class EnvironmentalData(Base):
    __tablename__ = "environmental_data"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    source = Column(String(100), default="ERA5", nullable=False)
    wind_speed = Column(Float, nullable=False)  # m/s
    wind_direction = Column(Float, nullable=False)  # degrees (0-360)
    current_u = Column(Float, nullable=False)  # m/s eastward
    current_v = Column(Float, nullable=False)  # m/s northward
    wave_height = Column(Float, nullable=True)  # meters
    temperature = Column(Float, nullable=True)  # Celsius
    geometry = Column(GeoJSONGeometry, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
