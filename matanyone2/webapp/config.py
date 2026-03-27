from dataclasses import dataclass
from pathlib import Path
import os


def _default_sam3_checkpoint_path() -> str:
    candidates = [
        os.getenv("MATANYONE2_WEBAPP_SAM3_CHECKPOINT_PATH"),
        r"D:\my_app\lens_hunter2\models\sam3\checkpoints\sam3.pt",
        str(Path("pretrained_models") / "sam3.pt"),
    ]
    for candidate in candidates:
        if not candidate:
            continue
        if Path(candidate).exists():
            return str(candidate)
    for candidate in candidates:
        if candidate:
            return str(candidate)
    return str(Path("pretrained_models") / "sam3.pt")


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
    sam_backend: str = os.getenv("MATANYONE2_WEBAPP_SAM_BACKEND", "sam3")
    sam_model_type: str = os.getenv("MATANYONE2_WEBAPP_SAM_MODEL_TYPE", "vit_h")
    sam2_variant: str = os.getenv(
        "MATANYONE2_WEBAPP_SAM2_VARIANT",
        "sam2.1_hiera_large",
    )
    sam2_checkpoint_path: str | None = os.getenv(
        "MATANYONE2_WEBAPP_SAM2_CHECKPOINT_PATH"
    )
    sam3_checkpoint_path: str = _default_sam3_checkpoint_path()
