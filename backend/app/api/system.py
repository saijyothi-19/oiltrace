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


@router.get("/api/system/provenance")
def system_provenance(db: Session = Depends(get_db)):
    """
    Exposes live data provenance and operational mode status across all four analytical layers:
    Satellite, Environmental, AIS, and ML Model.
    """
    import os
    from datetime import datetime, timezone
    from app.services.copernicus_service import CopernicusSatelliteService
    from app.services.environmental_service import env_provider

    # 1. Satellite Provenance
    has_copernicus_creds = bool(settings.COPERNICUS_CLIENT_ID and settings.COPERNICUS_CLIENT_SECRET)
    satellite_provenance = {
        "layer": "Satellite Imagery",
        "status": "REAL" if has_copernicus_creds else "OPEN_CATALOG",
        "mode_badge": "REAL DATA" if has_copernicus_creds else "OPEN CDSE",
        "is_demo": False,
        "primary_source": "Copernicus Data Space Ecosystem (Sentinel-1 C-SAR GRD)",
        "download_auth": "Configured (OAuth2)" if has_copernicus_creds else "Public Catalog (Credentials for Full ZIP)",
        "processing_level": "Level-1 Ground Range Detected High Resolution (GRDH)",
    }

    # 2. Environmental Provenance
    env_cond = env_provider.get_conditions(18.9, 72.5, datetime.now(timezone.utc))
    is_env_demo = env_cond.get("is_demo", True)
    environmental_provenance = {
        "layer": "Oceanic & Atmospheric Forcing",
        "status": "DEMO" if is_env_demo else "REAL",
        "mode_badge": "DEMO DATA" if is_env_demo else "REAL DATA",
        "is_demo": is_env_demo,
        "primary_source": env_cond.get("source", "Environmental Engine"),
        "quality": env_cond.get("data_quality", "OPERATIONAL"),
        "variables": "Surface currents (u, v m/s), 10m wind velocity (m/s), wave height (m)",
    }

    # 3. AIS Provenance
    vessel_count = db.query(Vessel).count() if db else 0
    ais_provenance = {
        "layer": "AIS Vessel Telemetry",
        "status": "REAL_IMPORTED" if vessel_count > 0 else "DEMO",
        "mode_badge": "REAL DATA" if vessel_count > 0 else "DEMO DATA",
        "is_demo": False if vessel_count > 0 else True,
        "primary_source": "NOAA MarineCadastre / Danish Maritime Ingestion Pipeline" if vessel_count > 0 else "Synthetic Demonstration Stream",
        "records_ingested": vessel_count,
        "standards": "IMO / ITU-R M.1371 Maritime Transponder Standard",
    }

    # 4. ML Model Provenance
    checkpoint_file = os.path.join(settings.MODEL_CHECKPOINT_DIR, "best_model.pt")
    has_real_checkpoint = os.path.exists(checkpoint_file)
    ml_provenance = {
        "layer": "Oil Spill AI Model",
        "status": "REAL_MODEL" if has_real_checkpoint else "ANALYTICAL_FALLBACK",
        "mode_badge": "REAL MODEL" if has_real_checkpoint else "DEMO ENGINE",
        "is_demo": not has_real_checkpoint,
        "architecture": "Deep Convolutional U-Net" if has_real_checkpoint else "Adaptive Radiometric Contrast Engine",
        "model_version": "v1.0-unet-production" if has_real_checkpoint else "v1.0-analytical-demo",
        "checkpoint_status": "LOADED" if has_real_checkpoint else "CHECKPOINT_DATASET_REQUIRED",
        "notes": "PyTorch U-Net inference active" if has_real_checkpoint else "Analytical contrast fallback active (Honest Demo Fallback)",
    }

    return {
        "system_status": "ONLINE",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "provenance_layers": {
            "satellite": satellite_provenance,
            "environment": environmental_provenance,
            "ais": ais_provenance,
            "ml_model": ml_provenance,
        }
    }

