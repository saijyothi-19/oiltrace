import csv
import io
import json
import time
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.vessel import Vessel, AisPosition
from app.schemas.ais import VesselResponse, AisPositionResponse, AisImportResponse
from app.ais.cleaner import AisRecordCleaner
from app.ais.spatial_filter import AisSpatialFilter
from app.core.security import get_current_user

router = APIRouter(prefix="/api/ais", tags=["AIS & Vessels"])

@router.get("/vessels", response_model=List[VesselResponse])
def list_vessels(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    return db.query(Vessel).offset(offset).limit(limit).all()


@router.get("/vessel/{mmsi}", response_model=VesselResponse)
def get_vessel_by_mmsi(mmsi: str, db: Session = Depends(get_db)):
    vessel = db.query(Vessel).filter(Vessel.mmsi == mmsi).first()
    if not vessel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vessel with MMSI {mmsi} not found in registry."
        )
    return vessel


@router.get("/vessel/{mmsi}/track", response_model=List[AisPositionResponse])
def get_vessel_track(
    mmsi: str,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = Query(1000, ge=1, le=5000),
    db: Session = Depends(get_db)
):
    vessel = db.query(Vessel).filter(Vessel.mmsi == mmsi).first()
    if not vessel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vessel with MMSI {mmsi} not found."
        )

    query = db.query(AisPosition).filter(AisPosition.vessel_id == vessel.id)
    if start_time:
        query = query.filter(AisPosition.timestamp >= start_time)
    if end_time:
        query = query.filter(AisPosition.timestamp <= end_time)

    positions = query.order_by(AisPosition.timestamp.asc()).limit(limit).all()
    return positions


@router.get("/track/{mmsi}", response_model=List[AisPositionResponse])
def get_vessel_track_alias(
    mmsi: str,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = Query(1000, ge=1, le=5000),
    db: Session = Depends(get_db)
):
    """Unified route alias for fetching chronological vessel waypoints."""
    return get_vessel_track(mmsi=mmsi, start_time=start_time, end_time=end_time, limit=limit, db=db)


@router.get("/vessel/{mmsi}/anomalies")
def get_vessel_behaviour_anomalies(
    mmsi: str,
    origin_lat: Optional[float] = Query(None),
    origin_lon: Optional[float] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Evaluates vessel trajectory for sudden deceleration, sharp turns, loitering, and AIS blackouts.
    Results are clearly flagged as decision-support indicators, not proof of illegal activity.
    """
    from app.ais.anomaly import VesselBehaviourAnomalyDetector
    vessel = db.query(Vessel).filter(Vessel.mmsi == mmsi).first()
    if not vessel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vessel with MMSI {mmsi} not found."
        )

    positions = db.query(AisPosition).filter(AisPosition.vessel_id == vessel.id).order_by(AisPosition.timestamp.asc()).all()
    analysis = VesselBehaviourAnomalyDetector.analyze_trajectory(
        positions=positions,
        origin_lat=origin_lat,
        origin_lon=origin_lon,
    )
    analysis["vessel"] = {
        "mmsi": vessel.mmsi,
        "name": vessel.name,
        "ship_type": vessel.ship_type,
        "flag": vessel.flag,
    }
    return analysis


@router.get("/nearby")
def get_nearby_vessels(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(50.0, gt=0, le=500),
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    results = AisSpatialFilter.find_nearby_vessels(
        db=db,
        center_lat=lat,
        center_lon=lon,
        radius_km=radius_km,
        start_time=start_time,
        end_time=end_time,
    )
    return [
        {
            "vessel": VesselResponse.model_validate(r["vessel"]),
            "positions_count": r["positions_count"],
            "closest_distance_km": round(r["closest_distance_km"], 2),
        }
        for r in results
    ]


@router.post("/import", response_model=AisImportResponse)
async def import_ais_data(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    start_wall = time.time()
    contents = await file.read()
    filename = file.filename or ""

    raw_rows = []
    if filename.endswith(".json"):
        try:
            data = json.loads(contents.decode("utf-8"))
            raw_rows = data if isinstance(data, list) else data.get("records", [])
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Malformed JSON payload: {e}"
            )
    else:  # Assume CSV
        try:
            text_stream = io.StringIO(contents.decode("utf-8", errors="replace"))
            reader = csv.DictReader(text_stream)
            raw_rows = list(reader)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Malformed CSV payload: {e}"
            )

    cleaned_records = []
    for r in raw_rows:
        cleaned = AisRecordCleaner.clean_record(r)
        if cleaned:
            cleaned_records.append(cleaned)

    if not cleaned_records:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid AIS records parsed from the uploaded file."
        )

    # Ingest into database
    vessels_cache = {}
    vessels_updated = set()
    positions_to_insert = []

    for item in cleaned_records:
        mmsi = item["mmsi"]
        if mmsi not in vessels_cache:
            vessel = db.query(Vessel).filter(Vessel.mmsi == mmsi).first()
            if not vessel:
                vessel = Vessel(
                    mmsi=mmsi,
                    name=item["name"],
                    ship_type=item["ship_type"],
                    flag="India",
                )
                db.add(vessel)
                db.flush()
            vessels_cache[mmsi] = vessel

        vessel = vessels_cache[mmsi]
        vessels_updated.add(vessel.id)

        pos = AisPosition(
            vessel_id=vessel.id,
            timestamp=item["timestamp"],
            position={"type": "Point", "coordinates": [item["lon"], item["lat"]]},
            speed=item["speed"],
            course=item["course"],
            heading=item["heading"],
            navigation_status=item["navigation_status"],
        )
        positions_to_insert.append(pos)

    db.add_all(positions_to_insert)
    db.commit()

    duration = round(time.time() - start_wall, 3)
    return AisImportResponse(
        imported_records=len(positions_to_insert),
        vessels_updated=len(vessels_updated),
        duration_seconds=duration,
        message=f"Successfully imported {len(positions_to_insert)} AIS records across {len(vessels_updated)} vessels.",
    )
