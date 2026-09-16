from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict

class SatelliteImageBase(BaseModel):
    product_id: str
    satellite: str = "Sentinel-1"
    sensor: str = "C-SAR"
    acquisition_time: datetime
    polarization: str = "VV"
    orbit: str = "DESCENDING"
    file_path: str
    thumbnail_path: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None
    bounding_geometry: Optional[Dict[str, Any]] = None

class SatelliteImageCreate(SatelliteImageBase):
    pass

class SatelliteImageResponse(SatelliteImageBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
