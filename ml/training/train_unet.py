#!/usr/bin/env python3
"""
OILTRACE Marine Oil Spill AI Subsystem — U-Net Training CLI.
Executes supervised training of the deep convolutional U-Net model for SAR oil spill detection.

Features:
- Reproducible random seeding across random, NumPy, and PyTorch.
- Configurable hyperparameters (epochs, batch size, learning rate, loss weighting).
- Dataset integrity validation (checks splits, dimensions, corruption, data leakage).
- Loss functions: BCE + Soft Dice, BCE, or Dice.
- Checkpointing and automatic selection of best model weights based on validation IoU.
- Saves weights directly to data/models/best_model.pt upon genuine training.
- Verification hook ensuring inference transitions from ANALYTICAL_CONTRAST to UNET.
"""

import os
import sys
import argparse
import json
import time

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ml.training.train_config import TrainingConfig
from ml.training.train import OilSpillTrainer, TORCH_AVAILABLE
from ml.datasets.dataset_validator import DatasetValidator
from ml.inference.infer import OilSpillInferenceEngine


def parse_args():
    parser = argparse.ArgumentParser(
        description="OILTRACE U-Net Marine Oil Spill Training Pipeline (SIH26143)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default=os.path.join(PROJECT_ROOT, "data", "dataset"),
        help="Path to dataset directory containing train/val/test splits or flat images/masks"
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=20,
        help="Number of training epochs"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=8,
        help="Mini-batch size for training and validation loaders"
    )
    parser.add_argument(
        "--lr",
        type=float,
        default=1e-4,
        help="Initial learning rate for AdamW optimizer"
    )
    parser.add_argument(
        "--loss",
        type=str,
        default="bce_dice",
        choices=["bce_dice", "bce", "dice"],
        help="Segmentation loss objective"
    )
    parser.add_argument(
        "--bce-weight",
        type=float,
        default=0.5,
        help="Weight for BCE component in combined loss"
    )
    parser.add_argument(
        "--dice-weight",
        type=float,
        default=0.5,
        help="Weight for Soft Dice component in combined loss"
    )
    parser.add_argument(
        "--val-split",
        type=float,
        default=0.2,
        help="Validation split ratio (used when flat images/masks directory is provided)"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Deterministic random seed for Python, NumPy, and PyTorch"
    )
    parser.add_argument(
        "--save-path",
        type=str,
        default=os.path.join(PROJECT_ROOT, "data", "models", "best_model.pt"),
        help="Target destination path for best model checkpoint"
    )
    parser.add_argument(
        "--checkpoint-dir",
        type=str,
        default=os.path.join(PROJECT_ROOT, "ml", "models", "unet", "checkpoints"),
        help="Directory to store epoch checkpoints and history summary"
    )
    parser.add_argument(
        "--device",
        type=str,
        default="auto",
        choices=["auto", "cuda", "cpu"],
        help="Compute hardware target ('auto' detects CUDA GPU if available)"
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate dataset integrity and statistics without training"
    )
    return parser.parse_args()


def print_banner():
    print("=" * 70)
    print("  OILTRACE — Deep Convolutional U-Net Training Suite (SIH26143)")
    print("  Supervised Satellite SAR Marine Oil Spill Segmentation")
    print("=" * 70)


