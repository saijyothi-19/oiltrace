"""
OILTRACE Marine Oil Spill AI Subsystem — Dataset Integrity Validator.
Verifies the integrity, alignment, and formatting of SAR imagery and ground-truth masks:
- Image exists and is uncorrupted.
- Corresponding mask exists for every image (and vice versa).
- Image dimensions match mask dimensions exactly (H x W).
- Pixel values are valid (no NaNs, no Infs, masks are binary).
- Train / Validation / Test separation (no data leakage).
"""
import os
import glob
import numpy as np
import cv2
from typing import Dict, Any, List, Set, Tuple, Optional
from PIL import Image

IMAGE_EXTENSIONS = (".npy", ".tif", ".tiff", ".png", ".jpg", ".jpeg", ".webp")
MASK_EXTENSIONS = (".png", ".npy", ".tif", ".tiff", ".webp")


class DatasetValidator:
    """
    Validates SAR oil spill training, validation, and test datasets.
    """

    @staticmethod
    def _read_image_shape_and_stats(path: str) -> Tuple[Optional[Tuple[int, int]], Optional[str]]:
        try:
            if path.endswith(".npy"):
                arr = np.load(path)
            elif path.endswith((".tif", ".tiff")):
                import tifffile
                arr = tifffile.imread(path)
            else:
                arr = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
                if arr is None:
                    with Image.open(path) as img:
                        arr = np.array(img.convert("L"))

            if arr is None:
                return None, f"Failed to decode image: {os.path.basename(path)}"

            if np.isnan(arr).any():
                return None, f"Image contains NaN values: {os.path.basename(path)}"
            if np.isinf(arr).any():
                return None, f"Image contains Infinite values: {os.path.basename(path)}"

            shape = arr.shape[:2]
            return shape, None
        except Exception as e:
            return None, f"Corrupted image file ({e}): {os.path.basename(path)}"

    @staticmethod
    def _read_mask_shape_and_stats(path: str) -> Tuple[Optional[Tuple[int, int]], bool, Optional[str]]:
        try:
            if path.endswith(".npy"):
                arr = np.load(path)
            elif path.endswith((".tif", ".tiff")):
                import tifffile
                arr = tifffile.imread(path)
            else:
                arr = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
                if arr is None:
                    with Image.open(path) as img:
                        arr = np.array(img.convert("L"))

            if arr is None:
                return None, False, f"Failed to decode mask: {os.path.basename(path)}"

            if np.isnan(arr).any() or np.isinf(arr).any():
                return None, False, f"Mask contains NaN/Inf values: {os.path.basename(path)}"

            unique_vals = np.unique(arr)
            # Check binary (either 0/1 or 0/255 or all 0 or all 1/255)
            is_binary = True
            for val in unique_vals:
                if val not in (0, 1, 255, 0.0, 1.0, 255.0):
                    is_binary = False
                    break

            shape = arr.shape[:2]
            return shape, is_binary, None
        except Exception as e:
            return None, False, f"Corrupted mask file ({e}): {os.path.basename(path)}"

    @classmethod
    def validate_split_directory(
        cls,
        split_name: str,
        split_dir: str
    ) -> Dict[str, Any]:
        images_dir = os.path.join(split_dir, "images")
        masks_dir = os.path.join(split_dir, "masks")

        errors: List[str] = []
        warnings: List[str] = []

        if not os.path.exists(images_dir):
            errors.append(f"[{split_name}] Missing images directory: {images_dir}")
            return {"split": split_name, "valid": False, "count": 0, "errors": errors, "warnings": warnings, "basenames": set()}

        if not os.path.exists(masks_dir):
            errors.append(f"[{split_name}] Missing masks directory: {masks_dir}")
            return {"split": split_name, "valid": False, "count": 0, "errors": errors, "warnings": warnings, "basenames": set()}

        # Gather image files
        image_files = []
        for ext in IMAGE_EXTENSIONS:
            image_files.extend(glob.glob(os.path.join(images_dir, f"*{ext}")))
        # Filter duplicates if both .npy and preview .png exist
        npy_basenames = {
            os.path.splitext(os.path.basename(f))[0]
            for f in image_files if f.endswith(".npy")
        }
        filtered_imgs = [
            f for f in image_files
            if not (f.endswith(".png") and os.path.splitext(os.path.basename(f))[0] in npy_basenames)
        ]

        img_map = {os.path.splitext(os.path.basename(f))[0]: f for f in filtered_imgs}

        # Gather mask files
        mask_files = []
        for ext in MASK_EXTENSIONS:
            mask_files.extend(glob.glob(os.path.join(masks_dir, f"*{ext}")))
        mask_map = {os.path.splitext(os.path.basename(f))[0]: f for f in mask_files}

        basenames = set(img_map.keys())

        # Check missing masks
        missing_masks = basenames - set(mask_map.keys())
        for m in sorted(missing_masks):
            errors.append(f"[{split_name}] Image '{m}' has no corresponding mask in {masks_dir}")

        # Check orphaned masks
        orphaned_masks = set(mask_map.keys()) - basenames
        for o in sorted(orphaned_masks):
            warnings.append(f"[{split_name}] Mask '{o}' has no corresponding image in {images_dir}")

        # Check dimensions & valid values for matched pairs
        matched = basenames & set(mask_map.keys())
        for bname in sorted(matched):
            img_path = img_map[bname]
            mask_path = mask_map[bname]

            img_shape, img_err = cls._read_image_shape_and_stats(img_path)
            if img_err:
                errors.append(f"[{split_name}] {img_err}")
                continue

            mask_shape, is_binary, mask_err = cls._read_mask_shape_and_stats(mask_path)
            if mask_err:
                errors.append(f"[{split_name}] {mask_err}")
                continue

            if img_shape != mask_shape:
                errors.append(
                    f"[{split_name}] Dimension mismatch for '{bname}': "
                    f"image {img_shape} vs mask {mask_shape}"
                )

            if not is_binary:
                warnings.append(
                    f"[{split_name}] Mask '{bname}' contains non-binary values (will be thresholded at 0.5)."
                )

        valid = len(errors) == 0 and len(matched) > 0
        return {
            "split": split_name,
            "valid": valid,
            "count": len(matched),
            "errors": errors,
            "warnings": warnings,
            "basenames": basenames,
        }

    @classmethod
    def validate_dataset(cls, dataset_dir: str) -> Dict[str, Any]:
        """
        Validates complete dataset structure:
        dataset_dir/
            train/ (images, masks)
            val/   (images, masks)
            test/  (images, masks) [optional]
        Or flat:
            images/, masks/
        """
        if not os.path.exists(dataset_dir):
            return {
                "valid": False,
                "dataset_dir": dataset_dir,
                "error": f"Dataset directory '{dataset_dir}' does not exist.",
                "total_images": 0,
            }

        # Check if structured splits exist
        has_train = os.path.exists(os.path.join(dataset_dir, "train"))
        has_val = os.path.exists(os.path.join(dataset_dir, "val"))
        has_test = os.path.exists(os.path.join(dataset_dir, "test"))

        all_errors: List[str] = []
        all_warnings: List[str] = []
        splits_info: Dict[str, Any] = {}

        if has_train or has_val:
            # Structured train/val/test mode
            train_info = cls.validate_split_directory("train", os.path.join(dataset_dir, "train"))
            val_info = cls.validate_split_directory("val", os.path.join(dataset_dir, "val"))
            splits_info["train"] = train_info
            splits_info["val"] = val_info
            all_errors.extend(train_info["errors"])
            all_warnings.extend(train_info["warnings"])
            all_errors.extend(val_info["errors"])
            all_warnings.extend(val_info["warnings"])

            if has_test:
                test_info = cls.validate_split_directory("test", os.path.join(dataset_dir, "test"))
                splits_info["test"] = test_info
                all_errors.extend(test_info["errors"])
                all_warnings.extend(test_info["warnings"])

            # Check train/val/test separation (data leakage check)
            train_names = train_info.get("basenames", set())
            val_names = val_info.get("basenames", set())
            leak_train_val = train_names & val_names
            if leak_train_val:
                all_errors.append(f"Data leakage detected! {len(leak_train_val)} samples appear in both train and val: {sorted(list(leak_train_val))[:5]}")

            if has_test:
                test_names = splits_info["test"].get("basenames", set())
                leak_train_test = train_names & test_names
                leak_val_test = val_names & test_names
                if leak_train_test:
                    all_errors.append(f"Data leakage detected! {len(leak_train_test)} samples appear in both train and test: {sorted(list(leak_train_test))[:5]}")
                if leak_val_test:
                    all_errors.append(f"Data leakage detected! {len(leak_val_test)} samples appear in both val and test: {sorted(list(leak_val_test))[:5]}")

            total_count = sum(s["count"] for s in splits_info.values())
            is_valid = len(all_errors) == 0 and train_info["count"] > 0 and val_info["count"] > 0

            return {
                "valid": is_valid,
                "dataset_dir": dataset_dir,
                "mode": "SPLIT_STRUCTURE",
                "splits": {k: {"count": v["count"], "valid": v["valid"]} for k, v in splits_info.items()},
                "total_images": total_count,
                "errors": all_errors,
                "warnings": all_warnings,
            }
        else:
            # Flat mode: images/ and masks/
            flat_info = cls.validate_split_directory("flat", dataset_dir)
            return {
                "valid": flat_info["valid"],
                "dataset_dir": dataset_dir,
                "mode": "FLAT_STRUCTURE",
                "total_images": flat_info["count"],
                "errors": flat_info["errors"],
                "warnings": flat_info["warnings"],
            }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="OILTRACE SAR Dataset Validator")
    parser.add_argument("--data-dir", default="./data/dataset", help="Path to dataset directory")
    args = parser.parse_args()

    report = DatasetValidator.validate_dataset(args.data_dir)
    print("=" * 60)
    print("OILTRACE DATASET VALIDATION REPORT")
    print("=" * 60)
    print(f"Dataset Directory : {report['dataset_dir']}")
    print(f"Valid Dataset     : {'YES' if report['valid'] else 'NO'}")
    print(f"Total Valid Pairs : {report.get('total_images', 0)}")
    if "splits" in report:
        for split, info in report["splits"].items():
            print(f"  - {split.upper():6s} : {info['count']} samples (Valid: {info['valid']})")
    if report.get("errors"):
        print("\nERRORS DETECTED:")
        for err in report["errors"][:10]:
            print(f"  [X] {err}")
    if report.get("warnings"):
        print("\nWARNINGS:")
        for w in report["warnings"][:10]:
            print(f"  [!] {w}")
    print("=" * 60)
