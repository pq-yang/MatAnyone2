from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class DesktopAppConfig:
    project_root: Path
    runtime_root: Path
    window_title: str
    default_step: str
    sam_backend: str
    sam3_checkpoint_path: Path
    max_video_seconds: int
    max_upload_bytes: int

    @classmethod
    def for_root(cls, project_root: Path) -> "DesktopAppConfig":
        project_root = Path(project_root)
        return cls(
            project_root=project_root,
            runtime_root=project_root / "runtime" / "desktop_workbench",
            window_title="MatAnyone2 Desktop Workbench",
            default_step="clip",
            sam_backend="sam3",
            sam3_checkpoint_path=Path(
                r"D:\my_app\lens_hunter2\models\sam3\checkpoints\sam3.pt"
            ),
            max_video_seconds=60,
            max_upload_bytes=2 * 1024 * 1024 * 1024,
        )
