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


@router.get("/{id}", response_model=SatelliteImageResponse)
def get_satellite_image(id: int, db: Session = Depends(get_db)):
    image = SatelliteService.get_by_id(db, id)
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Satellite product #{id} not found."
        )
    return image


@router.get("/search", response_model=List[SatelliteImageResponse])
def search_satellite_images(
    satellite: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    query = db.query(SatelliteImage)
    if satellite:
        query = query.filter(SatelliteImage.satellite.ilike(f"%{satellite}%"))
    if start_date:
        query = query.filter(SatelliteImage.acquisition_time >= start_date)
    if end_date:
        query = query.filter(SatelliteImage.acquisition_time <= end_date)
    return query.order_by(SatelliteImage.acquisition_time.desc()).limit(100).all()


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
    if ext not in (".tif", ".tiff", ".png", ".jpg", ".npy", ".nc"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported raster file extension. Supported formats: .tif, .tiff, .png, .npy, .nc"
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
