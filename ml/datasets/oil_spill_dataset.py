"""
OILTRACE Marine Oil Spill AI Subsystem — Dataset Loader & Synthetic Generator.
Supports loading real SAR imagery and ground-truth masks as well as
generating synthetic SAR datasets for training pipeline readiness and demonstration.
"""
import os
import glob
import math
import json
import random
import numpy as np
import cv2
from typing import Dict, Any, List, Tuple, Optional, Union

try:
    import torch
    from torch.utils.data import Dataset, DataLoader
    TORCH_AVAILABLE = True
except Exception:
    TORCH_AVAILABLE = False
    class Dataset:
        pass


class SyntheticSarDatasetGenerator:
    """
    Generates synthetic SAR images and corresponding ground-truth oil spill masks.
    Simulates:
    1. Realistic marine radar sea clutter with speckle (Rayleigh/K-distribution intensity).
    2. Curvilinear dark oil slicks (capillary wave dampening with softened boundary gradients).
    3. Occasional look-alike features (calm wind zones and linear ship wakes).
    """

    @staticmethod
    def generate_single_sample(
        size: int = 256,
        has_spill: bool = True,
        has_lookalike: bool = False,
        seed: Optional[int] = None
    ) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
        """
        Returns:
            sar_image: float32 array normalized to [0.0, 1.0]
            mask: uint8 array with 1 for spill, 0 for sea background
            metadata: dictionary describing features injected
        """
        if seed is not None:
            np.random.seed(seed)
            random.seed(seed)

        # 1. Background sea clutter: Rayleigh-distributed radar amplitude
        # Rayleigh scale parameter ~ 0.5, with multiplicative speckle noise
        scale = np.random.uniform(0.45, 0.65)
        sea_amplitude = np.random.rayleigh(scale, (size, size)).astype(np.float32)

        # Multi-scale spatial smoothing to mimic gentle ocean swell variations
        swell = cv2.GaussianBlur(sea_amplitude, (15, 15), 3.0)
        speckle = np.random.gamma(shape=2.0, scale=0.5, size=(size, size)).astype(np.float32)
        sar_image = (swell * 0.7 + sea_amplitude * 0.3) * speckle

        # Normalize sea clutter to standard dB dynamic range [-28 dB, -5 dB]
        sar_db = 10.0 * np.log10(np.maximum(sar_image ** 2, 1e-6))
        sar_norm = np.clip((sar_db - (-28.0)) / ((-5.0) - (-28.0)), 0.0, 1.0).astype(np.float32)

        mask = np.zeros((size, size), dtype=np.uint8)
        metadata: Dict[str, Any] = {
            "has_spill": has_spill,
            "has_lookalike": has_lookalike,
            "synthetic": True,
            "watermark": "Synthetic demonstration data — not real-world evidence.",
        }

        # 2. Inject oil slick if requested
        if has_spill:
            num_slicks = random.randint(1, 2)
            for _ in range(num_slicks):
                # Random spline / polyline path for curvilinear slick
                num_points = random.randint(4, 7)
                pts_x = np.random.randint(int(size * 0.15), int(size * 0.85), size=num_points)
                pts_y = np.random.randint(int(size * 0.15), int(size * 0.85), size=num_points)

                # Sort by x or random walk to make a coherent slick
                order = np.argsort(pts_x)
                curve_pts = np.column_stack([pts_x[order], pts_y[order]]).astype(np.int32)

                # Draw base slick ribbon
                slick_canvas = np.zeros((size, size), dtype=np.float32)
                thickness = random.randint(10, 24)
                cv2.polylines(slick_canvas, [curve_pts], isClosed=False, color=1.0, thickness=thickness)

                # Organic perturbation using morphological dilation and blur
                kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
                slick_blob = cv2.dilate(slick_canvas, kernel, iterations=random.randint(1, 3))
                slick_soft = cv2.GaussianBlur(slick_blob, (9, 9), 2.5)

                # Strong capillary wave dampening (reduces normalized SAR backscatter by 0.4 to 0.7)
                dampening_factor = np.random.uniform(0.45, 0.75)
                sar_norm = np.clip(sar_norm - (slick_soft * dampening_factor), 0.02, 1.0)

                # Ground truth binary mask (thresholded at 0.5)
                mask = np.maximum(mask, (slick_soft > 0.45).astype(np.uint8))

        # 3. Inject look-alike if requested
        if has_lookalike:
            lookalike_type = random.choice(["calm_wind", "ship_wake"])
            if lookalike_type == "calm_wind":
                # Broad, diffuse low-wind patch with gentle gradients
                margin = max(5, int(size * 0.2))
                cx = random.randint(margin, max(margin + 1, size - margin))
                cy = random.randint(margin, max(margin + 1, size - margin))
                calm_canvas = np.zeros((size, size), dtype=np.float32)
                max_ax = max(8, int(size * 0.25))
                min_ax = max(4, int(size * 0.15))
                axes = (random.randint(min_ax, max_ax), random.randint(max(2, min_ax // 2), max(4, max_ax // 2)))
                cv2.ellipse(calm_canvas, (cx, cy), axes, random.randint(0, 180), 0, 360, 1.0, -1)
                k_size = min(31, max(5, (size // 8) * 2 + 1))
                calm_soft = cv2.GaussianBlur(calm_canvas, (k_size, k_size), float(k_size / 3.0))
                sar_norm = np.clip(sar_norm - (calm_soft * 0.35), 0.05, 1.0)
                metadata["lookalike"] = "calm_wind"
            else:
                # Linear narrow bright/dark ship wake
                p1 = (random.randint(5, max(6, int(size * 0.25))), random.randint(5, size - 5))
                p2 = (random.randint(max(7, int(size * 0.75)), size - 5), random.randint(5, size - 5))
                wake_canvas = np.zeros((size, size), dtype=np.float32)
                cv2.line(wake_canvas, p1, p2, 1.0, max(1, size // 64))
                sar_norm = np.clip(sar_norm - (wake_canvas * 0.3), 0.05, 1.0)
                metadata["lookalike"] = "ship_wake"

        return sar_norm, mask, metadata

    @classmethod
    def create_dataset_directory(
        cls,
        output_dir: str,
        num_samples: int = 30,
        size: int = 256,
        spill_ratio: float = 0.8,
        lookalike_ratio: float = 0.3,
        seed: int = 42
    ) -> Dict[str, Any]:
        """
        Creates a structured dataset directory on disk:
        output_dir/
            images/ (float32 .npy and 8-bit .png)
            masks/  (uint8 .png and .npy)
            metadata.json
        """
        images_dir = os.path.join(output_dir, "images")
        masks_dir = os.path.join(output_dir, "masks")
        os.makedirs(images_dir, exist_ok=True)
        os.makedirs(masks_dir, exist_ok=True)

        samples_meta = []
        random.seed(seed)
        np.random.seed(seed)

        for i in range(num_samples):
            has_spill = random.random() < spill_ratio
            has_lookalike = random.random() < lookalike_ratio

            img, mask, meta = cls.generate_single_sample(
                size=size,
                has_spill=has_spill,
                has_lookalike=has_lookalike,
                seed=seed + i
            )

            file_id = f"sar_sample_{i:04d}"
            img_path = os.path.join(images_dir, f"{file_id}.npy")
            mask_path = os.path.join(masks_dir, f"{file_id}.png")

            # Save float32 array
            np.save(img_path, img)
            # Save 8-bit visual preview PNG
            preview_path = os.path.join(images_dir, f"{file_id}.png")
            cv2.imwrite(preview_path, (img * 255.0).astype(np.uint8))
            # Save binary mask PNG
            cv2.imwrite(mask_path, (mask * 255).astype(np.uint8))

            meta.update({
                "id": file_id,
                "image_path": img_path,
                "mask_path": mask_path,
                "preview_path": preview_path,
                "spill_pixel_count": int(np.sum(mask)),
            })
            samples_meta.append(meta)

        summary_path = os.path.join(output_dir, "dataset_summary.json")
        summary_data = {
            "total_samples": num_samples,
            "spill_samples": sum(1 for s in samples_meta if s["has_spill"]),
            "background_samples": sum(1 for s in samples_meta if not s["has_spill"]),
            "synthetic": True,
            "disclaimer": "Synthetic demonstration data — not real-world evidence.",
            "samples": samples_meta,
        }
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary_data, f, indent=2)

        return summary_data


class OilSpillDataset(Dataset):
    """
    General Dataset loader for Marine Oil Spill SAR imagery.
    Compatible with:
    - Real GeoTIFF / PNG / NPY rasters + binary masks.
    - Synthetic dataset generated via SyntheticSarDatasetGenerator.
    """

    def __init__(
        self,
        images_dir: str,
        masks_dir: str,
        augment: bool = False,
        target_size: Optional[Tuple[int, int]] = (256, 256)
    ):
        self.images_dir = images_dir
        self.masks_dir = masks_dir
        self.augment = augment
        self.target_size = target_size

        # Find image files
        self.image_files = []
        for ext in ("*.npy", "*.tif", "*.tiff", "*.png", "*.jpg"):
            self.image_files.extend(glob.glob(os.path.join(images_dir, ext)))

        # Filter out PNG previews if NPY exists
        npy_basenames = {
            os.path.splitext(os.path.basename(f))[0]
            for f in self.image_files if f.endswith(".npy")
        }
        filtered = []
        for f in self.image_files:
            bname = os.path.splitext(os.path.basename(f))[0]
            if f.endswith(".png") and bname in npy_basenames:
                continue
            filtered.append(f)
        self.image_files = sorted(filtered)

    def __len__(self) -> int:
        return len(self.image_files)

    def _load_image(self, path: str) -> np.ndarray:
        if path.endswith(".npy"):
            arr = np.load(path).astype(np.float32)
        else:
            arr = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
            if arr is None:
                raise FileNotFoundError(f"Cannot load image at {path}")
            arr = arr.astype(np.float32) / 255.0
        return arr

    def _load_mask(self, base_name: str) -> np.ndarray:
        for ext in (".png", ".npy", ".tif", ".tiff"):
            candidate = os.path.join(self.masks_dir, base_name + ext)
            if os.path.exists(candidate):
                if candidate.endswith(".npy"):
                    mask = np.load(candidate)
                else:
                    mask = cv2.imread(candidate, cv2.IMREAD_GRAYSCALE)
                return (mask > 127).astype(np.float32)

        # If mask file does not exist, return blank background mask
        sample_img = self._load_image(self.image_files[0])
        return np.zeros(sample_img.shape, dtype=np.float32)

    def _apply_augmentations(
        self,
        img: np.ndarray,
        mask: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        # Random horizontal flip
        if random.random() > 0.5:
            img = np.fliplr(img)
            mask = np.fliplr(mask)

        # Random vertical flip
        if random.random() > 0.5:
            img = np.flipud(img)
            mask = np.flipud(mask)

        # Random 90-degree rotation
        k = random.randint(0, 3)
        if k > 0:
            img = np.rot90(img, k)
            mask = np.rot90(mask, k)

        # Random contrast/brightness jitter
        if random.random() > 0.5:
            gamma = random.uniform(0.85, 1.15)
            img = np.clip(img ** gamma, 0.0, 1.0)

        return np.ascontiguousarray(img), np.ascontiguousarray(mask)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        img_path = self.image_files[idx]
        base_name = os.path.splitext(os.path.basename(img_path))[0]
        img = self._load_image(img_path)
        mask = self._load_mask(base_name)

        if self.target_size is not None and (img.shape[0] != self.target_size[0] or img.shape[1] != self.target_size[1]):
            img = cv2.resize(img, (self.target_size[1], self.target_size[0]), interpolation=cv2.INTER_LINEAR)
            mask = cv2.resize(mask, (self.target_size[1], self.target_size[0]), interpolation=cv2.INTER_NEAREST)

        if self.augment:
            img, mask = self._apply_augmentations(img, mask)

        # Return tensor if PyTorch is available, otherwise NumPy arrays
        if TORCH_AVAILABLE:
            tensor_img = torch.from_numpy(img).unsqueeze(0).float()  # (1, H, W)
            tensor_mask = torch.from_numpy(mask).unsqueeze(0).float()  # (1, H, W)
            return {
                "image": tensor_img,
                "mask": tensor_mask,
                "id": base_name,
            }
        else:
            return {
                "image": np.expand_dims(img, axis=0),
                "mask": np.expand_dims(mask, axis=0),
                "id": base_name,
            }


def create_train_val_loaders(
    dataset_dir: str,
    batch_size: int = 4,
    val_split: float = 0.2,
    seed: int = 42
) -> Tuple[Any, Any]:
    """
    Creates train and validation loaders from a dataset directory.
    If PyTorch is available, returns (DataLoader, DataLoader).
    If PyTorch is not available, returns Python generator iterables.
    """
    images_dir = os.path.join(dataset_dir, "images")
    masks_dir = os.path.join(dataset_dir, "masks")

    # If dataset directory is empty or missing, create synthetic demonstration dataset
    if not os.path.exists(images_dir) or len(glob.glob(os.path.join(images_dir, "*"))) == 0:
        SyntheticSarDatasetGenerator.create_dataset_directory(
            output_dir=dataset_dir,
            num_samples=25,
            seed=seed
        )

    all_files = sorted(glob.glob(os.path.join(images_dir, "*.npy")))
    if not all_files:
        all_files = sorted(glob.glob(os.path.join(images_dir, "*.png")))

    random.seed(seed)
    indices = list(range(len(all_files)))
    random.shuffle(indices)

    split_idx = int(len(indices) * (1.0 - val_split))
    train_indices = set(indices[:split_idx])
    val_indices = set(indices[split_idx:])

    full_ds = OilSpillDataset(images_dir=images_dir, masks_dir=masks_dir, augment=False)

    if TORCH_AVAILABLE:
        from torch.utils.data import Subset
        train_sub = Subset(full_ds, list(train_indices))
        val_sub = Subset(full_ds, list(val_indices))
        train_loader = DataLoader(train_sub, batch_size=batch_size, shuffle=True)
        val_loader = DataLoader(val_sub, batch_size=batch_size, shuffle=False)
        return train_loader, val_loader
    else:
        # Fallback generator for environments without PyTorch
        train_items = [full_ds[i] for i in train_indices]
        val_items = [full_ds[i] for i in val_indices]
        return train_items, val_items
