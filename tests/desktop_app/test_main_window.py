from pathlib import Path

from matanyone2.desktop_app.config import DesktopAppConfig
from matanyone2.desktop_app.main_window import DesktopWorkbenchWindow
from matanyone2.desktop_app.session_controller import DesktopSessionState


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
