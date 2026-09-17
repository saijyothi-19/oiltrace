import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
import io
import uuid
import cv2
import numpy as np
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, status
from fastapi.responses import Response, StreamingResponse, JSONResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.satellite import SatelliteImage
from app.models.spill import SpillEvent, SpillDetection, SpillStatus
from app.schemas.spill import DetectionRunRequest, SpillEventResponse
from app.core.config import settings

from ml.preprocessing.sar_preprocessor import SarPreprocessor
from ml.inference.infer import OilSpillInferenceEngine
from ml.training.train_config import TrainingConfig
from ml.training.train import OilSpillTrainer
from ml.training.checkpoint import CheckpointManager
from app.geospatial.characterization import SpillCharacterizationEngine

router = APIRouter(prefix="/api/detection", tags=["AI Spill Detection"])


@router.post("/run", response_model=SpillEventResponse)
def run_detection(payload: DetectionRunRequest, db: Session = Depends(get_db)):
    sat_img = db.query(SatelliteImage).filter(SatelliteImage.id == payload.satellite_image_id).first()
    if not sat_img:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Satellite image #{payload.satellite_image_id} not found."
        )

    # 1. SAR Preprocessing
    try:
        prep_result = SarPreprocessor.preprocess_sar(sat_img.file_path)
        norm_array = prep_result["processed_array"]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"SAR preprocessing pipeline failed: {e}"
        )

    # 2. AI Inference
    engine = OilSpillInferenceEngine(
        threshold=payload.threshold,
        filter_lookalikes=payload.filter_lookalikes
    )
    seg_result = engine.segment_sar_array(norm_array)
    prob_map = seg_result["probability_map"]
    binary_mask = seg_result["binary_mask"]

    # 3. Spatial Bounds extraction
    bounds = (72.0, 18.5, 73.0, 19.5)  # default Arabian Sea
    if sat_img.bounding_geometry and "coordinates" in sat_img.bounding_geometry:
        coords = sat_img.bounding_geometry["coordinates"][0]
        lons = [c[0] for c in coords]
        lats = [c[1] for c in coords]
        bounds = (min(lons), min(lats), max(lons), max(lats))

    # 4. Spill Characterization
    char_result = SpillCharacterizationEngine.polygonize_and_characterize(
        binary_mask=binary_mask,
        probability_map=prob_map,
        bounds=bounds,
        min_area_km2=payload.min_area_km2
    )

    if not char_result or not char_result.get("spill_detected"):
        raise HTTPException(
            status_code=status.HTTP_200_OK,
            detail="Analysis completed: No probable oil spill detected exceeding the area threshold."
        )

    # 5. Persist Spill Event
    spill = SpillEvent(
        satellite_image_id=sat_img.id,
        detected_at=sat_img.acquisition_time or datetime.now(timezone.utc),
        confidence=char_result["confidence"],
        area_km2=char_result["area_km2"],
        perimeter_km=char_result["perimeter_km"],
        centroid=char_result["centroid"],
        bounding_box=char_result["bounding_box"],
        spill_geometry=char_result["geometry"],
        status=SpillStatus.DETECTED,
        model_version="unet-v1.0-baseline",
    )
    db.add(spill)
    db.flush()

    # Persist Spill Detection Run Record
    detection_rec = SpillDetection(
        spill_event_id=spill.id,
        model_name="U-Net",
        model_version="v1.0",
        confidence=char_result["confidence"],
        polygon=char_result["geometry"],
        metadata_json={
            "threshold": payload.threshold,
            "lookalike_evaluation": seg_result.get("lookalike_evaluation", {}),
            "spill_pixel_count": seg_result.get("spill_pixel_count", 0),
        },
    )
    db.add(detection_rec)
    db.commit()
    db.refresh(spill)

    return spill


