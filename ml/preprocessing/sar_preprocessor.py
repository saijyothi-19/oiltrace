import os
import math
import numpy as np
import cv2
import tifffile
from PIL import Image
from typing import Dict, Any, Tuple, Optional, List

class SarPreprocessor:
    """
    Reproducible Sentinel-1 SAR Preprocessing Pipeline:
    1. Digital Number (DN) ingestion from GeoTIFF/TIFF/PNG/NPY
    2. Radiometric calibration to sigma0 backscatter decibels (dB)
    3. Adaptive Lee speckle noise reduction
    4. Dynamic range clipping (-30 dB to 0 dB) and [0, 1] normalization
    5. Sliding window tile extraction
    """

    @staticmethod
    def load_raster(input_path: str, polarization: str = "VV") -> np.ndarray:
        """Loads single-band or multi-band raster as float32 2D array."""
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"SAR raster not found at: {input_path}")

        ext = os.path.splitext(input_path)[1].lower()
        if ext in (".tif", ".tiff"):
            img = tifffile.imread(input_path)
            if img.ndim == 3:
                # Sentinel-1 GRD products: Channel 0 is VV (co-polarized), Channel 1 is VH (cross-polarized)
                if polarization.upper() == "VH" and img.shape[0] > 1:
                    img = img[1]
                else:
                    img = img[0]  # Primary polarization (default VV)
            return img.astype(np.float32)
        elif ext in (".npy",):
            arr = np.load(input_path)
            if arr.ndim == 3:
                arr = arr[0] if arr.shape[0] < arr.shape[2] else arr[:, :, 0]
            return arr.astype(np.float32)
        elif ext in (".webp",):
            # WebP decoding: Pillow handles RGB, RGBA, and lossy/lossless WebP variants
            try:
                with Image.open(input_path) as pil_img:
                    gray_img = pil_img.convert("L")
                    return np.array(gray_img, dtype=np.float32)
            except Exception as e:
                img = cv2.imread(input_path, cv2.IMREAD_GRAYSCALE)
                if img is None:
                    raise ValueError(f"Corrupted or unreadable WebP image: {e}")
                return img.astype(np.float32)
        else:
            # Fallback to OpenCV / Pillow
            img = cv2.imread(input_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                pil_img = Image.open(input_path).convert("L")
                img = np.array(pil_img)
            return img.astype(np.float32)

    @staticmethod
    def calibrate_to_sigma0_db(dn_array: np.ndarray, eps: float = 1e-6) -> np.ndarray:
        """
        Converts Digital Number (DN) amplitude to Sigma Naught backscatter in decibels (dB):
        sigma0_dB = 10 * log10(DN^2 + eps)
        """
        intensity = np.maximum(dn_array ** 2, eps)
        sigma0_db = 10.0 * np.log10(intensity)
        return sigma0_db

    @staticmethod
    def lee_filter(img: np.ndarray, window_size: int = 5, damping_factor: float = 1.0) -> np.ndarray:
        """
        Adaptive Lee Despeckling Filter for SAR imagery.
        Preserves edges while reducing granular speckle noise.
        """
        mean = cv2.blur(img, (window_size, window_size))
        sq_mean = cv2.blur(img ** 2, (window_size, window_size))
        variance = np.maximum(sq_mean - mean ** 2, 1e-6)

        # Estimate overall noise variance
        overall_noise_var = np.var(img)
        weight = variance / (variance + overall_noise_var * damping_factor + 1e-6)
        weight = np.clip(weight, 0.0, 1.0)

        filtered = mean + weight * (img - mean)
        return filtered.astype(np.float32)

    @staticmethod
    def normalize_sar(db_array: np.ndarray, min_db: float = -30.0, max_db: float = 0.0) -> np.ndarray:
        """
        Clips backscatter to standard marine SAR range [-30 dB, 0 dB] and scales to [0.0, 1.0].
        Dark oceanic features (oil slicks, low wind) occupy the low dB spectrum.
        """
        clipped = np.clip(db_array, min_db, max_db)
        normalized = (clipped - min_db) / (max_db - min_db)
        return normalized.astype(np.float32)

    @classmethod
    def preprocess_sar(
        cls,
        input_path: str,
        output_path: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Full end-to-end SAR preprocessing pipeline:
        input -> raw raster -> calibrated dB -> lee despeckled -> normalized [0, 1].
        """
        cfg = config or {}
        polarization = cfg.get("polarization", "VV")
        apply_calibration = cfg.get("apply_calibration", True)
        apply_despeckle = cfg.get("apply_despeckle", True)
        min_db = cfg.get("min_db", -30.0)
        max_db = cfg.get("max_db", 0.0)

        raw = cls.load_raster(input_path, polarization=polarization)
        ext = os.path.splitext(input_path)[1].lower()

        is_calibrated = False
        calib_method = "LINEAR_PROXY"
        notice = ""

        if ext in (".png", ".jpg", ".jpeg", ".webp") and cfg.get("apply_calibration") is None:
            # 8-bit preview image: scale directly from 0-255 to [0, 1]
            normalized = raw / 255.0
            if apply_despeckle:
                normalized = cls.lee_filter(normalized, window_size=3)
            normalized = np.clip(normalized, 0.0, 1.0).astype(np.float32)
            is_calibrated = False
            calib_method = "8BIT_VISUAL_PROXY"
            notice = "8-bit optical/preview raster: Linear scaling applied without radiometric sigma0 calibration."
        elif raw.max() <= 1.0 and ext in (".npy",):
            normalized = raw
            is_calibrated = True
            calib_method = "PRE_CALIBRATED_NUMPY"
            notice = "Pre-normalized float32 NumPy array."
        else:
            if apply_calibration:
                db = cls.calibrate_to_sigma0_db(raw)
                is_calibrated = True
                calib_method = "RADIOMETRIC_SIGMA0_DB"
                notice = "Radiometric calibration applied: sigma0 (dB) clipped to [-30, 0] dB."
            else:
                db = raw
                is_calibrated = False
                calib_method = "RAW_DN"
                notice = "Digital Number (DN) values processed directly without sigma0 calibration."

            if apply_despeckle:
                despeckled = cls.lee_filter(db)
            else:
                despeckled = db

            normalized = cls.normalize_sar(despeckled, min_db, max_db)

        if output_path:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            # Save as 8-bit PNG preview and float32 npy
            preview_8bit = (normalized * 255.0).astype(np.uint8)
            cv2.imwrite(output_path, preview_8bit)

        return {
            "processed_array": normalized,
            "shape": list(normalized.shape),
            "min_val": float(np.min(normalized)),
            "max_val": float(np.max(normalized)),
            "mean_val": float(np.mean(normalized)),
            "output_path": output_path,
            "polarization_used": polarization,
            "is_calibrated": is_calibrated,
            "calibration_method": calib_method,
            "speckle_filtered": apply_despeckle,
            "diagnostic_notice": notice,
        }

    @staticmethod
    def extract_tiles(
        array: np.ndarray,
        tile_size: int = 256,
        stride: int = 256
    ) -> Tuple[np.ndarray, List[Tuple[int, int, int, int]]]:
        """
        Splits preprocessed SAR image into model-ready patches (N, tile_size, tile_size).
        Returns tiles and coordinate bounding boxes (row_start, col_start, row_end, col_end).
        """
        h, w = array.shape[:2]
        tiles = []
        coords = []

        for r in range(0, h, stride):
            for c in range(0, w, stride):
                r_end = min(r + tile_size, h)
                c_end = min(c + tile_size, w)

                tile = np.zeros((tile_size, tile_size), dtype=np.float32)
                sub = array[r:r_end, c:c_end]
                tile[0:sub.shape[0], 0:sub.shape[1]] = sub

                tiles.append(tile)
                coords.append((r, c, r_end, c_end))

        return np.array(tiles), coords

    @staticmethod
    def reconstruct_from_tiles(
        tiles: np.ndarray,
        coords: List[Tuple[int, int, int, int]],
        output_shape: Tuple[int, int],
        use_blending: bool = True
    ) -> np.ndarray:
        """
        Reconstructs full-scene probability map from sliding-window tiles using
        2D Hann window spatial weighting to eliminate tile boundary seams.
        """
        h, w = output_shape
        prob_accum = np.zeros((h, w), dtype=np.float32)
        weight_accum = np.zeros((h, w), dtype=np.float32)

        tile_size = tiles.shape[1]
        if use_blending:
            # 2D Hann window
            hann_1d = np.hanning(tile_size)
            hann_2d = np.outer(hann_1d, hann_1d).astype(np.float32)
            hann_2d = np.maximum(hann_2d, 1e-4)
        else:
            hann_2d = np.ones((tile_size, tile_size), dtype=np.float32)

        for tile, (r1, c1, r2, c2) in zip(tiles, coords):
            th = r2 - r1
            tw = c2 - c1
            sub_tile = tile[:th, :tw]
            sub_weight = hann_2d[:th, :tw]

            prob_accum[r1:r2, c1:c2] += sub_tile * sub_weight
            weight_accum[r1:r2, c1:c2] += sub_weight

        weight_accum = np.maximum(weight_accum, 1e-6)
        reconstructed = prob_accum / weight_accum
        return np.clip(reconstructed, 0.0, 1.0).astype(np.float32)

    @staticmethod
    def generate_probability_heatmap(
        probability_map: np.ndarray,
        colormap: int = cv2.COLORMAP_TURBO,
        threshold_cut: float = 0.15,
        output_path: Optional[str] = None
    ) -> np.ndarray:
        """
        Generates an RGBA heatmap image where low-probability ocean is transparent,
        and high-probability slicks are colored with vibrant gradients.
        """
        prob_8u = (np.clip(probability_map, 0.0, 1.0) * 255.0).astype(np.uint8)
        color_bgr = cv2.applyColorMap(prob_8u, colormap)

        # Alpha channel: 0 below threshold, ramp up to 230 above threshold
        alpha = np.zeros_like(prob_8u)
        mask = probability_map >= threshold_cut
        alpha[mask] = np.clip(
            ((probability_map[mask] - threshold_cut) / (1.0 - threshold_cut) * 200.0 + 30.0),
            0, 230
        ).astype(np.uint8)

        # Merge BGR + Alpha into RGBA
        b, g, r = cv2.split(color_bgr)
        rgba = cv2.merge([b, g, r, alpha])

        if output_path:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            cv2.imwrite(output_path, rgba)

        return rgba

