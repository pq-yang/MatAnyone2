from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from matanyone2.desktop_app.config import DesktopAppConfig
from matanyone2.desktop_app.session_controller import DesktopWorkbenchController
from matanyone2.webapp.models import ExportResult, InferenceResult
from matanyone2.webapp.services.masking import MaskingService
from matanyone2.webapp.services.video import VideoDraftService


def _create_sample_video(video_path: Path, *, frame_count: int = 6) -> Path:
    writer = cv2.VideoWriter(
        str(video_path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        4.0,
        (16, 12),
    )
    for idx in range(frame_count):
        frame = np.full((12, 16, 3), fill_value=idx * 20, dtype=np.uint8)
        writer.write(frame)
    writer.release()
    return video_path


def _build_masking_service(runtime_root: Path) -> MaskingService:
    class FakeController:
        def first_frame_click(self, image, points, labels, multimask=True):
            mask = np.zeros((image.shape[0], image.shape[1]), dtype=np.uint8)
            for x, y in points.tolist():
                mask[max(0, y - 1):min(image.shape[0], y + 2), max(0, x - 1):min(image.shape[1], x + 2)] = 1
            return mask, np.zeros_like(mask, dtype=np.float32), Image.fromarray(image)

    return MaskingService(runtime_root=runtime_root, controller_factory=lambda: FakeController())


def test_submit_job_enters_review_and_persists_artifact_summary(tmp_path: Path):
    config = DesktopAppConfig.for_root(tmp_path)
    runtime_root = tmp_path / "runtime"

    class FakeInferenceService:
        def run_job(self, **kwargs):
            job_dir = Path(kwargs["job_dir"])
            foreground = job_dir / "foreground.mp4"
            alpha = job_dir / "alpha.mp4"
            foreground.write_bytes(b"foreground")
            alpha.write_bytes(b"alpha")
            return InferenceResult(foreground_video_path=foreground, alpha_video_path=alpha)

    class FakeExportService:
        def export_assets(self, foreground_video_path, alpha_video_path, job_dir, **kwargs):
            rgba_dir = job_dir / "rgba_png"
            rgba_dir.mkdir(parents=True, exist_ok=True)
            png_zip = job_dir / "rgba_png.zip"
            png_zip.write_bytes(b"zip")
            return ExportResult(
                rgba_png_dir=rgba_dir,
                png_zip_path=png_zip,
                preview_foreground_path=None,
                preview_alpha_path=None,
                prores_path=None,
                warning_text=None,
            )

    controller = DesktopWorkbenchController(
        config=config,
        video_service=VideoDraftService(
            runtime_root=runtime_root,
            max_video_seconds=config.max_video_seconds,
            max_upload_bytes=config.max_upload_bytes,
        ),
        masking_service=_build_masking_service(runtime_root),
        inference_service=FakeInferenceService(),
        export_service=FakeExportService(),
    )
    video_path = _create_sample_video(tmp_path / "sample.mp4")
    controller.open_video(video_path)
    controller.apply_click(x=4, y=4, positive=True)
    mask_name = controller.save_active_target()
    controller.set_selected_masks([mask_name])

    payload = controller.submit_job(tmp_path / "job-1")
    state = controller.current_state()

    assert state.workflow_step == "review"
    assert state.latest_job_id == payload["job_id"]
    assert (tmp_path / "job-1" / "desktop_job.json").exists()
    assert payload["png_zip_path"].endswith("rgba_png.zip")


def test_submit_job_reports_progress_stages(tmp_path: Path):
    config = DesktopAppConfig.for_root(tmp_path)
    runtime_root = tmp_path / "runtime"
    progress_events: list[tuple[str, int, bool]] = []

    class FakeInferenceService:
        def run_job(self, **kwargs):
            job_dir = Path(kwargs["job_dir"])
            foreground = job_dir / "foreground.mp4"
            alpha = job_dir / "alpha.mp4"
            foreground.write_bytes(b"foreground")
            alpha.write_bytes(b"alpha")
            return InferenceResult(foreground_video_path=foreground, alpha_video_path=alpha)

    class FakeExportService:
        def export_assets(self, foreground_video_path, alpha_video_path, job_dir, **kwargs):
            rgba_dir = job_dir / "rgba_png"
            rgba_dir.mkdir(parents=True, exist_ok=True)
            png_zip = job_dir / "rgba_png.zip"
            png_zip.write_bytes(b"zip")
            return ExportResult(
                rgba_png_dir=rgba_dir,
                png_zip_path=png_zip,
                preview_foreground_path=None,
                preview_alpha_path=None,
                prores_path=None,
                warning_text=None,
            )

    controller = DesktopWorkbenchController(
        config=config,
        video_service=VideoDraftService(
            runtime_root=runtime_root,
            max_video_seconds=config.max_video_seconds,
            max_upload_bytes=config.max_upload_bytes,
        ),
        masking_service=_build_masking_service(runtime_root),
        inference_service=FakeInferenceService(),
        export_service=FakeExportService(),
    )
    video_path = _create_sample_video(tmp_path / "sample.mp4")
    controller.open_video(video_path)
    controller.apply_click(x=4, y=4, positive=True)
    mask_name = controller.save_active_target()
    controller.set_selected_masks([mask_name])

    controller.submit_job(
        tmp_path / "job-2",
        progress_callback=lambda stage, value, indeterminate: progress_events.append(
            (stage, value, indeterminate)
        ),
    )

    assert progress_events == [
        ("Running MatAnyone2", 35, True),
        ("Exporting foreground and alpha", 80, True),
        ("Packaging outputs", 95, False),
    ]
