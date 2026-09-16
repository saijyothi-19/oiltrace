"""
OILTRACE Marine Oil Spill AI Subsystem — Training Configuration.
Defines hyperparameters, loss function parameters, optimizer settings, and device configuration.
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

@dataclass
class TrainingConfig:
    # Model Architecture
    model_name: str = "unet_oilspill"
    in_channels: int = 1
    out_channels: int = 1
    base_filters: int = 32
    dropout: float = 0.1

    # Training Hyperparameters
    batch_size: int = 4
    num_epochs: int = 10
    learning_rate: float = 1e-4
    weight_decay: float = 1e-4
    loss_type: str = "bce_dice"  # 'bce_dice', 'bce', or 'dice'
    bce_weight: float = 0.5
    dice_weight: float = 0.5
    lr_scheduler: str = "cosine"  # 'cosine', 'step', or 'none'
    lr_step_size: int = 5
    lr_gamma: float = 0.5

    # Early Stopping & Validation
    early_stopping_patience: int = 5
    min_delta: float = 1e-4
    threshold: float = 0.5

    # Data & Tiling
    tile_size: int = 256
    val_split: float = 0.2
    augment: bool = True
    seed: int = 42

    # Hardware & Paths
    device: str = "auto"  # 'cuda', 'cpu', or 'auto'
    checkpoint_dir: str = "./ml/models/unet/checkpoints"
    dataset_dir: str = "./data/synthetic/oil_spill_training"
    log_dir: str = "./ml/training/logs"

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TrainingConfig":
        valid_keys = {f for f in cls.__dataclass_fields__}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)
