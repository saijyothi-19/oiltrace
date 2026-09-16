from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict

class AisPositionResponse(BaseModel):
    id: int
    vessel_id: int
    timestamp: datetime
    position: Dict[str, Any]
    speed: Optional[float] = None
    course: Optional[float] = None
    heading: Optional[float] = None
    navigation_status: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class VesselResponse(BaseModel):
    id: int
    mmsi: str
    imo: Optional[str] = None
    name: str
    ship_type: str
    flag: Optional[str] = None
    length: Optional[float] = None
    width: Optional[float] = None
    positions: Optional[List[AisPositionResponse]] = None

    model_config = ConfigDict(from_attributes=True)

class AisImportResponse(BaseModel):
    imported_records: int
    vessels_updated: int
    duration_seconds: float
    message: str
