from pathlib import Path

from matanyone2.webapp.models import ExportResult
from matanyone2.webapp.models import JobStatus
from matanyone2.webapp.queue import QueueCoordinator
from matanyone2.webapp.repository import JobRepository
from matanyone2.webapp.worker import WorkerLoop


def test_recover_running_jobs_marks_them_interrupted(tmp_path):
    repo = JobRepository.from_path(tmp_path / "jobs.db")
    job = repo.create_job(
        source_video_path="a.mp4",
        template_frame_index=0,
        mask_path="a.png",
        params_json="{}",
    )
    repo.update_status(job.job_id, JobStatus.RUNNING)

    coordinator = QueueCoordinator(repo)
    coordinator.recover_interrupted_jobs()

    assert repo.get_job(job.job_id).status is JobStatus.INTERRUPTED


def test_process_next_job_completes_with_warning_when_export_warns(tmp_path):
    repo = JobRepository.from_path(tmp_path / "jobs.db")
    job = repo.create_job(
        source_video_path="a.mp4",
        template_frame_index=0,
        mask_path="a.png",
        params_json="{}",
    )

    class FakeInferenceService:
        def run_job(self, *, source_video_path, mask_path, job_dir, template_frame_index):
            foreground = Path(job_dir) / "foreground.mp4"
            alpha = Path(job_dir) / "alpha.mp4"
            foreground.write_bytes(b"fg")
            alpha.write_bytes(b"a")
            return type(
                "InferenceResultLike",
                (),
                {
                    "foreground_video_path": foreground,
                    "alpha_video_path": alpha,
                },
            )()

    class FakeExportService:
        def export_assets(self, foreground_video_path, alpha_video_path, job_dir):
            rgba_dir = Path(job_dir) / "rgba_png"
            rgba_dir.mkdir(parents=True, exist_ok=True)
            zip_path = Path(job_dir) / "rgba_png.zip"
            zip_path.write_bytes(b"zip")
            return ExportResult(
                rgba_png_dir=rgba_dir,
                png_zip_path=zip_path,
                prores_path=None,
                warning_text="ffmpeg failed",
            )

    worker = WorkerLoop(
        coordinator=QueueCoordinator(repo),
        repository=repo,
        inference_service=FakeInferenceService(),
        export_service=FakeExportService(),
        runtime_root=tmp_path,
    )

    processed_job_id = worker.process_next_job()
    updated_job = repo.get_job(job.job_id)

    assert processed_job_id == job.job_id
    assert updated_job.status is JobStatus.COMPLETED_WITH_WARNING
    assert updated_job.warning_text == "ffmpeg failed"
