from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from matanyone2.desktop_app.config import DesktopAppConfig
from matanyone2.desktop_app.main_window import DesktopWorkbenchWindow
from matanyone2.desktop_app.session_controller import DesktopSessionState, DesktopWorkbenchController
from matanyone2.webapp.services.masking import MaskingService
from matanyone2.webapp.services.video import VideoDraftService


def _state() -> DesktopSessionState:
    return DesktopSessionState(
        workflow_step="clip",
        active_sidebar_tab="targets",
        process_start_frame_index=0,
        process_end_frame_index=99,
        template_frame_index=12,
        can_enter_mask=True,
        can_enter_refine=True,
        saved_mask_names=[],
        active_target_id="target-001",
        active_target_name="Target 1",
        stage="coarse",
        current_preview_path=None,
        current_mask_path=None,
        selected_mask_names=[],
        targets=[],
    )


def _state_for_step(step: str, *, sidebar_tab: str = "targets") -> DesktopSessionState:
    state = _state()
    state.workflow_step = step
    state.active_sidebar_tab = sidebar_tab
    return state


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


def _build_controller(tmp_path: Path) -> DesktopWorkbenchController:
    config = DesktopAppConfig.for_root(tmp_path)
    runtime_root = tmp_path / "runtime"
    return DesktopWorkbenchController(
        config=config,
        video_service=VideoDraftService(
            runtime_root=runtime_root,
            max_video_seconds=config.max_video_seconds,
            max_upload_bytes=config.max_upload_bytes,
        ),
        masking_service=_build_masking_service(runtime_root),
    )


def test_main_window_uses_single_monitor_workspace(qapp, tmp_path: Path):
    window = DesktopWorkbenchWindow(
        config=DesktopAppConfig.for_root(tmp_path),
        initial_state=_state(),
    )

    assert window.windowTitle() == "MatAnyone2 Desktop Workbench"
    assert window.stepper.count() == 4
    assert [window.stepper.tabText(index) for index in range(window.stepper.count())] == [
        "Clip",
        "Mask",
        "Refine",
        "Review",
    ]
    assert window.inspector_tabs.count() == 3
    assert [window.inspector_tabs.tabText(index) for index in range(window.inspector_tabs.count())] == [
        "Targets",
        "Refine",
        "Export",
    ]


def test_main_window_exposes_horizontal_timeline_actions(qapp, tmp_path: Path):
    window = DesktopWorkbenchWindow(
        config=DesktopAppConfig.for_root(tmp_path),
        initial_state=_state(),
    )

    buttons = [
        window.mark_in_button.text(),
        window.mark_out_button.text(),
        window.clear_range_button.text(),
        window.play_button.text(),
    ]

    assert buttons == ["Mark In", "Mark Out", "Clear", "Play"]
    assert window.timeline_actions_layout.count() >= 7


def test_main_window_exposes_explicit_subject_selection_toolbar(qapp, tmp_path: Path):
    window = DesktopWorkbenchWindow(
        config=DesktopAppConfig.for_root(tmp_path),
        initial_state=_state(),
    )

    buttons = [
        window.select_subject_button.text(),
        window.exclude_button.text(),
        window.brush_add_button.text(),
        window.brush_remove_button.text(),
        window.brush_feather_button.text(),
    ]

    assert buttons == [
        "Select Subject",
        "Exclude",
        "Brush Add",
        "Brush Remove",
        "Brush Feather",
    ]
    assert window.select_subject_button.isChecked() is True


def test_main_window_prefers_refine_tab_during_refine_step(qapp, tmp_path: Path):
    window = DesktopWorkbenchWindow(
        config=DesktopAppConfig.for_root(tmp_path),
        initial_state=_state_for_step("refine", sidebar_tab="targets"),
    )

    assert window.inspector_tabs.tabText(window.inspector_tabs.currentIndex()) == "Refine"


def test_main_window_prefers_export_tab_during_review_step(qapp, tmp_path: Path):
    window = DesktopWorkbenchWindow(
        config=DesktopAppConfig.for_root(tmp_path),
        initial_state=_state_for_step("review", sidebar_tab="targets"),
    )

    assert window.inspector_tabs.tabText(window.inspector_tabs.currentIndex()) == "Export"


def test_toolbar_updates_hint_when_switching_tools(qapp, tmp_path: Path):
    window = DesktopWorkbenchWindow(
        config=DesktopAppConfig.for_root(tmp_path),
        initial_state=_state_for_step("mask"),
    )

    window._set_interaction_mode("negative")

    assert window.interaction_mode.currentText() == "Negative"
    assert "exclude" in window.interaction_hint_label.text().lower()


def test_clip_hint_defaults_to_whole_clip_when_range_not_trimmed(qapp, tmp_path: Path):
    window = DesktopWorkbenchWindow(
        config=DesktopAppConfig.for_root(tmp_path),
        initial_state=_state_for_step("clip"),
    )
    window.source_timeline.setMinimum(0)
    window.source_timeline.setMaximum(99)
    window.state.process_start_frame_index = 0
    window.state.process_end_frame_index = 99
    window._sync_interaction_hint()

    assert "whole clip" in window.interaction_hint_label.text().lower()
    assert "mark in/out" in window.interaction_hint_label.text().lower()


def test_clip_hint_switches_when_range_is_trimmed(qapp, tmp_path: Path):
    window = DesktopWorkbenchWindow(
        config=DesktopAppConfig.for_root(tmp_path),
        initial_state=_state_for_step("clip"),
    )
    window.source_timeline.setMinimum(0)
    window.source_timeline.setMaximum(99)
    window.state.process_start_frame_index = 12
    window.state.process_end_frame_index = 48
    window._sync_interaction_hint()

    assert "trimmed range" in window.interaction_hint_label.text().lower()


def test_select_subject_from_clip_uses_default_anchor(qapp, tmp_path: Path):
    controller = _build_controller(tmp_path)
    config = DesktopAppConfig.for_root(tmp_path)
    video_path = _create_sample_video(tmp_path / "sample.mp4")
    window = DesktopWorkbenchWindow(config=config, controller=controller)
    window.load_video_file(video_path)
    window.state = controller.apply_processing_range(start_frame_index=2, end_frame_index=5)
    window.current_playhead_frame = 4
    window._sync_state_to_ui()

    window.select_subject_button.click()

    assert window.state.workflow_step == "mask"
    assert window.state.template_frame_index == 2
    assert window.current_playhead_frame == 2


def test_mask_hint_guides_user_to_overlay_mask_and_save(qapp, tmp_path: Path):
    window = DesktopWorkbenchWindow(
        config=DesktopAppConfig.for_root(tmp_path),
        initial_state=_state_for_step("mask"),
    )
    window.state.current_mask_path = tmp_path / "mask.png"
    window.state.current_preview_path = tmp_path / "preview.png"
    window.current_view_mode = "overlay"

    window._sync_interaction_hint()

    hint = window.interaction_hint_label.text().lower()
    assert "overlay" in hint
    assert "mask" in hint
    assert "save target" in hint
