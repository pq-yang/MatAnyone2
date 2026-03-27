from pathlib import Path
import time
import json

from matanyone2.webapp.models import JobStatus
from matanyone2.webapp.queue import QueueCoordinator


class WorkerLoop:
    def __init__(
        self,
        coordinator: QueueCoordinator,
        *,
        repository,
        inference_service,
        export_service,
        runtime_root: Path,
    ):
        self.coordinator = coordinator
        self.repository = repository
        self.inference_service = inference_service
        self.export_service = export_service
        self.runtime_root = Path(runtime_root)

    def recover(self) -> None:
        self.coordinator.recover_interrupted_jobs()

    def run_forever(self, poll_interval_seconds: float = 1.0) -> None:
        while True:
            processed_job_id = self.process_next_job()
            if processed_job_id is None:
                time.sleep(poll_interval_seconds)

    def process_next_job(self) -> str | None:
        job_id = self.coordinator.next_job_id()
        if job_id is None:
            return None

        job = self.repository.get_job(job_id)
        job_dir = self.runtime_root / "jobs" / job.job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        try:
            self.repository.update_status(job.job_id, JobStatus.PREPARING)
            self.repository.update_status(job.job_id, JobStatus.RUNNING)
            job_params = json.loads(job.params_json or "{}")
            selected_mask_controls = job_params.get("selected_mask_controls", {})
            selected_mask_presets = job_params.get("selected_mask_presets", {})
            motion_strength = max(
                (
                    float(control.get("motion_strength", 0.0))
                    for control in selected_mask_controls.values()
                ),
                default=0.0,
            )
            temporal_stability = max(
                (
                    float(control.get("temporal_stability", 0.0))
                    for control in selected_mask_controls.values()
                ),
                default=0.0,
            )
            edge_feather_radius = max(
                (
                    float(control.get("edge_feather_radius", 0.0))
                    for control in selected_mask_controls.values()
                ),
                default=0.0,
            )
            inference_result = self.inference_service.run_job(
                source_video_path=Path(job.source_video_path),
                mask_path=Path(job.mask_path),
                job_dir=job_dir,
                template_frame_index=job.template_frame_index,
                process_start_frame_index=int(job_params.get("process_start_frame_index", 0)),
                process_end_frame_index=job_params.get("process_end_frame_index"),
                selected_mask_controls=selected_mask_controls,
                selected_mask_presets=selected_mask_presets,
            )
            self.repository.update_status(job.job_id, JobStatus.EXPORTING)
            export_result = self.export_service.export_assets(
                inference_result.foreground_video_path,
                inference_result.alpha_video_path,
                job_dir,
                motion_strength=motion_strength,
                temporal_stability=temporal_stability,
                edge_feather_radius=edge_feather_radius,
            )
        except Exception as exc:
            self.repository.update_status(
                job.job_id,
                JobStatus.FAILED,
                error_text=str(exc),
            )
            return job.job_id

        final_status = (
            JobStatus.COMPLETED_WITH_WARNING
            if export_result.warning_text
            else JobStatus.COMPLETED
        )
        self.repository.update_status(
            job.job_id,
            final_status,
            warning_text=export_result.warning_text,
        )
        return job.job_id
