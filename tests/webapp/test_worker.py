from pathlib import Path
import time

import pytest

import scripts.run_internal_worker as run_internal_worker
from matanyone2.webapp.models import ExportResult
from matanyone2.webapp.models import JobStatus
from matanyone2.webapp.queue import QueueCoordinator
from matanyone2.webapp.repository import JobRepository
from matanyone2.webapp.config import WebAppSettings
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
        params_json='{"process_start_frame_index": 3, "process_end_frame_index": 9, "selected_mask_controls": {"mask_001": {"motion_strength": 0.6, "temporal_stability": 0.8}}}',
    )

    class FakeInferenceService:
        def run_job(self, *, source_video_path, mask_path, job_dir, template_frame_index, process_start_frame_index, process_end_frame_index):
            assert process_start_frame_index == 3
            assert process_end_frame_index == 9
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
        def export_assets(
            self,
            foreground_video_path,
            alpha_video_path,
            job_dir,
            *,
            motion_strength,
            temporal_stability,
        ):
            assert motion_strength == 0.6
            assert temporal_stability == 0.8
            rgba_dir = Path(job_dir) / "rgba_png"
            rgba_dir.mkdir(parents=True, exist_ok=True)
            zip_path = Path(job_dir) / "rgba_png.zip"
            zip_path.write_bytes(b"zip")
            return ExportResult(
                rgba_png_dir=rgba_dir,
                png_zip_path=zip_path,
                preview_foreground_path=Path(job_dir) / "preview_foreground.mp4",
                preview_alpha_path=Path(job_dir) / "preview_alpha.mp4",
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


def test_run_forever_keeps_polling_after_idle(monkeypatch, tmp_path):
    repo = JobRepository.from_path(tmp_path / "jobs.db")
    worker = WorkerLoop(
        coordinator=QueueCoordinator(repo),
        repository=repo,
        inference_service=object(),
        export_service=object(),
        runtime_root=tmp_path,
    )

    observed_calls = []
    process_results = iter([None, "job-1"])

    def fake_process_next_job():
        observed_calls.append("tick")
        try:
            return next(process_results)
        except StopIteration as exc:
            raise RuntimeError("stop loop") from exc

    sleep_calls = []

    monkeypatch.setattr(worker, "process_next_job", fake_process_next_job)
    monkeypatch.setattr(time, "sleep", sleep_calls.append)

    with pytest.raises(RuntimeError, match="stop loop"):
        worker.run_forever(poll_interval_seconds=0.25)

    assert sleep_calls == [0.25]
    assert observed_calls == ["tick", "tick", "tick"]


def test_run_internal_worker_main_uses_run_forever(monkeypatch, tmp_path):
    settings = WebAppSettings(
        runtime_root=tmp_path / "runtime",
        database_path=tmp_path / "runtime" / "jobs.db",
    )
    observed = {}
    fake_repository = object()

    class FakeWorkerLoop:
        def __init__(self, coordinator, *, repository, inference_service, export_service, runtime_root):
            observed["coordinator"] = coordinator
            observed["repository"] = repository
            observed["inference_service"] = inference_service
            observed["export_service"] = export_service
            observed["runtime_root"] = runtime_root

        def recover(self):
            observed["recovered"] = True

        def run_forever(self, poll_interval_seconds=1.0):
            observed["poll_interval_seconds"] = poll_interval_seconds

    class FakeJobRepository:
        @staticmethod
        def from_path(path):
            observed["database_path"] = path
            return fake_repository

    monkeypatch.setattr(run_internal_worker, "WebAppSettings", lambda: settings)
    monkeypatch.setattr(run_internal_worker, "JobRepository", FakeJobRepository)
    monkeypatch.setattr(run_internal_worker, "QueueCoordinator", lambda repo: ("queue", repo))
    monkeypatch.setattr(run_internal_worker, "InferenceService", lambda: "inference")
    monkeypatch.setattr(
        run_internal_worker,
        "ExportService",
        lambda enable_prores: ("export", enable_prores),
    )
    monkeypatch.setattr(run_internal_worker, "WorkerLoop", FakeWorkerLoop)

    run_internal_worker.main()

    assert observed["database_path"] == settings.database_path
    assert observed["repository"] is fake_repository
    assert observed["recovered"] is True
    assert observed["poll_interval_seconds"] == 1.0
