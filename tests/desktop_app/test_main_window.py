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


def _state_for_step(step: str, *, sidebar_tab: str = "targets") -> DesktopSessionState:
    state = _state()
    state.workflow_step = step
    state.active_sidebar_tab = sidebar_tab
    return state


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
