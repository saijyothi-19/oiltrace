from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict
from app.models.spill import SpillStatus
from app.schemas.satellite import SatelliteImageResponse

class SpillEventBase(BaseModel):
    detected_at: Optional[datetime] = None
    confidence: float
    area_km2: float
    perimeter_km: float
    centroid: Optional[Dict[str, Any]] = None
    bounding_box: Optional[Dict[str, Any]] = None
    spill_geometry: Dict[str, Any]
    status: SpillStatus = SpillStatus.DETECTED
    model_version: str = "unet-v1.0-baseline"

class SpillEventCreate(SpillEventBase):
    satellite_image_id: Optional[int] = None

class SpillEventUpdate(BaseModel):
    status: Optional[SpillStatus] = None
    confidence: Optional[float] = None
    notes: Optional[str] = None

class SpillEventResponse(SpillEventBase):
    id: int
    satellite_image_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    satellite_image: Optional[SatelliteImageResponse] = None

    model_config = ConfigDict(from_attributes=True)

class DetectionRunRequest(BaseModel):
    satellite_image_id: int
    threshold: float = 0.5
    min_area_km2: float = 0.01
    filter_lookalikes: bool = True
