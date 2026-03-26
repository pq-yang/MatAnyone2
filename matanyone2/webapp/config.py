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
