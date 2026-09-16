"""
OILTRACE Marine Oil Spill AI Subsystem — Batch Model Evaluator.
Computes dataset-wide empirical metrics (mIoU, mDice, Precision, Recall, F1, Confusion Matrix)
and generates standardized evaluation reports.
"""
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import json
import numpy as np
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from ml.evaluation.metrics import calculate_segmentation_metrics
from ml.inference.infer import OilSpillInferenceEngine
from ml.datasets.oil_spill_dataset import OilSpillDataset

class ModelEvaluator:
    """
    Evaluates segmentation models against ground-truth datasets.
    """

    def __init__(
        self,
        inference_engine: Optional[OilSpillInferenceEngine] = None,
        threshold: float = 0.5
    ):
        self.threshold = threshold
        self.engine = inference_engine or OilSpillInferenceEngine(threshold=threshold)

    def evaluate_dataset(
        self,
        dataset_dir: str,
        output_report_path: Optional[str] = None
    ) -> Dict[str, Any]:
        images_dir = os.path.join(dataset_dir, "images")
        masks_dir = os.path.join(dataset_dir, "masks")

        if not os.path.exists(images_dir) or not os.path.exists(masks_dir):
            raise FileNotFoundError(f"Dataset directory must contain 'images' and 'masks' subdirectories: {dataset_dir}")

        ds = OilSpillDataset(images_dir=images_dir, masks_dir=masks_dir, augment=False)
        if len(ds) == 0:
            raise ValueError(f"No test images found in {images_dir}")

        per_sample_metrics = []
        total_tp = 0
        total_fp = 0
        total_tn = 0
        total_fn = 0

        ious = []
        dices = []
        precisions = []
        recalls = []
        f1s = []

        for i in range(len(ds)):
            item = ds[i]
            img = item["image"]
            if isinstance(img, np.ndarray):
                arr = img.squeeze()
            else:
                arr = img.squeeze().cpu().numpy()

            true_mask = item["mask"]
            if isinstance(true_mask, np.ndarray):
                t_arr = true_mask.squeeze()
            else:
                t_arr = true_mask.squeeze().cpu().numpy()

            # Run inference
            res = self.engine.segment_sar_array(arr)
            prob_map = res["probability_map"]
            pred_bin = (prob_map >= self.threshold).astype(np.uint8)
            true_bin = (t_arr >= 0.5).astype(np.uint8)

            # Metrics for this sample
            m = calculate_segmentation_metrics(true_bin, pred_bin, threshold=0.5)
            m["sample_id"] = item["id"]
            per_sample_metrics.append(m)

            ious.append(m["iou"])
            dices.append(m["dice"])
            precisions.append(m["precision"])
            recalls.append(m["recall"])
            f1s.append(m["f1"])

            # Confusion matrix accumulation
            tp = int(np.sum((pred_bin == 1) & (true_bin == 1)))
            fp = int(np.sum((pred_bin == 1) & (true_bin == 0)))
            tn = int(np.sum((pred_bin == 0) & (true_bin == 0)))
            fn = int(np.sum((pred_bin == 0) & (true_bin == 1)))

            total_tp += tp
            total_fp += fp
            total_tn += tn
            total_fn += fn

        total_pixels = total_tp + total_fp + total_tn + total_fn
        pixel_accuracy = float((total_tp + total_tn) / max(total_pixels, 1))
        specificity = float(total_tn / max(total_tn + total_fp, 1))

        summary = {
            "evaluation_timestamp": datetime.now(timezone.utc).isoformat(),
            "total_samples": len(ds),
            "threshold": self.threshold,
            "mean_metrics": {
                "mean_iou": round(float(np.mean(ious)), 4),
                "mean_dice": round(float(np.mean(dices)), 4),
                "mean_precision": round(float(np.mean(precisions)), 4),
                "mean_recall": round(float(np.mean(recalls)), 4),
                "mean_f1": round(float(np.mean(f1s)), 4),
                "pixel_accuracy": round(pixel_accuracy, 4),
                "specificity": round(specificity, 4),
            },
            "confusion_matrix_pixels": {
                "true_positives": total_tp,
                "false_positives": total_fp,
                "true_negatives": total_tn,
                "false_negatives": total_fn,
            },
            "samples": per_sample_metrics,
        }

        if output_report_path:
            os.makedirs(os.path.dirname(output_report_path), exist_ok=True)
            with open(output_report_path, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2)
            summary["report_path"] = output_report_path

        return summary
