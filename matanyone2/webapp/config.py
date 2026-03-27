from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(slots=True)
class WebAppSettings:
    runtime_root: Path = Path(
        os.getenv("MATANYONE2_WEBAPP_RUNTIME_ROOT", "runtime/webapp")
    )
    database_path: Path = Path(
        os.getenv("MATANYONE2_WEBAPP_DATABASE_PATH", "runtime/webapp/jobs.db")
    )
    max_video_seconds: int = int(
        os.getenv("MATANYONE2_WEBAPP_MAX_VIDEO_SECONDS", "10")
    )
    max_upload_bytes: int = int(
        os.getenv(
            "MATANYONE2_WEBAPP_MAX_UPLOAD_BYTES",
            str(2 * 1024 * 1024 * 1024),
        )
    )
    enable_prores_export: bool = (
        os.getenv("MATANYONE2_WEBAPP_ENABLE_PRORES", "1") == "1"
    )
    sam_backend: str = os.getenv("MATANYONE2_WEBAPP_SAM_BACKEND", "sam2")
    sam_model_type: str = os.getenv("MATANYONE2_WEBAPP_SAM_MODEL_TYPE", "vit_h")
    sam2_variant: str = os.getenv(
        "MATANYONE2_WEBAPP_SAM2_VARIANT",
        "sam2.1_hiera_large",
    )
    sam2_checkpoint_path: str | None = os.getenv(
        "MATANYONE2_WEBAPP_SAM2_CHECKPOINT_PATH"
    )
