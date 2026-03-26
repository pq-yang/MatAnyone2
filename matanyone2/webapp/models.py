from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class JobStatus(StrEnum):
    QUEUED = "queued"
    PREPARING = "preparing"
    RUNNING = "running"
    EXPORTING = "exporting"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNING = "completed_with_warning"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


@dataclass(slots=True)
class JobRecord:
    job_id: str
    status: JobStatus
    source_video_path: str
    mask_path: str
    template_frame_index: int
    params_json: str
    warning_text: str | None
    error_text: str | None


@dataclass(slots=True)
class DraftRecord:
    draft_id: str
    video_path: Path
    template_frame_path: Path
    width: int
    height: int
    fps: float
    frame_count: int
    duration_seconds: float


@dataclass(slots=True)
class DraftSession:
    draft: DraftRecord
    session_dir: Path
    click_points: list[tuple[int, int]] = field(default_factory=list)
    click_labels: list[int] = field(default_factory=list)
    saved_masks: dict[str, Path] = field(default_factory=dict)
    current_mask_path: Path | None = None
    current_preview_path: Path | None = None


@dataclass(slots=True)
class MaskingResult:
    current_mask_path: Path
    current_preview_path: Path


@dataclass(slots=True)
class InferenceResult:
    foreground_video_path: Path
    alpha_video_path: Path


@dataclass(slots=True)
class ExportResult:
    rgba_png_dir: Path
    png_zip_path: Path
    prores_path: Path | None
    warning_text: str | None
