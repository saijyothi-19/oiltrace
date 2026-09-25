import os
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.satellite import SatelliteImage
from app.schemas.satellite import SatelliteImageResponse
from app.services.satellite_service import SatelliteService
from app.core.config import settings

router = APIRouter(prefix="/api/satellite", tags=["Satellite Imagery"])

@router.get("", response_model=List[SatelliteImageResponse])
def list_satellite_images(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    return SatelliteService.get_all(db, limit, offset)


from app.services.copernicus_service import CopernicusSatelliteService

@router.get("/latest")
def get_latest_satellite_acquisition(
    latitude: float = Query(18.9, ge=-90.0, le=90.0),
    longitude: float = Query(72.5, ge=-180.0, le=180.0),
    radius_km: float = Query(50.0, gt=0, le=500.0),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
):
    """
    Retrieves the Latest Available Sentinel-1 Acquisition over the region of interest.
    Strictly marked as 'Latest Available Sentinel-1 Acquisition' to avoid misleading 'live feed' claims.
    """
    return CopernicusSatelliteService.get_latest_acquisition(
        lat=latitude,
        lon=longitude,
        radius_km=radius_km,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/cdse/search")
def search_copernicus_catalog(
    min_lon: float = Query(72.0, ge=-180.0, le=180.0),
    min_lat: float = Query(18.0, ge=-90.0, le=90.0),
    max_lon: float = Query(73.5, ge=-180.0, le=180.0),
    max_lat: float = Query(19.8, ge=-90.0, le=90.0),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    polarization: Optional[str] = Query(None, description="e.g. VV, VH, VV+VH"),
    orbit_direction: Optional[str] = Query(None, description="ASCENDING or DESCENDING"),
    limit: int = Query(20, ge=1, le=100),
):
    """
    Direct spatial-temporal search of the European Copernicus Data Space Ecosystem (CDSE)
    for Sentinel-1 C-SAR Ground Range Detected (GRD) acquisitions.
    """
    return CopernicusSatelliteService.search_acquisitions(
        min_lon=min_lon,
        min_lat=min_lat,
        max_lon=max_lon,
        max_lat=max_lat,
        start_date=start_date,
        end_date=end_date,
        polarization=polarization,
        orbit_direction=orbit_direction,
        limit=limit,
    )


@router.get("/search")
def search_satellite_images(
    satellite: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    live_cdse: bool = Query(False, description="Search live Copernicus CDSE if True"),
    min_lon: Optional[float] = None,
    min_lat: Optional[float] = None,
    max_lon: Optional[float] = None,
    max_lat: Optional[float] = None,
    db: Session = Depends(get_db)
):
    if live_cdse and min_lon is not None and min_lat is not None and max_lon is not None and max_lat is not None:
        return CopernicusSatelliteService.search_acquisitions(
            min_lon=min_lon,
            min_lat=min_lat,
            max_lon=max_lon,
            max_lat=max_lat,
            start_date=start_date,
            end_date=end_date,
        )

    query = db.query(SatelliteImage)
    if satellite:
        query = query.filter(SatelliteImage.satellite.ilike(f"%{satellite}%"))
    if start_date:
        query = query.filter(SatelliteImage.acquisition_time >= start_date)
    if end_date:
        query = query.filter(SatelliteImage.acquisition_time <= end_date)
    return query.order_by(SatelliteImage.acquisition_time.desc()).limit(100).all()


@router.get("/{id}", response_model=SatelliteImageResponse)
def get_satellite_image(id: int, db: Session = Depends(get_db)):
    image = SatelliteService.get_by_id(db, id)
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Satellite product #{id} not found."
        )
    return image


@router.post("/upload", response_model=SatelliteImageResponse, status_code=status.HTTP_201_CREATED)
async def upload_satellite_image(
    file: UploadFile = File(...),
    product_id: Optional[str] = Form(None),
    satellite: str = Form("Sentinel-1A"),
    sensor: str = Form("C-SAR"),
    polarization: str = Form("VV"),
    orbit: str = Form("DESCENDING"),
    min_lat: float = Form(18.5),
    max_lat: float = Form(19.5),
    min_lon: float = Form(72.0),
    max_lon: float = Form(73.0),
    db: Session = Depends(get_db)
):
    # Validate extension
    filename = file.filename or "scene.tif"
    ext = os.path.splitext(filename)[1].lower()
    allowed_exts = (".tif", ".tiff", ".png", ".jpg", ".jpeg", ".npy", ".nc", ".webp")
    if ext not in allowed_exts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format. Please upload .tif, .png, .npy, .jpg, .jpeg, or .webp."
        )

    # Save file outside executable directories
    target_dir = os.path.join(settings.DATA_DIR, "satellite")
    os.makedirs(target_dir, exist_ok=True)
    clean_id = product_id or f"S1A_IW_GRDH_1SDV_{uuid.uuid4().hex[:12].upper()}"
    saved_path = os.path.join(target_dir, f"{clean_id}{ext}")

    content = await file.read()
    with open(saved_path, "wb") as f:
        f.write(content)

    # Bounding polygon GeoJSON
    bounding_geom = {
        "type": "Polygon",
        "coordinates": [[
            [min_lon, min_lat],
            [max_lon, min_lat],
            [max_lon, max_lat],
            [min_lon, max_lat],
            [min_lon, min_lat],
        ]]
    }

    image = SatelliteService.create_satellite_image(
        db=db,
        product_id=clean_id,
        file_path=saved_path,
        acquisition_time=datetime.now(timezone.utc),
        satellite=satellite,
        sensor=sensor,
        polarization=polarization,
        orbit=orbit,
        bounding_geometry=bounding_geom,
    )
    return image