@router.post("/upload-and-detect", response_model=SpillEventResponse)
async def upload_and_detect(
    file: UploadFile = File(...),
    threshold: float = Form(0.5),
    min_area_km2: float = Form(0.01),
    min_lon: float = Form(72.0),
    min_lat: float = Form(18.5),
    max_lon: float = Form(73.0),
    max_lat: float = Form(19.5),
    filter_lookalikes: bool = Form(True),
    satellite_name: str = Form("Sentinel-1A SAR"),
    polarization: str = Form("VV"),
    db: Session = Depends(get_db)
):
    """
    Directly uploads a raw SAR raster (TIFF, PNG, JPG, NPY), executes the complete
    end-to-end preprocessing, U-Net inference, geospatial polygonization pipeline,
    and creates both a SatelliteImage record and a SpillEvent record.
    """
    # 1. Extension & Format Validation
    filename = file.filename or ""
    ext = os.path.splitext(filename)[1].lower()
    allowed_exts = {".tif", ".tiff", ".png", ".jpg", ".jpeg", ".npy", ".webp"}
    if ext not in allowed_exts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format. Please upload .tif, .png, .npy, .jpg, .jpeg, or .webp."
        )

    # 2. MIME type check if present
    if file.content_type:
        allowed_mimes = (
            "image/tiff", "image/png", "image/jpeg", "image/webp",
            "application/octet-stream", "application/x-numpy", "binary/octet-stream"
        )
        if not (file.content_type.startswith("image/") or file.content_type in allowed_mimes):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported file format. Please upload .tif, .png, .npy, .jpg, .jpeg, or .webp."
            )

    contents = await file.read()

    # 3. File size validation (50 MB limit)
    max_size_bytes = 50 * 1024 * 1024
    if len(contents) > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds the 50MB limit."
        )
    if len(contents) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty."
        )

    # 4. Image corruption / validity verification
    if ext in (".png", ".jpg", ".jpeg", ".webp"):
        from PIL import Image
        try:
            with Image.open(io.BytesIO(contents)) as test_img:
                test_img.verify()
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Corrupted or invalid {ext.upper().lstrip('.')} image file."
            )

    # Save uploaded file
    upload_dir = os.path.join(settings.DATA_DIR, "satellite", "uploads")
    os.makedirs(upload_dir, exist_ok=True)

    file_id = f"{uuid.uuid4().hex[:12]}_{filename}"
    file_path = os.path.join(upload_dir, file_id)
    with open(file_path, "wb") as f:
        f.write(contents)

    # Create bounding polygon
    bounds = (min_lon, min_lat, max_lon, max_lat)
    bounding_geom = {
        "type": "Polygon",
        "coordinates": [[
            [min_lon, min_lat],
            [max_lon, min_lat],
            [max_lon, max_lat],
            [min_lon, max_lat],
            [min_lon, min_lat]
        ]]
    }

    # Persist SatelliteImage
    sat_img = SatelliteImage(
        product_id=f"SAR_UPLOAD_{uuid.uuid4().hex[:8].upper()}",
        satellite=satellite_name,
        sensor="C-SAR",
        polarization=polarization,
        acquisition_time=datetime.now(timezone.utc),
        file_path=file_path,
        bounding_geometry=bounding_geom,
    )
    db.add(sat_img)
    db.flush()

    # Preprocess & Predict
    try:
        prep = SarPreprocessor.preprocess_sar(file_path)
        norm_array = prep["processed_array"]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to decode or preprocess uploaded SAR file: {e}"
        )

    engine = OilSpillInferenceEngine(
        threshold=threshold,
        filter_lookalikes=filter_lookalikes
    )
    seg_result = engine.segment_sar_array(norm_array)
    prob_map = seg_result["probability_map"]
    binary_mask = seg_result["binary_mask"]

    char_result = SpillCharacterizationEngine.polygonize_and_characterize(
        binary_mask=binary_mask,
        probability_map=prob_map,
        bounds=bounds,
        min_area_km2=min_area_km2
    )

    if not char_result or not char_result.get("spill_detected"):
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_200_OK,
            detail="SAR image processed successfully. No oil spill formations detected exceeding the area threshold."
        )

    spill = SpillEvent(
        satellite_image_id=sat_img.id,
        detected_at=sat_img.acquisition_time,
        confidence=char_result["confidence"],
        area_km2=char_result["area_km2"],
        perimeter_km=char_result["perimeter_km"],
        centroid=char_result["centroid"],
        bounding_box=char_result["bounding_box"],
        spill_geometry=char_result["geometry"],
        status=SpillStatus.DETECTED,
        model_version="unet-v1.0-baseline",
    )
    db.add(spill)
    db.flush()

    detection_rec = SpillDetection(
        spill_event_id=spill.id,
        model_name="U-Net",
        model_version="v1.0",
        confidence=char_result["confidence"],
        polygon=char_result["geometry"],
        metadata_json={
            "threshold": threshold,
            "lookalike_evaluation": seg_result.get("lookalike_evaluation", {}),
            "pixel_area_km2": char_result["area_km2"],
        },
    )
    db.add(detection_rec)
    db.commit()
    db.refresh(spill)

    return spill


