from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict
from app.models.attribution import PriorityLevel
from app.schemas.ais import VesselResponse

class CandidateEvidenceItem(BaseModel):
    key: str
    label: str
    passed: bool
    score: float
    detail: str

class CandidateEvidence(BaseModel):
    spatial_distance_km: float
    temporal_delta_hours: float
    trajectory_heading_match_deg: float
    speed_knots: float
    anomalous_behavior_flag: bool
    ais_gap_detected: bool
    explanation_points: List[str]
    evidence_breakdown: List[CandidateEvidenceItem]

class VesselCandidateResponse(BaseModel):
    id: int
    spill_event_id: int
    vessel_id: int
    spatial_score: float
    temporal_score: float
    trajectory_score: float
    behaviour_score: float
    data_quality_score: float
    overall_score: float
    priority: PriorityLevel
    explanation_json: CandidateEvidence
    created_at: datetime
    vessel: Optional[VesselResponse] = None

    model_config = ConfigDict(from_attributes=True)

class AttributionAnalyzeRequest(BaseModel):
    spatial_radius_km: float = 50.0
    temporal_window_hours: float = 12.0
