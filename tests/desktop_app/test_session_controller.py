from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from matanyone2.desktop_app.config import DesktopAppConfig
from matanyone2.desktop_app.session_controller import DesktopWorkbenchController
from matanyone2.webapp.services.masking import MaskingService
from matanyone2.webapp.services.video import VideoDraftService


def _create_sample_video(video_path: Path, *, frame_count: int = 8) -> Path:
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
                x0 = max(0, x - 1)
                y0 = max(0, y - 1)
                x1 = min(image.shape[1], x + 2)
                y1 = min(image.shape[0], y + 2)
                mask[y0:y1, x0:x1] = 1
            return mask, np.zeros_like(mask, dtype=np.float32), Image.fromarray(image)

    return MaskingService(runtime_root=runtime_root, controller_factory=lambda: FakeController())


def test_open_video_builds_clip_session(tmp_path: Path):
    config = DesktopAppConfig.for_root(tmp_path)
    runtime_root = tmp_path / "runtime"
    controller = DesktopWorkbenchController(
        config=config,
        video_service=VideoDraftService(
            runtime_root=runtime_root,
            max_video_seconds=config.max_video_seconds,
            max_upload_bytes=config.max_upload_bytes,
        ),
        masking_service=_build_masking_service(runtime_root),
    )
    video_path = _create_sample_video(tmp_path / "sample.mp4")

    state = controller.open_video(video_path)

    assert state.workflow_step == "clip"
    assert state.can_enter_mask is True
    assert state.process_start_frame_index == 0
    assert state.process_end_frame_index == 7
    assert state.template_frame_index == 0


def test_applying_processing_range_resets_saved_masks_and_anchor(tmp_path: Path):
    config = DesktopAppConfig.for_root(tmp_path)
    runtime_root = tmp_path / "runtime"
    controller = DesktopWorkbenchController(
        config=config,
        video_service=VideoDraftService(
            runtime_root=runtime_root,
            max_video_seconds=config.max_video_seconds,
            max_upload_bytes=config.max_upload_bytes,
        ),
        masking_service=_build_masking_service(runtime_root),
    )
    video_path = _create_sample_video(tmp_path / "sample.mp4")
    controller.open_video(video_path)
    controller.apply_click(x=4, y=4, positive=True)
    controller.save_active_target()

    state = controller.apply_processing_range(start_frame_index=2, end_frame_index=5)

    assert state.process_start_frame_index == 2
    assert state.process_end_frame_index == 5
    assert state.template_frame_index is None
    assert state.saved_mask_names == []
    assert state.can_enter_mask is False


def test_anchor_must_fall_inside_processing_range(tmp_path: Path):
    config = DesktopAppConfig.for_root(tmp_path)
    runtime_root = tmp_path / "runtime"
    controller = DesktopWorkbenchController(
        config=config,
        video_service=VideoDraftService(
            runtime_root=runtime_root,
            max_video_seconds=config.max_video_seconds,
            max_upload_bytes=config.max_upload_bytes,
        ),
        masking_service=_build_masking_service(runtime_root),
    )
    video_path = _create_sample_video(tmp_path / "sample.mp4")
    controller.open_video(video_path)
    controller.apply_processing_range(start_frame_index=2, end_frame_index=5)

    state = controller.apply_anchor(frame_index=3)

    assert state.template_frame_index == 3
    assert state.workflow_step == "mask"
    assert state.can_enter_mask is True


def test_ensure_anchor_for_masking_defaults_to_processing_range_start(tmp_path: Path):
    config = DesktopAppConfig.for_root(tmp_path)
    runtime_root = tmp_path / "runtime"
    controller = DesktopWorkbenchController(
        config=config,
        video_service=VideoDraftService(
            runtime_root=runtime_root,
            max_video_seconds=config.max_video_seconds,
            max_upload_bytes=config.max_upload_bytes,
        ),
        masking_service=_build_masking_service(runtime_root),
    )
    video_path = _create_sample_video(tmp_path / "sample.mp4")
    controller.open_video(video_path)
    controller.apply_processing_range(start_frame_index=2, end_frame_index=5)

    state = controller.ensure_anchor_for_masking()

    assert state.template_frame_index == 2
    assert state.workflow_step == "mask"
    assert state.can_enter_mask is True
