from datetime import timedelta, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.spill import SpillEvent
from app.models.drift import DriftSimulation, SimulationType
from app.models.vessel import Vessel, AisPosition
from app.models.attribution import VesselCandidate
from app.schemas.attribution import VesselCandidateResponse, AttributionAnalyzeRequest
from app.attribution.scorer import AttributionScoringEngine
from app.ais.trajectory import haversine_distance_km

router = APIRouter(prefix="/api/attribution", tags=["Vessel Attribution & Explainability"])

@router.post("/analyze/{spill_id}", response_model=List[VesselCandidateResponse])
def run_attribution_analysis(
    spill_id: int,
    payload: Optional[AttributionAnalyzeRequest] = None,
    db: Session = Depends(get_db)
):
    spill = db.query(SpillEvent).filter(SpillEvent.id == spill_id).first()
    if not spill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Spill event #{spill_id} does not exist."
        )

    # 1. Fetch or estimate origin geometry and release time
    drift_sim = db.query(DriftSimulation).filter(
        DriftSimulation.spill_event_id == spill.id,
        DriftSimulation.simulation_type == SimulationType.BACKWARD
    ).order_by(DriftSimulation.created_at.desc()).first()

    origin_geom = drift_sim.origin_probability_geometry if drift_sim else spill.spill_geometry
    origin_time = drift_sim.start_time if drift_sim else (spill.detected_at - timedelta(hours=6))

    if spill.centroid and "coordinates" in spill.centroid:
        center_lon, center_lat = spill.centroid["coordinates"][0], spill.centroid["coordinates"][1]
    else:
        center_lon, center_lat = 72.5, 19.0

    radius_km = payload.spatial_radius_km if payload else 50.0
    window_hours = payload.temporal_window_hours if payload else 12.0

    # 2. Fetch all vessels with AIS reports
    vessels = db.query(Vessel).all()
    if not vessels:
        return []

    scorer = AttributionScoringEngine()
    scored_candidates = []

    # Clear previous candidates for this spill to avoid duplicate rows
    db.query(VesselCandidate).filter(VesselCandidate.spill_event_id == spill.id).delete()

    for vessel in vessels:
        positions = db.query(AisPosition).filter(AisPosition.vessel_id == vessel.id).all()
        if not positions:
            continue

        eval_res = scorer.evaluate_vessel(
            vessel=vessel,
            positions=positions,
            origin_geometry_dict=origin_geom,
            origin_center_lat=center_lat,
            origin_center_lon=center_lon,
            origin_time=origin_time,
            temporal_window_hours=window_hours,
            spatial_radius_km=radius_km,
        )

        candidate = VesselCandidate(
            spill_event_id=spill.id,
            vessel_id=vessel.id,
            spatial_score=eval_res["spatial_score"],
            temporal_score=eval_res["temporal_score"],
            trajectory_score=eval_res["trajectory_score"],
            behaviour_score=eval_res["behaviour_score"],
            data_quality_score=eval_res["data_quality_score"],
            overall_score=eval_res["overall_score"],
            priority=eval_res["priority"],
            explanation_json=eval_res["explanation"],
        )
        scored_candidates.append(candidate)

    # Sort descending by overall_score
    scored_candidates.sort(key=lambda c: c.overall_score, reverse=True)

    db.add_all(scored_candidates)
    db.commit()

    for c in scored_candidates:
        db.refresh(c)

    return scored_candidates


@router.post("/run", response_model=List[VesselCandidateResponse])
def run_attribution_analysis_unified(
    payload: AttributionAnalyzeRequest,
    db: Session = Depends(get_db)
):
    """
    Unified endpoint for executing multi-factor explainable vessel attribution scoring.
    """
    return run_attribution_analysis(spill_id=payload.spill_event_id, payload=payload, db=db)


@router.get("/{spill_id}/candidates", response_model=List[VesselCandidateResponse])
def get_candidates_for_spill(spill_id: int, db: Session = Depends(get_db)):
    """Returns ranked candidate vessels for a given spill event."""
    candidates = db.query(VesselCandidate).filter(
        VesselCandidate.spill_event_id == spill_id
    ).order_by(VesselCandidate.overall_score.desc()).all()
    return candidates


@router.get("/{spill_id}/candidate/{candidate_id}", response_model=VesselCandidateResponse)
def get_candidate_details(spill_id: int, candidate_id: int, db: Session = Depends(get_db)):
    """Returns granular attribution score breakdown for a specific candidate vessel."""
    cand = db.query(VesselCandidate).filter(
        VesselCandidate.id == candidate_id,
        VesselCandidate.spill_event_id == spill_id
    ).first()
    if not cand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate #{candidate_id} not found for spill #{spill_id}."
        )
    return cand


@router.get("/{investigation_id}", response_model=List[VesselCandidateResponse])
def get_candidates_for_investigation(investigation_id: int, db: Session = Depends(get_db)):
    """
    Returns ranked candidate vessels for a given spill event or investigation ID.
    """
    candidates = db.query(VesselCandidate).filter(
        VesselCandidate.spill_event_id == investigation_id
    ).order_by(VesselCandidate.overall_score.desc()).all()
    return candidates


