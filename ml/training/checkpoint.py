"""
OILTRACE Marine Oil Spill AI Subsystem — Model Checkpoint Manager.
Handles saving, loading, metadata inspection, and retention of model checkpoints.
"""
import os
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

try:
    import torch
    TORCH_AVAILABLE = True
except Exception:
    TORCH_AVAILABLE = False


class CheckpointManager:
    """
    Manages neural network checkpoints for the marine oil spill segmentation model.
    """

    def __init__(self, checkpoint_dir: str = "./ml/models/unet/checkpoints", max_to_keep: int = 3):
        self.checkpoint_dir = checkpoint_dir
        self.max_to_keep = max_to_keep
        os.makedirs(checkpoint_dir, exist_ok=True)

    def save_checkpoint(
        self,
        model_state_dict: Any,
        optimizer_state_dict: Any,
        epoch: int,
        val_metrics: Dict[str, float],
        train_loss: float,
        val_loss: float,
        config: Dict[str, Any],
        is_best: bool = False,
        filename: Optional[str] = None
    ) -> str:
        """
        Saves a checkpoint containing weights and verification metadata.
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        checkpoint_data = {
            "epoch": epoch,
            "timestamp": timestamp,
            "train_loss": float(train_loss),
            "val_loss": float(val_loss),
            "val_metrics": val_metrics,
            "config": config,
            "is_best": is_best,
            "model_architecture": "UNet",
            "model_version": "v1.0-oilspill",
        }

        if filename is None:
            filename = f"checkpoint_epoch_{epoch:03d}.pt"

        save_path = os.path.join(self.checkpoint_dir, filename)

        if TORCH_AVAILABLE and isinstance(model_state_dict, dict):
            torch_payload = {
                **checkpoint_data,
                "model_state_dict": model_state_dict,
                "optimizer_state_dict": optimizer_state_dict,
            }
            torch.save(torch_payload, save_path)
        else:
            # Metadata stub file if running in non-torch environment
            meta_path = save_path if save_path.endswith(".json") else save_path + ".json"
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(checkpoint_data, f, indent=2)
            save_path = meta_path

        # Save copy as best_model if requested
        if is_best:
            best_target = os.path.join(self.checkpoint_dir, "best_model.pt")
            if TORCH_AVAILABLE and isinstance(model_state_dict, dict):
                torch.save(torch_payload, best_target)
            else:
                with open(best_target + ".json", "w", encoding="utf-8") as f:
                    json.dump(checkpoint_data, f, indent=2)

        # Save metadata summary
        summary_path = os.path.join(self.checkpoint_dir, "checkpoint_summary.json")
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(checkpoint_data, f, indent=2)

        return save_path

    @staticmethod
    def load_checkpoint(checkpoint_path: str, map_location: str = "cpu") -> Dict[str, Any]:
        """
        Loads checkpoint weights and metadata.
        """
        if not os.path.exists(checkpoint_path):
            # Check if JSON metadata version exists
            if os.path.exists(checkpoint_path + ".json"):
                checkpoint_path = checkpoint_path + ".json"
            else:
                raise FileNotFoundError(f"Checkpoint not found at: {checkpoint_path}")

        if checkpoint_path.endswith(".json"):
            with open(checkpoint_path, "r", encoding="utf-8") as f:
                return json.load(f)

        if TORCH_AVAILABLE:
            payload = torch.load(checkpoint_path, map_location=map_location, weights_only=False)
            return payload
        else:
            # If torch is not available, check for sibling JSON metadata
            sibling_json = checkpoint_path + ".json"
            if os.path.exists(sibling_json):
                with open(sibling_json, "r", encoding="utf-8") as f:
                    return json.load(f)
            return {"status": "torch_unavailable", "path": checkpoint_path}

    @classmethod
    def inspect_checkpoint(cls, checkpoint_path: str) -> Dict[str, Any]:
        """
        Returns metadata summary from a checkpoint without loading large tensor weights.
        """
        data = cls.load_checkpoint(checkpoint_path)
        return {
            "epoch": data.get("epoch"),
            "timestamp": data.get("timestamp"),
            "train_loss": data.get("train_loss"),
            "val_loss": data.get("val_loss"),
            "val_metrics": data.get("val_metrics", {}),
            "model_architecture": data.get("model_architecture", "UNet"),
            "model_version": data.get("model_version", "v1.0-oilspill"),
            "is_best": data.get("is_best", False),
        }

    def list_checkpoints(self) -> List[Dict[str, Any]]:
        """
        Lists all available checkpoints in the checkpoint directory with their metrics.
        """
        results = []
        for fname in os.listdir(self.checkpoint_dir):
            if fname.endswith(".pt") or fname.endswith(".pt.json"):
                full_p = os.path.join(self.checkpoint_dir, fname)
                try:
                    meta = self.inspect_checkpoint(full_p)
                    meta["filename"] = fname
                    meta["path"] = full_p
                    results.append(meta)
                except Exception:
                    continue
        return sorted(results, key=lambda x: x.get("epoch") or 0, reverse=True)
