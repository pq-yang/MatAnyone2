from dataclasses import dataclass
from enum import StrEnum


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
