from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict
from app.models.drift import SimulationType, SimulationStatus

class DriftSimulationRequest(BaseModel):
    spill_event_id: int
    duration_hours: float = 12.0
    particle_count: int = 150
    timestep_minutes: int = 15
    windage_factor: float = 0.03

class DriftParticleResponse(BaseModel):
    id: int
    particle_id: int
    timestamp: datetime
    position: Dict[str, Any]

    model_config = ConfigDict(from_attributes=True)

class DriftSimulationResponse(BaseModel):
    id: int
    spill_event_id: int
    simulation_type: SimulationType
    start_time: datetime
    end_time: datetime
    duration_hours: float
    particle_count: int
    model_name: str
    confidence: float
    status: SimulationStatus
    origin_probability_geometry: Optional[Dict[str, Any]] = None
    created_at: datetime
    particles: Optional[List[DriftParticleResponse]] = None

    model_config = ConfigDict(from_attributes=True)
