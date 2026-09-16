import os
import cv2
import json
import tempfile
import numpy as np
import pytest

from ml.preprocessing.sar_preprocessor import SarPreprocessor
from ml.datasets.oil_spill_dataset import SyntheticSarDatasetGenerator, OilSpillDataset
from ml.models.unet.unet_model import UNet
from ml.training.train_config import TrainingConfig
from ml.training.checkpoint import CheckpointManager
from ml.training.train import OilSpillTrainer
from ml.inference.infer import OilSpillInferenceEngine
from ml.evaluation.metrics import calculate_segmentation_metrics
from ml.evaluation.evaluator import ModelEvaluator
from app.geospatial.characterization import SpillCharacterizationEngine


def test_sar_preprocessing_and_tiling():
    """Test DN calibration, Lee speckle filter, normalization, and seamless 2D Hann tile reconstruction."""
    # Synthetic SAR patch (128x128)
    np.random.seed(42)
    raw_dn = np.random.uniform(50.0, 500.0, (128, 128)).astype(np.float32)

    # 1. Calibrate to sigma0 dB
    db = SarPreprocessor.calibrate_to_sigma0_db(raw_dn)
    assert db.shape == (128, 128)
    assert np.all(db > -50.0)

    # 2. Lee Filter
    lee_filtered = SarPreprocessor.lee_filter(db, window_size=5)
    assert lee_filtered.shape == (128, 128)

    # 3. Normalization
    norm = SarPreprocessor.normalize_sar(lee_filtered, min_db=-30.0, max_db=0.0)
    assert np.all(norm >= 0.0) and np.all(norm <= 1.0)

    # 4. Tiling & Reconstructing
    tiles, coords = SarPreprocessor.extract_tiles(norm, tile_size=64, stride=32)
    assert len(tiles) > 0
    assert tiles[0].shape == (64, 64)

    reconstructed = SarPreprocessor.reconstruct_from_tiles(tiles, coords, (128, 128), use_blending=True)
    assert reconstructed.shape == (128, 128)
    assert np.all(reconstructed >= 0.0) and np.all(reconstructed <= 1.0)

    # 5. Probability Heatmap
    heatmap = SarPreprocessor.generate_probability_heatmap(norm, threshold_cut=0.2)
    assert heatmap.shape == (128, 128, 4)


def test_dataset_generator_and_loader():
    """Test synthetic SAR dataset generation and dataset loading with augmentations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        summary = SyntheticSarDatasetGenerator.create_dataset_directory(
            output_dir=tmpdir,
            num_samples=8,
            size=128,
            seed=101
        )
        assert summary["total_samples"] == 8
        assert os.path.exists(os.path.join(tmpdir, "images"))
        assert os.path.exists(os.path.join(tmpdir, "masks"))

        # Load via OilSpillDataset
        ds = OilSpillDataset(
            images_dir=os.path.join(tmpdir, "images"),
            masks_dir=os.path.join(tmpdir, "masks"),
            augment=True,
            target_size=(128, 128)
        )
        assert len(ds) == 8
        sample = ds[0]
        assert "image" in sample
        assert "mask" in sample
        assert "id" in sample


def test_training_config_and_checkpoint_manager():
    """Test training config serialization and checkpoint saving/loading."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg = TrainingConfig(
            num_epochs=5,
            batch_size=2,
            learning_rate=2e-4,
            checkpoint_dir=tmpdir
        )
        cfg_dict = cfg.to_dict()
        assert cfg_dict["num_epochs"] == 5

        mgr = CheckpointManager(checkpoint_dir=tmpdir)
        val_m = {"iou": 0.81, "dice": 0.89, "precision": 0.90, "recall": 0.88, "f1": 0.89}
        saved_path = mgr.save_checkpoint(
            model_state_dict={"weights": "dummy"},
            optimizer_state_dict={},
            epoch=3,
            val_metrics=val_m,
            train_loss=0.15,
            val_loss=0.18,
            config=cfg_dict,
            is_best=True
        )
        assert os.path.exists(saved_path)

        # Inspect checkpoint
        inspected = mgr.inspect_checkpoint(saved_path)
        assert inspected["epoch"] == 3
        assert inspected["val_metrics"]["iou"] == 0.81
        assert inspected["is_best"] is True

        # List checkpoints
        all_ckpts = mgr.list_checkpoints()
        assert len(all_ckpts) >= 1


def test_segmentation_metrics():
    """Test IoU, Dice, Precision, Recall, and F1 calculations against known truth."""
    # Perfect overlap
    y_true = np.ones((10, 10), dtype=np.uint8)
    y_pred = np.ones((10, 10), dtype=np.float32)
    m_perfect = calculate_segmentation_metrics(y_true, y_pred, threshold=0.5)
    assert m_perfect["iou"] == 1.0
    assert m_perfect["dice"] == 1.0
    assert m_perfect["precision"] == 1.0
    assert m_perfect["recall"] == 1.0

    # No overlap
    y_pred_zero = np.zeros((10, 10), dtype=np.float32)
    m_zero = calculate_segmentation_metrics(y_true, y_pred_zero, threshold=0.5)
    assert m_zero["iou"] < 0.001
    assert m_zero["dice"] < 0.001
    assert m_zero["recall"] < 0.001

    # 50% overlap (half true matches pred)
    half_pred = np.zeros((10, 10), dtype=np.float32)
    half_pred[:5, :] = 1.0  # 50 pixels match
    m_half = calculate_segmentation_metrics(y_true, half_pred, threshold=0.5)
    assert 0.49 <= m_half["iou"] <= 0.51
    assert 0.65 <= m_half["dice"] <= 0.68
    assert m_half["precision"] == 1.0
    assert m_half["recall"] == 0.5


