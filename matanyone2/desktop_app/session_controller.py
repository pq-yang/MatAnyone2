from dataclasses import dataclass
import json
from pathlib import Path
import uuid

from matanyone2.desktop_app.config import DesktopAppConfig
from matanyone2.webapp.models import DraftRecord, DraftSession
from matanyone2.webapp.services.masking import MaskingService
from matanyone2.webapp.services.video import VideoDraftService


@dataclass(slots=True)
class DesktopSessionState:
    workflow_step: str
    active_sidebar_tab: str
    process_start_frame_index: int
    process_end_frame_index: int
    template_frame_index: int | None
    can_enter_mask: bool
    can_enter_refine: bool
    saved_mask_names: list[str]
    active_target_id: str
    active_target_name: str
    stage: str
    current_preview_path: Path | None
    current_mask_path: Path | None
    selected_mask_names: list[str]
    targets: list[dict]
    latest_job_id: str | None = None


class DesktopWorkbenchController:
    def __init__(
        self,
        *,
        config: DesktopAppConfig,
        video_service: VideoDraftService,
        masking_service: MaskingService,
        inference_service=None,
        export_service=None,
    ):
        self.config = config
        self.video_service = video_service
        self.masking_service = masking_service
        self.inference_service = inference_service
        self.export_service = export_service
        self._draft: DraftRecord | None = None
        self._session: DraftSession | None = None
        self._latest_job_payload: dict | None = None

    @property
    def draft(self) -> DraftRecord:
        if self._draft is None:
            raise RuntimeError("open a video before accessing draft state")
        return self._draft

    @property
    def session(self) -> DraftSession:
        if self._session is None:
            raise RuntimeError("open a video before accessing session state")
        return self._session

    def open_video(self, video_path: str | Path) -> DesktopSessionState:
        self._draft = self.video_service.create_draft(Path(video_path))
        self._session = self.masking_service.create_session(self._draft)
        self._session.workflow_step = self.config.default_step
        self._session.active_sidebar_tab = "targets"
        return self.current_state()

    def apply_processing_range(
        self,
        *,
        start_frame_index: int,
        end_frame_index: int,
    ) -> DesktopSessionState:
        self.video_service.select_processing_range(
            self.draft,
            start_frame_index=start_frame_index,
            end_frame_index=end_frame_index,
        )
        self.masking_service.reset_session_for_processing_range(self.session)
        self.session.workflow_step = "clip"
        self.session.active_sidebar_tab = "targets"
        return self.current_state()

    def apply_anchor(self, *, frame_index: int) -> DesktopSessionState:
        self.video_service.select_template_frame(self.draft, frame_index)
        self.masking_service.reset_session_for_template_frame(self.session, frame_index=frame_index)
        self.session.workflow_step = "mask"
        self.session.active_sidebar_tab = "targets"
        return self.current_state()

    def create_target(self, name: str | None = None) -> DesktopSessionState:
        self.masking_service.create_target(self.session, name=name)
        return self.current_state()

    def select_target(self, target_id: str) -> DesktopSessionState:
        self.masking_service.select_target(self.session, target_id)
        return self.current_state()

    def apply_click(self, *, x: int, y: int, positive: bool):
        return self.masking_service.apply_click(self.session, x=x, y=y, positive=positive)

    def apply_brush(self, *, points: list[tuple[int, int]], mode: str, radius: int):
        return self.masking_service.apply_brush(self.session, points=points, mode=mode, radius=radius)

    def update_active_target(
        self,
        *,
        name: str | None = None,
        visible: bool | None = None,
        locked: bool | None = None,
        refine_preset: str | None = None,
        preset_strength: float | None = None,
        motion_strength: float | None = None,
        temporal_stability: float | None = None,
        edge_feather_radius: float | None = None,
    ) -> DesktopSessionState:
        self.masking_service.update_target(
            self.session,
            self.session.active_target_id,
            name=name,
            visible=visible,
            locked=locked,
            refine_preset=refine_preset,
            preset_strength=preset_strength,
            motion_strength=motion_strength,
            temporal_stability=temporal_stability,
            edge_feather_radius=edge_feather_radius,
        )
        return self.current_state()

    def undo_last_click(self) -> DesktopSessionState:
        self.masking_service.undo_last_click(self.session)
        return self.current_state()

    def reset_active_target(self) -> DesktopSessionState:
        self.masking_service.reset_active_target(self.session)
        return self.current_state()

    def save_active_target(self) -> str:
        return self.masking_service.save_current_mask(self.session)

    def set_workflow_step(self, workflow_step: str) -> DesktopSessionState:
        self.session.workflow_step = workflow_step
        return self.current_state()

    def set_stage(self, stage: str) -> DesktopSessionState:
        self.masking_service.set_stage(self.session, stage)
        return self.current_state()

    def set_active_sidebar_tab(self, tab_name: str) -> DesktopSessionState:
        self.session.active_sidebar_tab = tab_name
        return self.current_state()

    def set_selected_masks(self, mask_names: list[str]) -> DesktopSessionState:
        self.session.selected_mask_names = set(mask_names)
        return self.current_state()

    def submit_job(self, job_dir: Path) -> dict:
        if self.inference_service is None or self.export_service is None:
            raise RuntimeError("inference/export services are not configured")

        job_dir = Path(job_dir)
        job_dir.mkdir(parents=True, exist_ok=True)

        selected_masks = sorted(self.session.selected_mask_names)
        if not selected_masks:
            raise ValueError("select at least one mask to export")

        merged_mask_path = self.masking_service.write_merged_mask(self.session, selected_masks)
        selected_mask_presets = {
            mask_name: self.session.saved_mask_presets.get(mask_name, "balanced")
            for mask_name in selected_masks
        }
        selected_mask_controls = self._selected_mask_controls(selected_masks)

        inference_result = self.inference_service.run_job(
            source_video_path=self.draft.video_path,
            mask_path=merged_mask_path,
            job_dir=job_dir,
            template_frame_index=int(self.draft.template_frame_index or 0),
            process_start_frame_index=self.draft.process_start_frame_index,
            process_end_frame_index=self.draft.process_end_frame_index,
            selected_mask_controls=selected_mask_controls,
            selected_mask_presets=selected_mask_presets,
        )
        export_result = self.export_service.export_assets(
            inference_result.foreground_video_path,
            inference_result.alpha_video_path,
            job_dir,
            motion_strength=max(
                (item["motion_strength"] for item in selected_mask_controls.values()),
                default=0.0,
            ),
            temporal_stability=max(
                (item["temporal_stability"] for item in selected_mask_controls.values()),
                default=0.0,
            ),
            edge_feather_radius=max(
                (item["edge_feather_radius"] for item in selected_mask_controls.values()),
                default=0.0,
            ),
        )
        job_id = uuid.uuid4().hex
        self.session.latest_job_id = job_id
        self.session.workflow_step = "review"
        source_clip_path = inference_result.foreground_video_path.parent / "processing_range.mp4"
        self._latest_job_payload = {
            "job_id": job_id,
            "job_dir": str(job_dir),
            "source_video_path": str(source_clip_path if source_clip_path.exists() else self.draft.video_path),
            "foreground_video_path": str(inference_result.foreground_video_path),
            "alpha_video_path": str(inference_result.alpha_video_path),
            "png_zip_path": str(export_result.png_zip_path),
            "prores_path": str(export_result.prores_path) if export_result.prores_path else None,
            "warning_text": export_result.warning_text,
            "selected_mask_presets": selected_mask_presets,
            "selected_mask_controls": selected_mask_controls,
            "process_start_frame_index": self.draft.process_start_frame_index,
            "process_end_frame_index": self.draft.process_end_frame_index,
            "template_frame_index": self.draft.template_frame_index,
        }
        (job_dir / "desktop_job.json").write_text(
            json.dumps(self._latest_job_payload, indent=2),
            encoding="utf-8",
        )
        return self._latest_job_payload

    def latest_job_payload(self) -> dict | None:
        return self._latest_job_payload

    def current_state(self) -> DesktopSessionState:
        active_target = self.session.active_target
        return DesktopSessionState(
            workflow_step=self.session.workflow_step,
            active_sidebar_tab=self.session.active_sidebar_tab,
            process_start_frame_index=self.draft.process_start_frame_index,
            process_end_frame_index=self.draft.process_end_frame_index,
            template_frame_index=self.draft.template_frame_index,
            can_enter_mask=self.draft.template_frame_index is not None,
            can_enter_refine=self.draft.template_frame_index is not None,
            saved_mask_names=sorted(self.session.saved_masks.keys()),
            active_target_id=active_target.target_id,
            active_target_name=active_target.name,
            stage=self.session.stage,
            current_preview_path=self.session.current_preview_path,
            current_mask_path=self.session.current_mask_path,
            selected_mask_names=sorted(self.session.selected_mask_names),
            targets=[
                {
                    "target_id": target.target_id,
                    "name": target.name,
                    "visible": target.visible,
                    "locked": target.locked,
                    "saved_mask_name": target.saved_mask_name,
                    "refine_preset": target.refine_preset,
                }
                for target in self.session.targets.values()
            ],
            latest_job_id=self.session.latest_job_id,
        )

    def _selected_mask_controls(self, selected_masks: list[str]) -> dict[str, dict]:
        controls = {}
        for target in self.session.targets.values():
            if target.saved_mask_name in selected_masks:
                controls[target.saved_mask_name] = {
                    "preset_strength": target.preset_strength,
                    "motion_strength": target.motion_strength,
                    "temporal_stability": target.temporal_stability,
                    "edge_feather_radius": target.edge_feather_radius,
                }
        return controls
