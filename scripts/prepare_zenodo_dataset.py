#!/usr/bin/env python3
"""
OILTRACE Marine Oil Spill AI Subsystem — Zenodo Sentinel-1 Dataset Preparation Pipeline.
Preprocesses raw Sentinel-1 SAR imagery and ground-truth masks for supervised U-Net training.

Key Capabilities:
- Ingestion of raw Sentinel-1 GeoTIFFs (2048x2048x2 VV/VH or single-band).
- Extraction of co-polarized VV band (standard for marine capillary wave dampening).
- Radiometric calibration & dB clipping [-30 dB, 0 dB] normalized to [0.0, 1.0].
- Synchronous tiling into 256x256 patches preserving 1:1 image-mask spatial alignment.
- Mask binarization (0 = background / clean sea, 255 = oil spill).
- Robust validation against NaNs, Infs, dimension mismatches, and corrupted files.
- Controlled background filtering preserving negative samples for false-positive suppression.
- Scene-level dataset splitting (70% train, 20% val, 10% test) to prevent spatial data leakage.
- Dry-run mode for pre-flight testing and full JSON report generation.
"""

import os
import sys
import argparse
import glob
import json
import random
import time
import numpy as np
import cv2

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ml.preprocessing.sar_preprocessor import SarPreprocessor

try:
    import tifffile
    TIFFFILE_AVAILABLE = True
except ImportError:
    TIFFFILE_AVAILABLE = False


def parse_args():
    parser = argparse.ArgumentParser(
        description="OILTRACE — Prepare Zenodo Sentinel-1 SAR Oil Spill Dataset (SIH26143)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--input-dir",
        type=str,
        required=True,
        help="Path to raw Zenodo dataset containing images/ and masks/ (or flat directory)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=os.path.join(PROJECT_ROOT, "data", "dataset"),
        help="Destination directory for tiled train/val/test splits"
    )
    parser.add_argument(
        "--polarization",
        type=str,
        default="VV",
        choices=["VV", "VH"],
        help="SAR polarization channel to extract (VV is gold standard for oil slicks)"
    )
    parser.add_argument(
        "--tile-size",
        type=int,
        default=256,
        help="Target square patch dimension in pixels"
    )
    parser.add_argument(
        "--stride",
        type=int,
        default=256,
        help="Sliding window stride (256 = non-overlapping, 128 = 50%% overlap)"
    )
    parser.add_argument(
        "--spill-class-id",
        type=int,
        default=1,
        help="Integer class ID representing oil spill in raw masks (default: 1)"
    )
    parser.add_argument(
        "--min-spill-pixels",
        type=int,
        default=16,
        help="Minimum spill pixels required for a patch to be classified as positive"
    )
    parser.add_argument(
        "--negative-ratio",
        type=float,
        default=1.0,
        help="Ratio of negative (clean water) to positive patches to keep per scene (e.g. 1.0 = 1:1 balance)"
    )
    parser.add_argument(
        "--clean-scene-negatives",
        type=int,
        default=4,
        help="Max negative patches to keep from scenes containing zero oil spills"
    )
    parser.add_argument(
        "--train-split",
        type=float,
        default=0.70,
        help="Fraction of original scenes assigned to training set"
    )
    parser.add_argument(
        "--val-split",
        type=float,
        default=0.20,
        help="Fraction of original scenes assigned to validation set"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Deterministic random seed for scene splitting and patch sampling"
    )
    parser.add_argument(
        "--max-scenes",
        type=int,
        default=None,
        help="Optional limit on number of scenes to process (useful for testing)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate processing, validate inputs, and report metrics without writing tiles to disk"
    )
    parser.add_argument(
        "--apply-despeckle",
        action="store_true",
        default=True,
        help="Apply adaptive Lee filter to reduce granular SAR speckle noise"
    )
    return parser.parse_args()