def test_batch_model_evaluator():
    """Test batch dataset evaluation and confusion matrix extraction."""
    with tempfile.TemporaryDirectory() as tmpdir:
        SyntheticSarDatasetGenerator.create_dataset_directory(
            output_dir=tmpdir,
            num_samples=4,
            size=64,
            seed=42
        )
        evaluator = ModelEvaluator(threshold=0.5)
        report_path = os.path.join(tmpdir, "eval_report.json")
        res = evaluator.evaluate_dataset(dataset_dir=tmpdir, output_report_path=report_path)

        assert res["total_samples"] == 4
        assert "mean_metrics" in res
        assert "mean_iou" in res["mean_metrics"]
        assert "mean_dice" in res["mean_metrics"]
        assert "confusion_matrix_pixels" in res
        assert os.path.exists(report_path)


def test_geospatial_characterization_and_geojson():
    """Test contour polygonization, WGS84 mapping, area/perimeter, and mask PNG export."""
    # Create mask with circular slick
    mask = np.zeros((200, 200), dtype=np.uint8)
    cv2.circle(mask, (100, 100), 30, 1, -1)
    prob_map = mask.astype(np.float32) * 0.95

    bounds = (72.0, 18.0, 73.0, 19.0)  # 1 deg by 1 deg box
    char_res = SpillCharacterizationEngine.polygonize_and_characterize(
        binary_mask=mask,
        probability_map=prob_map,
        bounds=bounds,
        min_area_km2=0.01
    )
    assert char_res is not None
    assert char_res["spill_detected"] is True
    assert char_res["area_km2"] > 0.0
    assert char_res["perimeter_km"] > 0.0
    assert char_res["confidence"] >= 0.90
    assert char_res["centroid"]["type"] == "Point"

    # GeoJSON Feature formatting
    geojson_feature = SpillCharacterizationEngine.to_geojson_feature(
        char_res, extra_properties={"model_version": "unet-v1.0"}
    )
    assert geojson_feature["type"] == "Feature"
    assert "geometry" in geojson_feature
    assert geojson_feature["properties"]["model_version"] == "unet-v1.0"

    # Mask PNG generation
    mask_rgba = SpillCharacterizationEngine.generate_mask_png(mask)
    assert mask_rgba.shape == (200, 200, 4)
    # Active pixels have alpha = 180
    assert np.any(mask_rgba[:, :, 3] == 180)


def test_fastapi_detection_endpoints(client):
    """Test /api/detection endpoints: models, upload-and-detect, geojson, and mask."""
    # 1. Check models endpoint
    models_resp = client.get("/api/detection/models")
    assert models_resp.status_code == 200
    models_data = models_resp.json()
    assert models_data["active_architecture"] == "UNet"
    assert "Synthetic demonstration data" in models_data["synthetic_watermark"]

    # 2. Upload and detect with synthetic SAR PNG
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
        sar_sample, _, _ = SyntheticSarDatasetGenerator.generate_single_sample(size=128, has_spill=True, seed=99)
        preview_8bit = (sar_sample * 255.0).astype(np.uint8)
        cv2.imwrite(tmp_file.name, preview_8bit)
        tmp_path = tmp_file.name

    try:
        with open(tmp_path, "rb") as f:
            upload_resp = client.post(
                "/api/detection/upload-and-detect",
                files={"file": ("test_sar.png", f, "image/png")},
                data={
                    "threshold": "0.45",
                    "min_area_km2": "0.01",
                    "min_lon": "72.1",
                    "min_lat": "18.6",
                    "max_lon": "72.9",
                    "max_lat": "19.4",
                    "filter_lookalikes": "false",
                    "satellite_name": "Sentinel-1A SAR (Upload Test)",
                }
            )
        assert upload_resp.status_code == 200
        spill_data = upload_resp.json()
        assert "id" in spill_data
        spill_id = spill_data["id"]
        assert spill_data["area_km2"] > 0
        assert spill_data["perimeter_km"] > 0

        # 3. Retrieve GeoJSON Feature
        geo_resp = client.get(f"/api/detection/{spill_id}/geojson")
        assert geo_resp.status_code == 200
        geo_json = geo_resp.json()
        assert geo_json["type"] == "Feature"
        assert geo_json["properties"]["spill_id"] == spill_id

        # 4. Retrieve Mask Image
        mask_resp = client.get(f"/api/detection/{spill_id}/mask?format_type=heatmap")
        assert mask_resp.status_code == 200
        assert mask_resp.headers["content-type"] == "image/png"
        assert len(mask_resp.content) > 100

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
