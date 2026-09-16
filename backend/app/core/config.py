import os
from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    PROJECT_NAME: str = "OILTRACE"
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    SECRET_KEY: str = "oiltrace_super_secret_jwt_key_2026_marine_decision_support_prototype"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    DATABASE_URL: str = "sqlite:///./oiltrace.db"

    @field_validator("DATABASE_URL", mode="after")
    @classmethod
    def assemble_db_connection(cls, v: str) -> str:
        if v.startswith("sqlite:///.") or v.startswith("sqlite:////."):
            backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            rel_path = v.split("sqlite:///", 1)[-1].lstrip("./\\")
            abs_db_path = os.path.join(backend_dir, rel_path).replace("\\", "/")
            return f"sqlite:///{abs_db_path}"
        return v

    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://localhost:8000",
    ]

    # ML & Segmentation
    MODEL_CHECKPOINT_DIR: str = "./ml/models/unet/checkpoints"
    BASELINE_MODEL_PATH: str = "./ml/models/unet/checkpoints/unet_oilspill_baseline.pt"
    INFERENCE_THRESHOLD: float = 0.5
    MIN_SPILL_AREA_KM2: float = 0.01

    # Drift Engine
    DRIFT_DEFAULT_PARTICLES: int = 150
    DRIFT_DEFAULT_DURATION_HOURS: int = 12
    DRIFT_TIMESTEP_MINUTES: int = 15
    WINDAGE_FACTOR: float = 0.03
    WIND_DEFLECTION_ANGLE_DEG: float = 10.0

    # AIS Correlation
    SPATIAL_RADIUS_KM: float = 50.0
    TEMPORAL_WINDOW_HOURS: float = 12.0

    # Directories
    DATA_DIR: str = "./data"
    SATELLITE_DIR: str = "./data/satellite"
    AIS_DIR: str = "./data/ais"
    ENVIRONMENTAL_DIR: str = "./data/environmental"
    DEMO_DIR: str = "./data/demo"
    REPORTS_DIR: str = "./reports"

    DISCLAIMER_TEXT: str = (
        "This report provides analytical decision support based on available satellite, "
        "environmental and AIS data. Candidate rankings do not establish legal responsibility or causation."
    )

settings = Settings()