class ZenodoDatasetPreparator:
    """
    Handles robust ingestion, calibration, tiling, and leakage-free splitting
    of Sentinel-1 SAR oil spill scenes.
    """

    def __init__(self, args):
        self.args = args
        random.seed(args.seed)
        np.random.seed(args.seed)

    def find_scene_pairs(self) -> list:
        """
        Discovers corresponding image and mask files.
        Supports:
        1. Subdirectory structure: input_dir/images and input_dir/masks
        2. Flat directory with name matching
        """
        input_dir = os.path.abspath(self.args.input_dir)
        if not os.path.exists(input_dir):
            raise FileNotFoundError(f"Input dataset directory not found: {input_dir}")

        images_subdir = os.path.join(input_dir, "images")
        masks_subdir = os.path.join(input_dir, "masks")

        if os.path.exists(images_subdir):
            img_search_dir = images_subdir
            mask_search_dir = masks_subdir if os.path.exists(masks_subdir) else input_dir
        else:
            img_search_dir = input_dir
            mask_search_dir = input_dir

        image_extensions = ("*.tif", "*.tiff", "*.png", "*.jpg", "*.jpeg", "*.npy")
        candidate_images = []
        for ext in image_extensions:
            candidate_images.extend(glob.glob(os.path.join(img_search_dir, ext)))
            candidate_images.extend(glob.glob(os.path.join(img_search_dir, ext.upper())))

        # Remove duplicate paths
        candidate_images = sorted(list(set(candidate_images)))

        # Exclude mask files if scanning a flat directory
        image_files = [
            f for f in candidate_images
            if not any(k in os.path.basename(f).lower() for k in ("_mask", "-mask", "_label", "-label", "_gt"))
        ]

        pairs = []
        for img_path in image_files:
            bname = os.path.splitext(os.path.basename(img_path))[0]
            # Look for matching mask
            mask_candidates = [
                os.path.join(mask_search_dir, f"{bname}.tif"),
                os.path.join(mask_search_dir, f"{bname}.tiff"),
                os.path.join(mask_search_dir, f"{bname}.png"),
                os.path.join(mask_search_dir, f"{bname}.npy"),
                os.path.join(mask_search_dir, f"{bname}_mask.png"),
                os.path.join(mask_search_dir, f"{bname}_mask.tif"),
                os.path.join(mask_search_dir, f"{bname}_label.png"),
                os.path.join(mask_search_dir, f"{bname}_gt.png"),
            ]
            matched_mask = None
            for cand in mask_candidates:
                if os.path.exists(cand):
                    matched_mask = cand
                    break

            if matched_mask:
                pairs.append({
                    "id": bname,
                    "image_path": img_path,
                    "mask_path": matched_mask
                })

        return pairs

    def read_raw_sar(self, path: str) -> np.ndarray:
        """
        Reads Sentinel-1 SAR raster, extracting the specified polarization channel (VV/VH).
        """
        ext = os.path.splitext(path)[1].lower()
        if ext in (".tif", ".tiff"):
            if not TIFFFILE_AVAILABLE:
                raise ImportError("tifffile package is required to read GeoTIFF images. Install with: pip install tifffile")
            arr = tifffile.imread(path)
        elif ext == ".npy":
            arr = np.load(path)
        else:
            arr = cv2.imread(path, cv2.IMREAD_UNCHANGED)
            if arr is None:
                raise ValueError(f"Failed to read image at: {path}")

        arr = arr.astype(np.float32)

        # Handle multi-band dimensions (Sentinel-1 2048x2048x2 VV/VH)
        if arr.ndim == 3:
            # Check channel ordering
            if arr.shape[0] in (2, 3, 4) and arr.shape[1] > 100:
                # Shape: (Channels, H, W)
                ch_idx = 1 if self.args.polarization.upper() == "VH" and arr.shape[0] > 1 else 0
                channel = arr[ch_idx, :, :]
            elif arr.shape[2] in (2, 3, 4):
                # Shape: (H, W, Channels)
                ch_idx = 1 if self.args.polarization.upper() == "VH" and arr.shape[2] > 1 else 0
                channel = arr[:, :, ch_idx]
            else:
                channel = arr[:, :, 0]
        elif arr.ndim == 2:
            channel = arr
        else:
            raise ValueError(f"Unexpected image array dimensionality: {arr.shape}")

        return channel

    def read_raw_mask(self, path: str) -> np.ndarray:
        """
        Reads ground-truth mask and maps to binary: 0 (background) and 255 (oil spill).
        """
        ext = os.path.splitext(path)[1].lower()
        if ext in (".tif", ".tiff"):
            if not TIFFFILE_AVAILABLE:
                raise ImportError("tifffile package is required to read GeoTIFF masks.")
            arr = tifffile.imread(path)
        elif ext == ".npy":
            arr = np.load(path)
        else:
            arr = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
            if arr is None:
                raise ValueError(f"Failed to read mask at: {path}")

        if arr.ndim == 3:
            arr = arr[:, :, 0] if arr.shape[2] <= 4 else arr[0, :, :]

        arr = arr.astype(np.float32)
        unique_vals = np.unique(arr)

        # Map to binary 0 and 255
        if len(unique_vals) <= 2 and set(unique_vals).issubset({0, 1, 0.0, 1.0}):
            # Binary mask with 0 and 1
            binary = (arr > 0.5).astype(np.uint8) * 255
        elif set(unique_vals).issubset({0, 255, 0.0, 255.0}):
            # Already binary 0 and 255
            binary = (arr >= 128).astype(np.uint8) * 255
        else:
            # Multiclass mask (e.g. 0=sea, 1=oil spill, 2=lookalike, 3=ship, 4=land)
            # Extract spill_class_id as positive (255) and all other classes as background (0)
            binary = (np.isclose(arr, self.args.spill_class_id)).astype(np.uint8) * 255

        return binary

    def normalize_sar_band(self, sar_band: np.ndarray) -> np.ndarray:
        """
        Applies radiometric sigma0 decibel clipping [-30, 0] and [0.0, 1.0] scaling.
        """
        # Determine whether input is already in decibels (dB) or raw DN
        is_already_db = (np.median(sar_band) < 0) or (sar_band.min() < -5.0 and sar_band.max() <= 10.0)

        if is_already_db:
            db = sar_band
        elif sar_band.max() <= 1.0 and sar_band.min() >= 0.0:
            # Pre-normalized
            return np.clip(sar_band, 0.0, 1.0).astype(np.float32)
        else:
            # Raw digital numbers (DN) -> calibrate to sigma0 dB
            db = SarPreprocessor.calibrate_to_sigma0_db(sar_band)

        if self.args.apply_despeckle:
            db = SarPreprocessor.lee_filter(db, window_size=5)

        # Marine SAR normalization [-30 dB, 0 dB] -> [0.0, 1.0]
        norm = SarPreprocessor.normalize_sar(db, min_db=-30.0, max_db=0.0)
        return norm

    def tile_scene(
        self,
        norm_img: np.ndarray,
        binary_mask: np.ndarray,
        scene_id: str
    ) -> tuple:
        """
        Tiles an aligned image and mask synchronously into 256x256 patches.
        Separates into positive (spill-containing) and negative (clean sea) patches.
        """
        h, w = norm_img.shape[:2]
        tile_size = self.args.tile_size
        stride = self.args.stride

        pos_patches = []
        neg_patches = []

        for r in range(0, h - tile_size + 1, stride):
            for c in range(0, w - tile_size + 1, stride):
                img_patch = norm_img[r:r + tile_size, c:c + tile_size]
                mask_patch = binary_mask[r:r + tile_size, c:c + tile_size]

                spill_pixels = int(np.count_nonzero(mask_patch == 255))
                patch_name = f"{scene_id}_r{r:04d}_c{c:04d}"

                patch_data = {
                    "name": patch_name,
                    "img": img_patch,
                    "mask": mask_patch,
                    "spill_pixels": spill_pixels,
                    "has_spill": spill_pixels >= self.args.min_spill_pixels
                }

                if patch_data["has_spill"]:
                    pos_patches.append(patch_data)
                else:
                    neg_patches.append(patch_data)

        return pos_patches, neg_patches

    def run(self) -> dict:
        start_time = time.time()
        print("=" * 70)
        print("  OILTRACE — Zenodo Sentinel-1 Dataset Preparation Pipeline")
        print("  SIH26143 Supervised Marine Oil Spill Training Preparation")
        print("=" * 70)
        print(f"Input Directory:      {self.args.input_dir}")
        print(f"Output Directory:     {self.args.output_dir}")
        print(f"Polarization Target:  {self.args.polarization} (Single-Channel U-Net)")
        print(f"Patch Size:           {self.args.tile_size} x {self.args.tile_size} (Stride: {self.args.stride})")
        print(f"Dry-Run Mode:         {'ENABLED (Simulation only — no files written)' if self.args.dry_run else 'DISABLED (Writing output patches)'}")
        print("-" * 70)

        pairs = self.find_scene_pairs()
        if not pairs:
            raise FileNotFoundError(
                f"No matching Sentinel-1 image and mask pairs found in '{self.args.input_dir}'.\n"
                f"Expected image formats (.tif, .tiff) with matching masks in images/ and masks/."
            )

        print(f"[FOUND] Discovered {len(pairs)} matching original Sentinel-1 scenes.")

        if self.args.max_scenes is not None and self.args.max_scenes > 0:
            pairs = pairs[:self.args.max_scenes]
            print(f"[LIMIT] Processing capped to {len(pairs)} scenes via --max-scenes.")

        # -------------------------------------------------------------
        # LEAKAGE-FREE SPLITTING: Split at ORIGINAL SCENE level first
        # -------------------------------------------------------------
        random.shuffle(pairs)
        n_total = len(pairs)

        if n_total == 1:
            train_scenes = pairs
            val_scenes = []
            test_scenes = []
        elif n_total == 2:
            train_scenes = [pairs[0]]
            val_scenes = [pairs[1]]
            test_scenes = []
        else:
            n_train = max(1, int(round(n_total * self.args.train_split)))
            n_val = max(1, int(round(n_total * self.args.val_split)))
            n_test = n_total - n_train - n_val
            if n_test < 0:
                n_train = max(1, n_train - 1)
                n_test = n_total - n_train - n_val

            train_scenes = pairs[:n_train]
            val_scenes = pairs[n_train:n_train + n_val]
            test_scenes = pairs[n_train + n_val:]

        splits_map = {
            "train": train_scenes,
            "val": val_scenes,
            "test": test_scenes
        }

        print(f"[SPLIT] Leakage-Free Scene Split: {len(train_scenes)} Train | {len(val_scenes)} Val | {len(test_scenes)} Test")

        # Prepare output directories if not dry run
        if not self.args.dry_run:
            for s in ("train", "val", "test"):
                os.makedirs(os.path.join(self.args.output_dir, s, "images"), exist_ok=True)
                os.makedirs(os.path.join(self.args.output_dir, s, "masks"), exist_ok=True)

        stats = {
            "total_scenes": n_total,
            "scene_splits": {"train": len(train_scenes), "val": len(val_scenes), "test": len(test_scenes)},
            "total_patches": 0,
            "positive_patches": 0,
            "negative_patches": 0,
            "split_patch_counts": {"train": 0, "val": 0, "test": 0},
            "corrupted_or_skipped": 0,
            "skipped_details": [],
            "polarization_used": self.args.polarization,
            "patch_dimension": f"{self.args.tile_size}x{self.args.tile_size}",
            "execution_mode": "DRY_RUN" if self.args.dry_run else "FULL_EXPORT",
        }

        for split_name, scene_list in splits_map.items():
            if not scene_list:
                continue

            for idx, item in enumerate(scene_list, 1):
                scene_id = item["id"]
                try:
                    # Ingest and validate image
                    sar_band = self.read_raw_sar(item["image_path"])
                    mask = self.read_raw_mask(item["mask_path"])

                    # Dimension validation
                    if sar_band.shape[:2] != mask.shape[:2]:
                        raise ValueError(
                            f"Dimension mismatch between image {sar_band.shape[:2]} and mask {mask.shape[:2]}"
                        )

                    # Integrity checks
                    if np.isnan(sar_band).any() or np.isnan(mask).any():
                        raise ValueError("Data contains NaN values.")
                    if np.isinf(sar_band).any() or np.isinf(mask).any():
                        raise ValueError("Data contains Infinite values.")

                    # Preprocess & normalize SAR
                    norm_sar = self.normalize_sar_band(sar_band)

                    # Tile synchronously
                    pos_patches, neg_patches = self.tile_scene(norm_sar, mask, scene_id)

                    # Balanced background sampling
                    if len(pos_patches) > 0:
                        # Keep all positive patches
                        selected_pos = pos_patches
                        # Sample negatives proportional to positive count
                        num_neg_to_keep = max(1, int(len(pos_patches) * self.args.negative_ratio))
                        selected_neg = random.sample(neg_patches, min(len(neg_patches), num_neg_to_keep))
                    else:
                        # Scene has no oil slicks: retain a controlled sample of clean background
                        selected_pos = []
                        num_neg_to_keep = min(len(neg_patches), self.args.clean_scene_negatives)
                        selected_neg = random.sample(neg_patches, num_neg_to_keep)

                    combined = selected_pos + selected_neg
                    random.shuffle(combined)

                    # Save patches if not dry-run
                    if not self.args.dry_run:
                        img_out_dir = os.path.join(self.args.output_dir, split_name, "images")
                        mask_out_dir = os.path.join(self.args.output_dir, split_name, "masks")

                        for p in combined:
                            # Save 8-bit grayscale PNG for SAR image
                            img_uint8 = (p["img"] * 255.0).astype(np.uint8)
                            img_dest = os.path.join(img_out_dir, f"{p['name']}.png")
                            cv2.imwrite(img_dest, img_uint8)

                            # Save binary mask (0 and 255)
                            mask_dest = os.path.join(mask_out_dir, f"{p['name']}.png")
                            cv2.imwrite(mask_dest, p["mask"])

                    # Update statistics
                    stats["split_patch_counts"][split_name] += len(combined)
                    stats["total_patches"] += len(combined)
                    stats["positive_patches"] += len(selected_pos)
                    stats["negative_patches"] += len(selected_neg)

                    print(
                        f"  [{split_name.upper():5s}] Scene {idx:02d}/{len(scene_list):02d} ({scene_id}): "
                        f"{len(selected_pos)} positive, {len(selected_neg)} negative patches generated."
                    )

                except Exception as e:
                    stats["corrupted_or_skipped"] += 1
                    stats["skipped_details"].append({"scene_id": scene_id, "error": str(e)})
                    print(f"  [ERROR] Skipping corrupted scene {scene_id}: {e}")

        # Compute percentages
        tot = stats["total_patches"]
        stats["pos_percentage"] = round((stats["positive_patches"] / tot * 100), 2) if tot > 0 else 0.0
        stats["neg_percentage"] = round((stats["negative_patches"] / tot * 100), 2) if tot > 0 else 0.0
        stats["duration_seconds"] = round(time.time() - start_time, 2)

        # Write prep report JSON
        report_path = os.path.join(
            self.args.output_dir if not self.args.dry_run else PROJECT_ROOT,
            "dataset_prep_report.json"
        )
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2)

        # Print summary report
        print("\n" + "=" * 70)
        print("  DATASET PREPARATION REPORT SUMMARY")
        print("=" * 70)
        print(f"  Execution Mode:         {stats['execution_mode']}")
        print(f"  Total Original Scenes:  {stats['total_scenes']}")
        print(f"    - Train Scenes:       {stats['scene_splits']['train']}")
        print(f"    - Val Scenes:         {stats['scene_splits']['val']}")
        print(f"    - Test Scenes:        {stats['scene_splits']['test']}")
        print(f"  Total Patches Generated:{stats['total_patches']}")
        print(f"    - Train Patches:      {stats['split_patch_counts']['train']}")
        print(f"    - Val Patches:        {stats['split_patch_counts']['val']}")
        print(f"    - Test Patches:       {stats['split_patch_counts']['test']}")
        print(f"  Positive Spill Patches: {stats['positive_patches']} ({stats['pos_percentage']}%)")
        print(f"  Negative Sea Patches:   {stats['negative_patches']} ({stats['neg_percentage']}%)")
        print(f"  Corrupted/Skipped:      {stats['corrupted_or_skipped']}")
        print(f"  Polarization Channel:   {stats['polarization_used']}")
        print(f"  Patch Dimensions:       {stats['patch_dimension']}")
        print(f"  Report Saved To:        {report_path}")
        print("=" * 70)

        return stats


def main():
    args = parse_args()
    preparator = ZenodoDatasetPreparator(args)
    preparator.run()


if __name__ == "__main__":
    main()