@router.get("/models")
def get_model_status():
    """
    Returns available checkpoints, active baseline model status, and training history summary.
    """
    mgr = CheckpointManager(checkpoint_dir="./ml/models/unet/checkpoints")
    checkpoints = mgr.list_checkpoints()

    history_path = os.path.join(mgr.checkpoint_dir, "training_history.json")
    history_summary = {}
    if os.path.exists(history_path):
        try:
            import json
            with open(history_path, "r", encoding="utf-8") as f:
                h_data = json.load(f)
                history_summary = {
                    "best_epoch": h_data.get("best_epoch"),
                    "best_val_iou": h_data.get("best_val_iou"),
                    "timestamp": h_data.get("timestamp"),
                    "epochs_trained": len(h_data.get("history", {}).get("epochs", [])),
                }
        except Exception:
            pass

    return {
        "active_architecture": "UNet",
        "version": "v1.0-baseline",
        "total_checkpoints": len(checkpoints),
        "checkpoints": checkpoints,
        "latest_training": history_summary,
        "supported_input": "Single-channel SAR (VV/VH backscatter)",
        "synthetic_watermark": "Synthetic demonstration data — not real-world evidence."
    }


@router.post("/train")
def trigger_training(
    num_epochs: int = Query(3, ge=1, le=50),
    batch_size: int = Query(4, ge=1, le=32),
    learning_rate: float = Query(1e-4, gt=0),
    dataset_dir: str = Query("./data/synthetic/oil_spill_training")
):
    """
    Executes the U-Net training pipeline on the designated dataset directory.
    If no labelled dataset is configured, creates a synthetic demonstration dataset.
    """
    cfg = TrainingConfig(
        num_epochs=num_epochs,
        batch_size=batch_size,
        learning_rate=learning_rate,
        dataset_dir=dataset_dir,
    )
    trainer = OilSpillTrainer(cfg)
    result = trainer.train()
    return result


@router.get("/{spill_id}/geojson")
def get_spill_geojson(spill_id: int, db: Session = Depends(get_db)):
    """
    Returns an RFC 7946 compliant GeoJSON Feature representation of the detected spill.
    """
    spill = db.query(SpillEvent).filter(SpillEvent.id == spill_id).first()
    if not spill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Spill #{spill_id} not found."
        )

    feature = SpillCharacterizationEngine.to_geojson_feature(
        char_result={
            "spill_detected": True,
            "confidence": spill.confidence,
            "area_km2": spill.area_km2,
            "perimeter_km": spill.perimeter_km,
            "centroid": spill.centroid,
            "bounding_box": spill.bounding_box,
            "geometry": spill.spill_geometry,
        },
        extra_properties={
            "spill_id": spill.id,
            "detected_at": spill.detected_at.isoformat() if spill.detected_at else None,
            "status": spill.status.value,
            "model_version": spill.model_version,
            "disclaimer": settings.DISCLAIMER_TEXT,
        }
    )
    return feature


@router.get("/{spill_id}/mask")
def get_spill_mask_image(
    spill_id: int,
    format_type: str = Query("heatmap", pattern="^(heatmap|binary)$"),
    db: Session = Depends(get_db)
):
    """
    Generates and returns an RGBA PNG overlay (probability heatmap or binary mask).
    """
    spill = db.query(SpillEvent).filter(SpillEvent.id == spill_id).first()
    if not spill or not spill.satellite_image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Spill #{spill_id} or associated satellite image not found."
        )

    try:
        prep = SarPreprocessor.preprocess_sar(spill.satellite_image.file_path)
        engine = OilSpillInferenceEngine(threshold=0.5)
        seg = engine.segment_sar_array(prep["processed_array"])

        if format_type == "heatmap":
            rgba = seg.get("heatmap_rgba")
            if rgba is None:
                rgba = SarPreprocessor.generate_probability_heatmap(seg["probability_map"])
        else:
            rgba = SpillCharacterizationEngine.generate_mask_png(seg["binary_mask"])

        # Encode to PNG buffer
        success, buffer = cv2.imencode(".png", rgba)
        if not success:
            raise ValueError("Failed to encode mask image to PNG.")

        return Response(content=buffer.tobytes(), media_type="image/png")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate mask image: {e}"
        )


@router.get("/{id}/result")
def get_detection_result(id: int, db: Session = Depends(get_db)):
    det = db.query(SpillDetection).filter(SpillDetection.id == id).first()
    if not det:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Detection run #{id} not found."
        )
    return {
        "id": det.id,
        "spill_event_id": det.spill_event_id,
        "model_name": det.model_name,
        "confidence": det.confidence,
        "polygon": det.polygon,
        "metadata": det.metadata_json,
        "created_at": det.created_at,
    }
