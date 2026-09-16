from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.investigation import Investigation, InvestigationStatus
from app.models.spill import SpillEvent
from app.schemas.investigation import InvestigationResponse, InvestigationCreate, InvestigationUpdate
from app.core.security import get_current_user

router = APIRouter(prefix="/api/investigations", tags=["Investigation Workflow"])

@router.get("", response_model=List[InvestigationResponse])
def list_investigations(
    status_filter: Optional[InvestigationStatus] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    query = db.query(Investigation)
    if status_filter:
        query = query.filter(Investigation.status == status_filter)
    return query.order_by(Investigation.updated_at.desc()).offset(offset).limit(limit).all()


@router.get("/{id}", response_model=InvestigationResponse)
def get_investigation(id: int, db: Session = Depends(get_db)):
    inv = db.query(Investigation).filter(Investigation.id == id).first()
    if not inv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation case #{id} does not exist."
        )
    return inv


@router.post("", response_model=InvestigationResponse, status_code=status.HTTP_201_CREATED)
def create_investigation(payload: InvestigationCreate, db: Session = Depends(get_db)):
    spill = db.query(SpillEvent).filter(SpillEvent.id == payload.spill_event_id).first()
    if not spill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Spill event #{payload.spill_event_id} does not exist."
        )

    # Check if an investigation already exists for this spill
    existing = db.query(Investigation).filter(Investigation.spill_event_id == payload.spill_event_id).first()
    if existing:
        return existing

    inv = Investigation(
        spill_event_id=payload.spill_event_id,
        assigned_to=payload.assigned_to,
        status=payload.status,
        notes=payload.notes or f"Investigation initiated for Spill #{payload.spill_event_id}",
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)
    return inv


@router.patch("/{id}", response_model=InvestigationResponse)
def update_investigation(id: int, payload: InvestigationUpdate, db: Session = Depends(get_db)):
    inv = db.query(Investigation).filter(Investigation.id == id).first()
    if not inv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation case #{id} does not exist."
        )

    if payload.status is not None:
        inv.status = payload.status
    if payload.notes is not None:
        inv.notes = payload.notes
    if payload.assigned_to is not None:
        inv.assigned_to = payload.assigned_to

    inv.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(inv)
    return inv
