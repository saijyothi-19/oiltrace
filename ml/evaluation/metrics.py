import numpy as np
from typing import Dict

def calculate_segmentation_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    threshold: float = 0.5,
    eps: float = 1e-7
) -> Dict[str, float]:
    """
    Computes scientific segmentation evaluation metrics:
    - Intersection over Union (IoU / Jaccard Index)
    - Dice Similarity Coefficient (F1-score)
    - Precision
    - Recall
    """
    pred_bin = (y_pred >= threshold).astype(np.uint8)
    true_bin = (y_true >= 0.5).astype(np.uint8)

    intersection = np.sum(pred_bin & true_bin)
    union = np.sum(pred_bin | true_bin)
    pred_sum = np.sum(pred_bin)
    true_sum = np.sum(true_bin)

    iou = float((intersection + eps) / (union + eps))
    dice = float((2.0 * intersection + eps) / (pred_sum + true_sum + eps))
    precision = float((intersection + eps) / (pred_sum + eps))
    recall = float((intersection + eps) / (true_sum + eps))
    f1 = float(2.0 * (precision * recall) / (precision + recall + eps))

    return {
        "iou": round(iou, 4),
        "dice": round(dice, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }
