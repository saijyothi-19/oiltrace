from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db.session import get_db
from app.core.config import settings
from app.schemas.common import SystemStatus
from app.models.spill import SpillEvent
from app.models.investigation import Investigation, InvestigationStatus
from app.models.vessel import Vessel

router = APIRouter(tags=["System"])

def get_ml_device() -> str:
    """Safely detect acceleration device without crashing if C++ DLLs are unavailable."""
    import os
    if os.environ.get("USE_CUDA", "").lower() in ("1", "true"):
        return "cuda"
    return "cpu (optimized numpy/scipy engine)"

@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    
    return {
        "status": "healthy" if db_ok else "degraded",
        "database": "connected" if db_ok else "disconnected",
        "service": settings.PROJECT_NAME,
        "version": "1.0.0-prototype",
    }


@router.get("/api/system/status", response_model=SystemStatus)
def system_status(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    device = get_ml_device()

    active_spills = 0
    active_investigations = 0
    total_vessels = 0

    if db_ok:
        try:
            active_spills = db.query(SpillEvent).count()
            active_investigations = db.query(Investigation).filter(
                Investigation.status.in_([
                    InvestigationStatus.NEW,
                    InvestigationStatus.UNDER_REVIEW,
                    InvestigationStatus.HIGH_PRIORITY
                ])
            ).count()
            total_vessels = db.query(Vessel).count()
        except Exception:
            pass

    return SystemStatus(
        status="ONLINE" if db_ok else "DATABASE_ERROR",
        service=f"{settings.PROJECT_NAME} Marine Decision Support API",
        version="1.0.0-prototype",
        environment=settings.APP_ENV,
        database_connected=db_ok,
        ml_device=device,
        active_spills_count=active_spills,
        active_investigations_count=active_investigations,
        total_vessels_tracked=total_vessels,
    )
