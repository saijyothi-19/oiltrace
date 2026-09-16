import os
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from app.models.satellite import SatelliteImage
from app.core.config import settings

class SatelliteService:
    @staticmethod
    def create_satellite_image(
        db: Session,
        product_id: str,
        file_path: str,
        acquisition_time: Optional[datetime] = None,
        satellite: str = "Sentinel-1A",
        sensor: str = "C-SAR",
        polarization: str = "VV",
        orbit: str = "DESCENDING",
        bounding_geometry: Optional[Dict[str, Any]] = None,
        thumbnail_path: Optional[str] = None,
        metadata_json: Optional[Dict[str, Any]] = None,
    ) -> SatelliteImage:
        if not acquisition_time:
            acquisition_time = datetime.now(timezone.utc)

        existing = db.query(SatelliteImage).filter(SatelliteImage.product_id == product_id).first()
        if existing:
            return existing

        image = SatelliteImage(
            product_id=product_id,
            satellite=satellite,
            sensor=sensor,
            acquisition_time=acquisition_time,
            polarization=polarization,
            orbit=orbit,
            file_path=file_path,
            thumbnail_path=thumbnail_path,
            metadata_json=metadata_json or {},
            bounding_geometry=bounding_geometry,
        )
        db.add(image)
        db.commit()
        db.refresh(image)
        return image

    @staticmethod
    def get_by_id(db: Session, image_id: int) -> Optional[SatelliteImage]:
        return db.query(SatelliteImage).filter(SatelliteImage.id == image_id).first()

    @staticmethod
    def get_all(db: Session, limit: int = 50, offset: int = 0) -> List[SatelliteImage]:
        return db.query(SatelliteImage).order_by(SatelliteImage.acquisition_time.desc()).offset(offset).limit(limit).all()