def main():
    print_banner()
    args = parse_args()

    # -------------------------------------------------------------
    # STEP 1: DATASET INTEGRITY VALIDATION
    # -------------------------------------------------------------
    print(f"\n[STEP 1/4] Validating Dataset Integrity: {args.data_dir}")
    if not os.path.exists(args.data_dir):
        print(f"\n[ERROR] Dataset directory not found: {args.data_dir}")
        print("Please create the dataset structure or point --data-dir to your dataset:")
        print("  data/dataset/")
        print("    train/  -> images/ and masks/")
        print("    val/    -> images/ and masks/")
        print("    test/   -> images/ and masks/")
        sys.exit(1)

    val_report = DatasetValidator.validate_dataset(args.data_dir)
    print(f"  Mode:            {val_report.get('mode')}")
    print(f"  Total Images:    {val_report.get('total_images', 0)}")

    if "splits" in val_report:
        for split, info in val_report["splits"].items():
            print(f"    - Split '{split}': {info.get('count', 0)} samples (Valid: {info.get('valid')})")

    if val_report.get("warnings"):
        print(f"  Warnings ({len(val_report['warnings'])}):")
        for w in val_report["warnings"][:5]:
            print(f"    [!] {w}")

    if not val_report["valid"]:
        print("\n[ERROR] Dataset validation failed with errors:")
        if val_report.get("errors"):
            for err in val_report.get("errors", [])[:10]:
                print(f"    [X] {err}")
        else:
            print("    [X] Dataset splits are empty (0 images found). Please add real SAR images and masks into the directories:")
            print("        - data/dataset/train/images/ and data/dataset/train/masks/")
            print("        - data/dataset/val/images/ and data/dataset/val/masks/")
        print("\nPlease fix the above dataset errors before training.")
        sys.exit(1)

    print("  [OK] Dataset integrity passed all checks (existence, matching dimensions, binary masks, no data leakage).")

    if args.validate_only:
        print("\n[INFO] --validate-only requested. Exiting successfully.")
        sys.exit(0)

    # -------------------------------------------------------------
    # STEP 2: ENVIRONMENT & PYTORCH VERIFICATION
    # -------------------------------------------------------------
    print("\n[STEP 2/4] Verifying Machine Learning Environment...")
    if not TORCH_AVAILABLE:
        print("\n[ERROR] PyTorch (torch) is not available or failed to load on this Python installation.")
        print("PyTorch with C-extensions is strictly required to train the U-Net architecture and produce weights.")
        print("\nTo resolve this:")
        print("  1. Ensure a compatible Python version is used (e.g. Python 3.10, 3.11, or 3.12).")
        print("  2. Install PyTorch via pip or conda:")
        print("     pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121  (CUDA)")
        print("     pip install torch torchvision                                                    (CPU)")
        print("\nNo fake weights or placeholders will be generated.")
        sys.exit(1)

    import torch
    device_name = "cuda" if (args.device == "cuda" or (args.device == "auto" and torch.cuda.is_available())) else "cpu"
    print(f"  PyTorch Version: {torch.__version__}")
    print(f"  Compute Target:  {device_name.upper()} ({torch.cuda.get_device_name(0) if device_name == 'cuda' else 'Host CPU'})")

    # -------------------------------------------------------------
    # STEP 3: CONFIGURE TRAINING PIPELINE
    # -------------------------------------------------------------
    print("\n[STEP 3/4] Initializing Training Configuration...")
    config = TrainingConfig(
        dataset_dir=args.data_dir,
        num_epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
        loss_type=args.loss,
        bce_weight=args.bce_weight,
        dice_weight=args.dice_weight,
        val_split=args.val_split,
        seed=args.seed,
        checkpoint_dir=args.checkpoint_dir,
        device=device_name
    )

    print(f"  Hyperparameters:")
    print(f"    - Epochs:         {config.num_epochs}")
    print(f"    - Batch Size:     {config.batch_size}")
    print(f"    - Learning Rate:  {config.learning_rate}")
    print(f"    - Loss Type:      {config.loss_type} (BCE: {config.bce_weight}, Dice: {config.dice_weight})")
    print(f"    - Random Seed:    {config.seed}")
    print(f"    - Checkpoint Dir: {config.checkpoint_dir}")
    print(f"    - Model Save Path:{args.save_path}")

    trainer = OilSpillTrainer(config)

    # -------------------------------------------------------------
    # STEP 4: EXECUTE TRAINING
    # -------------------------------------------------------------
    print("\n[STEP 4/4] Executing U-Net Training Loop...")
    start_wall_time = time.time()
    result = trainer.train()
    total_time = time.time() - start_wall_time

    # Ensure best model is placed at args.save_path
    checkpoint_best = os.path.join(args.checkpoint_dir, "best_model.pt")
    if os.path.exists(checkpoint_best) and args.save_path != checkpoint_best:
        import shutil
        os.makedirs(os.path.dirname(args.save_path), exist_ok=True)
        shutil.copy2(checkpoint_best, args.save_path)

    # -------------------------------------------------------------
    # VERIFY TRAINED MODEL & INFERENCE ACTIVATION
    # -------------------------------------------------------------
    print("\n" + "=" * 70)
    print("  TRAINING COMPLETE — VERIFICATION SUMMARY")
    print("=" * 70)
    print(f"  Total Duration:     {total_time:.2f} seconds")
    print(f"  Best Epoch:         {result.get('best_epoch')}")
    print(f"  Best Validation IoU:{result.get('best_val_iou', 0.0):.4f}")
    print(f"  History Saved To:   {result.get('history_path')}")

    if os.path.exists(args.save_path):
        print(f"  Model Saved To:     {args.save_path} ({os.path.getsize(args.save_path) / (1024*1024):.2f} MB)")
        # Test loading into inference engine
        test_engine = OilSpillInferenceEngine(model_path=args.save_path)
        if test_engine.torch_model is not None:
            print("\n  [VERIFIED] Active Inference Transition Successful:")
            print("    * Model Type:     UNET (Deep Convolutional U-Net)")
            print("    * Is Demo:        False (Production Neural Segmentation)")
            print("    * Inference Mode: PYTORCH_SLIDING_WINDOW_HANN")
            print("    * Checkpoint:     " + args.save_path)
            print("\nOILTRACE backend and dashboard will now automatically utilize the trained U-Net weights!")
        else:
            print("\n  [WARNING] Saved weights file exists but could not be loaded into U-Net inference engine.")
    else:
        print("\n  [NOTICE] No model weights saved (either no improvement or non-torch environment).")

    print("=" * 70)


if __name__ == "__main__":
    main()
