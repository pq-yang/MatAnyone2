from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

try:
    from enum import StrEnum
except ImportError:  # pragma: no cover - Python < 3.11 compatibility
    class StrEnum(str, Enum):
        pass


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
    template_frame_index: int = 0


@dataclass(slots=True)
class AnnotationTarget:
    target_id: str
    name: str
    click_points: list[tuple[int, int]] = field(default_factory=list)
    click_labels: list[int] = field(default_factory=list)
    saved_mask_name: str | None = None
    visible: bool = True
    locked: bool = False
    refine_preset: str = "balanced"
    preset_strength: float = 0.5
    motion_strength: float = 0.35
    temporal_stability: float = 0.0


@dataclass(slots=True)
class DraftSession:
    draft: DraftRecord
    session_dir: Path
    targets: dict[str, AnnotationTarget] = field(default_factory=dict)
    active_target_id: str | None = None
    saved_masks: dict[str, Path] = field(default_factory=dict)
    saved_mask_presets: dict[str, str] = field(default_factory=dict)
    selected_mask_names: set[str] = field(default_factory=set)
    current_mask_base_path: Path | None = None
    current_mask_path: Path | None = None
    current_preview_path: Path | None = None
    stage: str = "coarse"
    _target_sequence: int = 0

    def __post_init__(self):
        if not self.targets:
            self.create_target()
        elif self.active_target_id is None:
            self.active_target_id = next(iter(self.targets))
            self._target_sequence = len(self.targets)

    @property
    def active_target(self) -> AnnotationTarget:
        if self.active_target_id is None or self.active_target_id not in self.targets:
            return self.create_target()
        return self.targets[self.active_target_id]

    @property
    def click_points(self) -> list[tuple[int, int]]:
        return self.active_target.click_points

    @click_points.setter
    def click_points(self, value: list[tuple[int, int]]):
        self.active_target.click_points = list(value)

    @property
    def click_labels(self) -> list[int]:
        return self.active_target.click_labels

    @click_labels.setter
    def click_labels(self, value: list[int]):
        self.active_target.click_labels = list(value)

    def create_target(self, name: str | None = None) -> AnnotationTarget:
        self._target_sequence += 1
        target = AnnotationTarget(
            target_id=f"target-{self._target_sequence:03d}",
            name=name or f"Target {self._target_sequence}",
        )
        self.targets[target.target_id] = target
        self.active_target_id = target.target_id
        return target

    def select_target(self, target_id: str) -> AnnotationTarget:
        if target_id not in self.targets:
            raise KeyError(target_id)
        self.active_target_id = target_id
        return self.targets[target_id]


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
