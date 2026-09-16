from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.spill import SpillEvent
from app.models.drift import DriftSimulation, DriftParticle, SimulationType, SimulationStatus
from app.schemas.drift import DriftSimulationRequest, DriftSimulationResponse, DriftParticleResponse
from app.drift.simulation import LagrangianDriftSimulator

router = APIRouter(prefix="/api/drift", tags=["Drift Reconstruction & Hindcasting"])

def _execute_simulation(
    payload: DriftSimulationRequest,
    is_backward: bool,
    db: Session
) -> DriftSimulation:
    spill = db.query(SpillEvent).filter(SpillEvent.id == payload.spill_event_id).first()
    if not spill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Spill event #{payload.spill_event_id} not found."
        )

    # Extract spill centroid
    if not spill.centroid or "coordinates" not in spill.centroid:
        # Fallback to coordinates from bounding box or default
        center_lon, center_lat = 72.5, 19.0
    else:
        center_lon, center_lat = spill.centroid["coordinates"][0], spill.centroid["coordinates"][1]

    simulator = LagrangianDriftSimulator(windage_factor=payload.windage_factor)
    sim_data = simulator.simulate(
        center_lon=center_lon,
        center_lat=center_lat,
        start_time=spill.detected_at,
        duration_hours=payload.duration_hours,
        timestep_minutes=payload.timestep_minutes,
        particle_count=payload.particle_count,
        is_backward=is_backward,
    )

    sim = DriftSimulation(
        spill_event_id=spill.id,
        simulation_type=SimulationType.BACKWARD if is_backward else SimulationType.FORWARD,
        start_time=sim_data["start_time"],
        end_time=sim_data["end_time"],
        duration_hours=payload.duration_hours,
        particle_count=payload.particle_count,
        model_name="OpenDrift Lagrangian Emulator v2.0",
        parameters_json={
            "windage": payload.windage_factor,
            "timestep_minutes": payload.timestep_minutes,
            "environmental": sim_data["environmental_conditions"],
        },
        confidence=sim_data["confidence"],
        status=SimulationStatus.COMPLETED,
        origin_probability_geometry=sim_data["origin_probability_geometry"],
    )
    db.add(sim)
    db.flush()

    # Save a sampled trajectory subset for visualization (e.g. 30 particles x 5 waypoints)
    particles_to_insert = []
    sampled_particles = sim_data["particles"][:35]
    for p in sampled_particles:
        # Sample waypoints evenly
        history = p["history"]
        step_sample = max(1, len(history) // 6)
        for lon, lat, ts in history[::step_sample]:
            particle_rec = DriftParticle(
                simulation_id=sim.id,
                particle_id=p["id"],
                timestamp=ts,
                position={"type": "Point", "coordinates": [round(lon, 5), round(lat, 5)]},
            )
            particles_to_insert.append(particle_rec)

    db.add_all(particles_to_insert)
    db.commit()
    db.refresh(sim)
    return sim


@router.post("/backward", response_model=DriftSimulationResponse)
def run_backward_hindcast(payload: DriftSimulationRequest, db: Session = Depends(get_db)):
    return _execute_simulation(payload, is_backward=True, db=db)


@router.post("/forward", response_model=DriftSimulationResponse)
def run_forward_drift(payload: DriftSimulationRequest, db: Session = Depends(get_db)):
    return _execute_simulation(payload, is_backward=False, db=db)


@router.get("/{id}", response_model=DriftSimulationResponse)
def get_simulation_by_spill(id: int, db: Session = Depends(get_db)):
    # Look up by simulation id or spill_event_id
    sim = db.query(DriftSimulation).filter(
        (DriftSimulation.id == id) | (DriftSimulation.spill_event_id == id)
    ).order_by(DriftSimulation.created_at.desc()).first()

    if not sim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Drift simulation record for #{id} not found."
        )
    return sim


@router.get("/{id}/trajectory")
def get_trajectory_particles(id: int, db: Session = Depends(get_db)):
    particles = db.query(DriftParticle).filter(DriftParticle.simulation_id == id).all()
    return [
        {
            "particle_id": p.particle_id,
            "timestamp": p.timestamp,
            "coordinates": p.position.get("coordinates") if p.position else [0, 0]
        }
        for p in particles
    ]
