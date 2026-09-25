"""
OILTRACE — Environmental Forcing & Meteorological API Endpoints.
Supplies real-world or validated demonstration ocean currents and 10m wind fields.
"""
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException, status

from app.services.environmental_service import env_provider, SyntheticEnvironmentalProvider

router = APIRouter(prefix="/api/environment", tags=["Environmental Forcing (Wind & Currents)"])

@router.get("/current")
def get_current_conditions(
    latitude: float = Query(18.9, ge=-90.0, le=90.0),
    longitude: float = Query(72.5, ge=-180.0, le=180.0),
    timestamp: Optional[datetime] = None,
    force_demo: bool = Query(False, description="Force demo climatological provider"),
) -> Dict[str, Any]:
    """
    Returns ocean surface current velocity (u, v m/s) and 10-meter wind fields.
    Queries Copernicus Marine / Open-Meteo live API, or validated climatological demo mode.
    """
    ts = timestamp or datetime.now(timezone.utc)
    provider = SyntheticEnvironmentalProvider() if force_demo else env_provider
    conditions = provider.get_conditions(lat=latitude, lon=longitude, timestamp=ts)
    return conditions


@router.get("/history")
def get_historical_conditions(
    latitude: float = Query(18.9, ge=-90.0, le=90.0),
    longitude: float = Query(72.5, ge=-180.0, le=180.0),
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    step_hours: int = Query(3, ge=1, le=24),
    force_demo: bool = Query(False),
) -> List[Dict[str, Any]]:
    """
    Returns time-series of environmental conditions across a backward/forward drift window.
    """
    now = datetime.now(timezone.utc)
    end_dt = end_time or now
    start_dt = start_time or (end_dt - timedelta(hours=24))

    provider = SyntheticEnvironmentalProvider() if force_demo else env_provider
    series = []
    curr = start_dt

    while curr <= end_dt:
        cond = provider.get_conditions(lat=latitude, lon=longitude, timestamp=curr)
        series.append(cond)
        curr += timedelta(hours=step_hours)

    return series
