from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.spill import SpillEvent, SpillStatus
from app.schemas.spill import SpillEventResponse, SpillEventCreate, SpillEventUpdate

router = APIRouter(prefix="/api/spills", tags=["Spill Events"])

@router.get("", response_model=List[SpillEventResponse])
def list_spills(
    status_filter: Optional[SpillStatus] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    query = db.query(SpillEvent)
    if status_filter:
        query = query.filter(SpillEvent.status == status_filter)
    return query.order_by(SpillEvent.detected_at.desc()).offset(offset).limit(limit).all()


@router.get("/{id}", response_model=SpillEventResponse)
def get_spill(id: int, db: Session = Depends(get_db)):
    spill = db.query(SpillEvent).filter(SpillEvent.id == id).first()
    if not spill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Spill event #{id} does not exist."
        )
    return spill


@router.post("", response_model=SpillEventResponse, status_code=status.HTTP_201_CREATED)
def create_spill(payload: SpillEventCreate, db: Session = Depends(get_db)):
    spill = SpillEvent(
        satellite_image_id=payload.satellite_image_id,
        detected_at=payload.detected_at or datetime.now(timezone.utc),
        confidence=payload.confidence,
        area_km2=payload.area_km2,
        perimeter_km=payload.perimeter_km,
        centroid=payload.centroid,
        bounding_box=payload.bounding_box,
        spill_geometry=payload.spill_geometry,
        status=payload.status,
        model_version=payload.model_version,
    )
    db.add(spill)
    db.commit()
    db.refresh(spill)
    return spill


@router.patch("/{id}", response_model=SpillEventResponse)
def update_spill(id: int, payload: SpillEventUpdate, db: Session = Depends(get_db)):
    spill = db.query(SpillEvent).filter(SpillEvent.id == id).first()
    if not spill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Spill event #{id} does not exist."
        )

    if payload.status is not None:
        spill.status = payload.status
    if payload.confidence is not None:
        spill.confidence = payload.confidence

    db.commit()
    db.refresh(spill)
    return spill


@router.delete("/{id}")
def delete_spill(id: int, db: Session = Depends(get_db)):
    spill = db.query(SpillEvent).filter(SpillEvent.id == id).first()
    if not spill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Spill event #{id} does not exist."
        )
    db.delete(spill)
    db.commit()
    return {"success": True, "deleted_id": id}
