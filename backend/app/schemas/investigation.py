from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict
from app.models.investigation import InvestigationStatus
from app.schemas.user import UserResponse
from app.schemas.spill import SpillEventResponse

class InvestigationBase(BaseModel):
    spill_event_id: int
    assigned_to: Optional[int] = None
    status: InvestigationStatus = InvestigationStatus.NEW
    notes: Optional[str] = None

class InvestigationCreate(InvestigationBase):
    pass

class InvestigationUpdate(BaseModel):
    status: Optional[InvestigationStatus] = None
    notes: Optional[str] = None
    assigned_to: Optional[int] = None

class InvestigationResponse(InvestigationBase):
    id: int
    created_at: datetime
    updated_at: datetime
    assignee: Optional[UserResponse] = None
    spill_event: Optional[SpillEventResponse] = None

    model_config = ConfigDict(from_attributes=True)
