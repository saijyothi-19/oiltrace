from typing import Optional, Any
from pydantic import BaseModel, Field

class ErrorDetail(BaseModel):
    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error description")
    details: Optional[Any] = Field(None, description="Optional diagnostic details")

class ErrorResponse(BaseModel):
    error: ErrorDetail

class SystemStatus(BaseModel):
    status: str = "ONLINE"
    service: str = "OILTRACE Marine Decision Support API"
    version: str = "1.0.0-prototype"
    environment: str
    database_connected: bool
    ml_device: str
    active_spills_count: int = 0
    active_investigations_count: int = 0
    total_vessels_tracked: int = 0
