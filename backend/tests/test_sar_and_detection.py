import os
import numpy as np
import cv2
import pytest
from fastapi.testclient import TestClient
from app.main import app
from ml.preprocessing.sar_preprocessor import SarPreprocessor
from ml.evaluation.lookalike_filter import RuleBasedLookAlikeFilter
from ml.evaluation.metrics import calculate_segmentation_metrics
from app.geospatial.characterization import SpillCharacterizationEngine

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def test_sar_preprocessing_synthetic_raster(tmp_path):
    # Create synthetic SAR raster with bright sea clutter (DN ~ 200) and dark oil patch (DN ~ 30)
    raster_path = str(tmp_path / "synthetic_s1.png")
    synthetic_dn = np.random.normal(loc=180.0, scale=20.0, size=(128, 128)).astype(np.float32)
    # Add dark oil spill blob
    synthetic_dn[40:80, 40:80] = np.random.normal(loc=35.0, scale=8.0, size=(40, 40))
    synthetic_dn = np.clip(synthetic_dn, 0.0, 255.0).astype(np.uint8)
    cv2.imwrite(raster_path, synthetic_dn)

    # Run preprocessing
    output_preview = str(tmp_path / "processed_s1.png")
    result = SarPreprocessor.preprocess_sar(raster_path, output_preview)
    norm = result["processed_array"]

    assert norm.shape == (128, 128)
    assert 0.0 <= result["min_val"] <= 1.0
    assert 0.0 <= result["max_val"] <= 1.0
    assert os.path.exists(output_preview)

    # Test tile extraction
    tiles, coords = SarPreprocessor.extract_tiles(norm, tile_size=64, stride=64)
    assert len(tiles) == 4
    assert tiles.shape == (4, 64, 64)

def test_lookalike_filter():
    filter_engine = RuleBasedLookAlikeFilter(min_reliable_wind_mps=2.5)
    dummy_patch = np.ones((64, 64), dtype=np.float32) * 0.8

    # Case 1: Low wind calm zone
    eval_low_wind = filter_engine.evaluate_candidate(dummy_patch, wind_speed_mps=1.2)
    assert "LOW_WIND_CALM_ZONE_SUSPECTED" in eval_low_wind["flags"]
    assert eval_low_wind["lookalike_probability"] >= 0.5

    # Case 2: Normal marine wind
    eval_normal = filter_engine.evaluate_candidate(dummy_patch, wind_speed_mps=6.5)
    assert "LOW_WIND_CALM_ZONE_SUSPECTED" not in eval_normal["flags"]

def test_segmentation_metrics():
    y_true = np.zeros((32, 32), dtype=np.float32)
    y_true[10:20, 10:20] = 1.0

    y_pred = np.zeros((32, 32), dtype=np.float32)
    y_pred[10:20, 10:20] = 0.95  # Exact prediction

    metrics = calculate_segmentation_metrics(y_true, y_pred, threshold=0.5)
    assert metrics["iou"] > 0.95
    assert metrics["dice"] > 0.95
    assert metrics["f1"] > 0.95

def test_spill_characterization():
    # Synthetic binary mask with an oil patch
    mask = np.zeros((100, 100), dtype=np.uint8)
    mask[30:70, 30:70] = 1
    prob = mask.astype(np.float32) * 0.92

    bounds = (72.0, 18.0, 73.0, 19.0)
    char = SpillCharacterizationEngine.polygonize_and_characterize(
        binary_mask=mask,
        probability_map=prob,
        bounds=bounds,
        min_area_km2=0.01
    )
    assert char is not None
    assert char["spill_detected"] is True
    assert char["area_km2"] > 0.0
    assert char["perimeter_km"] > 0.0
    assert char["confidence"] >= 0.85
    assert "coordinates" in char["centroid"]

def test_spills_api_crud(client):
    # Create spill
    create_payload = {
        "confidence": 0.92,
        "area_km2": 14.5,
        "perimeter_km": 18.2,
        "centroid": {"type": "Point", "coordinates": [72.5, 18.9]},
        "spill_geometry": {
            "type": "Polygon",
            "coordinates": [[[72.4, 18.8], [72.6, 18.8], [72.6, 19.0], [72.4, 19.0], [72.4, 18.8]]]
        },
        "status": "DETECTED",
        "model_version": "unet-v1.0-baseline"
    }
    resp = client.post("/api/spills", json=create_payload)
    assert resp.status_code == 201
    spill_data = resp.json()
    spill_id = spill_data["id"]
    assert spill_data["area_km2"] == 14.5

    # Get spill
    get_resp = client.get(f"/api/spills/{spill_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == spill_id

    # Update spill (Accept detection)
    patch_resp = client.patch(f"/api/spills/{spill_id}", json={"status": "ACCEPTED"})
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "ACCEPTED"


def test_webp_preprocessing_and_decoding(tmp_path):
    from PIL import Image
    # Create valid synthetic WebP image
    webp_path = str(tmp_path / "test_scene.webp")
    arr = np.random.randint(50, 220, size=(128, 128), dtype=np.uint8)
    arr[40:70, 40:70] = 25  # simulated dark slick feature
    img = Image.fromarray(arr)
    img.save(webp_path, "WEBP")

    # Verify SarPreprocessor loads and normalizes WebP
    result = SarPreprocessor.preprocess_sar(webp_path)
    norm = result["processed_array"]
    assert norm.shape == (128, 128)
    assert norm.dtype == np.float32
    assert 0.0 <= result["min_val"] <= 1.0
    assert 0.0 <= result["max_val"] <= 1.0


def test_webp_upload_and_detect(client, tmp_path):
    import io
    from PIL import Image
    # Generate valid WebP bytes
    arr = np.full((128, 128), 180, dtype=np.uint8)
    arr[30:70, 30:70] = 30  # Dark slick patch
    pil_img = Image.fromarray(arr)
    buf = io.BytesIO()
    pil_img.save(buf, format="WEBP")
    buf.seek(0)

    files = {"file": ("sar_scene.webp", buf.getvalue(), "image/webp")}
    data = {
        "threshold": "0.4",
        "min_area_km2": "0.001",
        "min_lon": "72.1",
        "min_lat": "18.6",
        "max_lon": "72.9",
        "max_lat": "19.4",
        "filter_lookalikes": "false"
    }
    resp = client.post("/api/detection/upload-and-detect", files=files, data=data)
    assert resp.status_code in (200, 201)
    json_data = resp.json()
    assert "id" in json_data or "spill_detected" in str(json_data)


def test_corrupted_webp_upload_rejected(client):
    files = {"file": ("corrupted.webp", b"NOT_A_REAL_WEBP_IMAGE_CONTENT_DATA", "image/webp")}
    data = {"threshold": "0.5"}
    resp = client.post("/api/detection/upload-and-detect", files=files, data=data)
    assert resp.status_code == 400
    assert "Corrupted or invalid" in resp.json().get("error", {}).get("message", "") or "Corrupted or invalid" in resp.text


def test_unsupported_file_extension_rejected(client):
    files = {"file": ("notes.txt", b"This is a text file, not a raster.", "text/plain")}
    data = {"threshold": "0.5"}
    resp = client.post("/api/detection/upload-and-detect", files=files, data=data)
    assert resp.status_code == 400
    assert "Unsupported file format" in resp.json().get("error", {}).get("message", "") or "Unsupported file format" in resp.text

