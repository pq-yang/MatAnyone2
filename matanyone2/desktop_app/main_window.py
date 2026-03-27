from pathlib import Path

import cv2
import numpy as np
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QTabBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from matanyone2.desktop_app.config import DesktopAppConfig
from matanyone2.desktop_app.jobs import DesktopJobHandle
from matanyone2.desktop_app.media import VideoFrameStore
from matanyone2.desktop_app.session_controller import DesktopSessionState, DesktopWorkbenchController
from matanyone2.desktop_app.widgets import MonitorPane, TimelineDock


class DesktopWorkbenchWindow(QMainWindow):
    def __init__(
        self,
        *,
        config: DesktopAppConfig,
        initial_state: DesktopSessionState | None = None,
        controller: DesktopWorkbenchController | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.config = config
        self.controller = controller
        self.state = initial_state or self._initial_placeholder_state()
        self.setWindowTitle(config.window_title)
        self.resize(1680, 1020)

        self.source_store: VideoFrameStore | None = None
        self.review_source_store: VideoFrameStore | None = None
        self.review_foreground_store: VideoFrameStore | None = None
        self.review_alpha_store: VideoFrameStore | None = None
        self.current_view_mode = "source"
        self.current_playhead_frame = 0
        self.pending_in_frame = 0
        self.pending_out_frame = 0
        self.current_interaction_mode = "positive"
        self.current_job_handle: DesktopJobHandle | None = None
        self.playback_timer = QTimer(self)
        self.playback_timer.timeout.connect(self._advance_playback)

        self._build_ui()
        self._wire_events()
        self._sync_state_to_ui()

    def _initial_placeholder_state(self) -> DesktopSessionState:
        if self.controller is not None:
            try:
                return self.controller.current_state()
            except RuntimeError:
                pass
        return DesktopSessionState(
            workflow_step="clip",
            active_sidebar_tab="targets",
            process_start_frame_index=0,
            process_end_frame_index=0,
            template_frame_index=None,
            can_enter_mask=False,
            can_enter_refine=False,
            saved_mask_names=[],
            active_target_id="target-000",
            active_target_name="No video loaded",
            stage="coarse",
            current_preview_path=None,
            current_mask_path=None,
            selected_mask_names=[],
            targets=[],
            latest_job_id=None,
        )

    def _build_ui(self) -> None:
        root = QWidget(self)
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(12)

        self.inspector_tabs = QTabWidget()
        self.inspector_tabs.setObjectName("inspectorTabs")
        self.inspector_tabs.setMinimumWidth(340)
        self.inspector_tabs.addTab(self._build_targets_tab(), "Targets")
        self.inspector_tabs.addTab(self._build_refine_tab(), "Refine")
        self.inspector_tabs.addTab(self._build_export_tab(), "Export")
        outer.addWidget(self.inspector_tabs, 0)

        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(10)

        topbar = QHBoxLayout()
        self.open_video_button = QPushButton("Open Video")
        self.back_button = QPushButton("Back")
        self.next_button = QPushButton("Next")
        self.session_status_label = QLabel("No session")
        topbar.addWidget(self.open_video_button)
        topbar.addWidget(self.back_button)
        topbar.addWidget(self.next_button)
        topbar.addWidget(self.session_status_label, 1)
        center_layout.addLayout(topbar)

        self.stepper = QTabBar()
        self.stepper.setObjectName("workflowStepper")
        for label in ("Clip", "Mask", "Refine", "Review"):
            self.stepper.addTab(label)
        center_layout.addWidget(self.stepper)

        view_row = QHBoxLayout()
        self.view_buttons = {}
        for key, label in (
            ("source", "Source"),
            ("overlay", "Overlay"),
            ("mask", "Mask"),
            ("alpha", "Alpha"),
            ("foreground", "Foreground"),
        ):
            button = QPushButton(label)
            button.setCheckable(True)
            if key == "source":
                button.setChecked(True)
            self.view_buttons[key] = button
            view_row.addWidget(button)
        view_row.addStretch(1)
        center_layout.addLayout(view_row)

        tool_row = QHBoxLayout()
        self.tool_group_label = QLabel("Mask Tools")
        self.select_subject_button = QPushButton("Select Subject")
        self.exclude_button = QPushButton("Exclude")
        self.brush_add_button = QPushButton("Brush Add")
        self.brush_remove_button = QPushButton("Brush Remove")
        self.brush_feather_button = QPushButton("Brush Feather")
        self.interaction_toolbar_buttons = {
            "positive": self.select_subject_button,
            "negative": self.exclude_button,
            "brush_add": self.brush_add_button,
            "brush_remove": self.brush_remove_button,
            "brush_feather": self.brush_feather_button,
        }
        tool_row.addWidget(self.tool_group_label)
        tool_row.addSpacing(8)
        for button in self.interaction_toolbar_buttons.values():
            button.setCheckable(True)
            tool_row.addWidget(button)
        self.interaction_hint_label = QLabel("Select Subject, then click the monitor to tag the active person or object.")
        tool_row.addSpacing(8)
        tool_row.addWidget(self.interaction_hint_label, 1)
        center_layout.addLayout(tool_row)

        self.monitor = MonitorPane()
        center_layout.addWidget(self.monitor, 1)

        self.timeline_dock = TimelineDock()
        center_layout.addWidget(self.timeline_dock, 0)
        outer.addWidget(center, 1)

        self.mark_in_button = self.timeline_dock.mark_in_button
        self.mark_out_button = self.timeline_dock.mark_out_button
        self.clear_range_button = self.timeline_dock.clear_range_button
        self.play_button = self.timeline_dock.play_button
        self.timeline_actions_layout = self.timeline_dock.timeline_actions_layout
        self.source_timeline = self.timeline_dock.source_timeline
        self.anchor_timeline = self.timeline_dock.anchor_timeline
        self.current_time_label = self.timeline_dock.current_time_label
        self.in_label = self.timeline_dock.in_label
        self.out_label = self.timeline_dock.out_label
        self.duration_label = self.timeline_dock.duration_label

    def _build_targets_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self.target_list = QListWidget()
        self.new_target_button = QPushButton("New Target")
        self.target_name_input = QLineEdit()
        self.apply_name_button = QPushButton("Apply Name")
        self.visible_checkbox = QCheckBox("Visible")
        self.visible_checkbox.setChecked(True)
        self.locked_checkbox = QCheckBox("Locked")
        controls = QHBoxLayout()
        controls.addWidget(self.new_target_button)
        controls.addStretch(1)

        layout.addLayout(controls)
        layout.addWidget(self.target_list)
        layout.addWidget(QLabel("Target Name"))
        layout.addWidget(self.target_name_input)
        row = QHBoxLayout()
        row.addWidget(self.apply_name_button)
        row.addWidget(self.visible_checkbox)
        row.addWidget(self.locked_checkbox)
        layout.addLayout(row)
        layout.addStretch(1)
        return tab

    def _build_refine_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        mode_group = QGroupBox("Interaction")
        mode_layout = QVBoxLayout(mode_group)
        self.interaction_mode = QComboBox()
        self.interaction_mode.addItems(
            ["Positive", "Negative", "Brush Add", "Brush Remove", "Brush Feather"]
        )
        mode_layout.addWidget(self.interaction_mode)

        preset_group = QGroupBox("Refine")
        preset_layout = QFormLayout(preset_group)
        self.refine_preset_combo = QComboBox()
        self.refine_preset_combo.addItems(["Balanced", "Hair", "Edge", "Motion"])
        self.preset_strength_slider = self._slider(0, 100, 50)
        self.motion_softness_slider = self._slider(0, 100, 35)
        self.temporal_stability_slider = self._slider(0, 100, 0)
        self.edge_feather_slider = self._slider(0, 240, 0)
        self.brush_size_slider = self._slider(1, 64, 14)
        self.overlay_opacity_slider = self._slider(0, 100, 100)
        preset_layout.addRow("Preset", self.refine_preset_combo)
        preset_layout.addRow("Preset strength", self.preset_strength_slider)
        preset_layout.addRow("Motion softness", self.motion_softness_slider)
        preset_layout.addRow("Temporal stability", self.temporal_stability_slider)
        preset_layout.addRow("Edge feather", self.edge_feather_slider)
        preset_layout.addRow("Brush size", self.brush_size_slider)
        preset_layout.addRow("Overlay opacity", self.overlay_opacity_slider)

        action_row = QHBoxLayout()
        self.undo_click_button = QPushButton("Undo")
        self.reset_target_button = QPushButton("Reset Target")
        action_row.addWidget(self.undo_click_button)
        action_row.addWidget(self.reset_target_button)

        layout.addWidget(mode_group)
        layout.addWidget(preset_group)
        layout.addLayout(action_row)
        layout.addStretch(1)
        return tab

    def _build_export_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self.saved_masks_list = QListWidget()
        self.save_target_button = QPushButton("Save Target")
        self.submit_job_button = QPushButton("Run MatAnyone2")
        self.open_output_button = QPushButton("Open Output Folder")
        self.open_output_button.setEnabled(False)
        self.export_status_label = QLabel("No job yet")

        layout.addWidget(QLabel("Saved Masks"))
        layout.addWidget(self.saved_masks_list)
        layout.addWidget(self.save_target_button)
        layout.addWidget(self.submit_job_button)
        layout.addWidget(self.export_status_label)
        layout.addWidget(self.open_output_button)
        layout.addStretch(1)
        return tab

    def _wire_events(self) -> None:
        self.open_video_button.clicked.connect(self._open_video_dialog)
        self.back_button.clicked.connect(self._go_back)
        self.next_button.clicked.connect(self._go_next)
        self.stepper.currentChanged.connect(self._on_stepper_changed)
        self.inspector_tabs.currentChanged.connect(self._on_inspector_changed)

        self.source_timeline.valueChanged.connect(self._on_source_scrub)
        self.anchor_timeline.valueChanged.connect(self._on_anchor_scrub)
        self.anchor_timeline.sliderReleased.connect(self._apply_anchor_from_slider)
        self.mark_in_button.clicked.connect(self._mark_in)
        self.mark_out_button.clicked.connect(self._mark_out)
        self.clear_range_button.clicked.connect(self._clear_range)
        self.play_button.clicked.connect(self._toggle_playback)

        self.monitor.surface.clicked.connect(self._on_monitor_clicked)
        self.monitor.surface.strokeFinished.connect(self._on_monitor_stroke)

        self.new_target_button.clicked.connect(self._new_target)
        self.target_list.currentRowChanged.connect(self._select_target_from_list)
        self.apply_name_button.clicked.connect(self._apply_target_name)
        self.visible_checkbox.toggled.connect(self._toggle_visible)
        self.locked_checkbox.toggled.connect(self._toggle_locked)

        self.interaction_mode.currentIndexChanged.connect(self._on_interaction_mode_changed)
        self.refine_preset_combo.currentIndexChanged.connect(self._on_refine_controls_changed)
        self.preset_strength_slider.valueChanged.connect(self._on_refine_controls_changed)
        self.motion_softness_slider.valueChanged.connect(self._on_refine_controls_changed)
        self.temporal_stability_slider.valueChanged.connect(self._on_refine_controls_changed)
        self.edge_feather_slider.valueChanged.connect(self._on_refine_controls_changed)
        self.undo_click_button.clicked.connect(self._undo_click)
        self.reset_target_button.clicked.connect(self._reset_target)

        self.save_target_button.clicked.connect(self._save_target)
        self.saved_masks_list.itemChanged.connect(self._on_saved_mask_selection_changed)
        self.submit_job_button.clicked.connect(self._submit_job)
        self.open_output_button.clicked.connect(self._open_output_folder)

        for key, button in self.view_buttons.items():
            button.clicked.connect(lambda _checked=False, mode=key: self._set_view_mode(mode))
        for mode, button in self.interaction_toolbar_buttons.items():
            button.clicked.connect(lambda _checked=False, value=mode: self._set_interaction_mode(value))

    def load_video_file(self, video_path: str | Path) -> None:
        if self.controller is None:
            return
        state = self.controller.open_video(video_path)
        self.state = state
        self._close_video_stores()
        self.source_store = VideoFrameStore(video_path)
        self.review_source_store = None
        self.review_foreground_store = None
        self.review_alpha_store = None
        self.current_playhead_frame = int(state.template_frame_index or 0)
        self.pending_in_frame = state.process_start_frame_index
        self.pending_out_frame = state.process_end_frame_index
        self.current_view_mode = "source"
        self._sync_state_to_ui()
        self._render_monitor()

    def _open_video_dialog(self) -> None:
        video_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Video",
            "",
            "Video Files (*.mp4 *.mov *.m4v *.avi *.mkv)",
        )
        if video_path:
            self.load_video_file(video_path)

    def _sync_state_to_ui(self) -> None:
        if self.state is None:
            return
        step_index = {"clip": 0, "mask": 1, "refine": 2, "review": 3}.get(self.state.workflow_step, 0)
        self.stepper.setCurrentIndex(step_index)
        preferred_tab = self._preferred_sidebar_tab()
        self.inspector_tabs.setCurrentIndex({"targets": 0, "refine": 1, "export": 2}.get(preferred_tab, 0))
        self.session_status_label.setText(f"Step: {self.state.workflow_step.title()} | Target: {self.state.active_target_name}")
        self.source_timeline.setMinimum(0)
        self.source_timeline.setMaximum(max(self.state.process_end_frame_index, 0))
        self.source_timeline.setValue(self.current_playhead_frame)
        self.anchor_timeline.setMinimum(self.state.process_start_frame_index)
        self.anchor_timeline.setMaximum(self.state.process_end_frame_index)
        self.anchor_timeline.setEnabled(self.state.process_end_frame_index >= self.state.process_start_frame_index)
        self.anchor_timeline.setValue(
            int(self.state.template_frame_index if self.state.template_frame_index is not None else self.state.process_start_frame_index)
        )
        self._sync_target_list()
        self._sync_saved_masks_list()
        self._sync_refine_controls()
        self._sync_action_states()
        self._update_timeline_labels()
        self._sync_interaction_hint()

    def _sync_target_list(self) -> None:
        self.target_list.blockSignals(True)
        self.target_list.clear()
        for target in self.state.targets:
            item = QListWidgetItem(f"{target['name']}  [{target['refine_preset']}]")
            item.setData(Qt.UserRole, target["target_id"])
            if target["saved_mask_name"]:
                item.setToolTip(target["saved_mask_name"])
            self.target_list.addItem(item)
            if target["target_id"] == self.state.active_target_id:
                self.target_list.setCurrentItem(item)
                self.target_name_input.setText(target["name"])
                self.visible_checkbox.setChecked(target["visible"])
                self.locked_checkbox.setChecked(target["locked"])
        self.target_list.blockSignals(False)

    def _sync_saved_masks_list(self) -> None:
        self.saved_masks_list.blockSignals(True)
        self.saved_masks_list.clear()
        for mask_name in self.state.saved_mask_names:
            item = QListWidgetItem(mask_name)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if mask_name in self.state.selected_mask_names else Qt.Unchecked)
            self.saved_masks_list.addItem(item)
        self.saved_masks_list.blockSignals(False)

    def _sync_refine_controls(self) -> None:
        active = next((target for target in self.state.targets if target["target_id"] == self.state.active_target_id), None)
        preset_text = (active or {}).get("refine_preset", "balanced").title()
        index = max(0, self.refine_preset_combo.findText(preset_text))
        self.refine_preset_combo.blockSignals(True)
        self.refine_preset_combo.setCurrentIndex(index)
        self.refine_preset_combo.blockSignals(False)
        interaction_index = {
            "positive": 0,
            "negative": 1,
            "brush_add": 2,
            "brush_remove": 3,
            "brush_feather": 4,
        }.get(self.current_interaction_mode, 0)
        self.interaction_mode.blockSignals(True)
        self.interaction_mode.setCurrentIndex(interaction_index)
        self.interaction_mode.blockSignals(False)
        self._sync_interaction_toolbar()

    def _sync_action_states(self) -> None:
        can_edit = self.controller is not None and self.state.can_enter_mask and self.state.workflow_step != "review"
        self.save_target_button.setEnabled(can_edit and self.state.current_mask_path is not None)
        self.submit_job_button.setEnabled(bool(self.state.selected_mask_names))
        self.view_buttons["alpha"].setEnabled(self.state.workflow_step == "review")
        self.view_buttons["foreground"].setEnabled(self.state.workflow_step == "review")
        self.view_buttons["mask"].setEnabled(self.state.workflow_step in {"mask", "refine"} and self.state.current_mask_path is not None)
        self.view_buttons["overlay"].setEnabled(
            (self.state.workflow_step in {"mask", "refine"} and self.state.current_preview_path is not None)
            or self.state.workflow_step == "review"
        )
        for button in self.interaction_toolbar_buttons.values():
            button.setEnabled(can_edit)
        self.interaction_mode.setEnabled(can_edit)
        self.interaction_hint_label.setVisible(can_edit)

    def _preferred_sidebar_tab(self) -> str:
        if self.state.workflow_step == "review":
            return "export"
        if self.state.workflow_step == "refine":
            return "refine"
        return self.state.active_sidebar_tab

    def _is_full_clip_range(self) -> bool:
        return (
            self.source_timeline.minimum() == self.state.process_start_frame_index
            and self.source_timeline.maximum() == self.state.process_end_frame_index
        )

    def _update_timeline_labels(self) -> None:
        fps = self._active_fps()
        self.current_time_label.setText(self._format_timecode(self.current_playhead_frame, fps))
        self.in_label.setText(f"In {self._format_timecode(self.state.process_start_frame_index, fps)}")
        self.out_label.setText(f"Out {self._format_timecode(self.state.process_end_frame_index, fps)}")
        duration = max(0, self.state.process_end_frame_index - self.state.process_start_frame_index + 1)
        self.duration_label.setText(f"Duration {duration}f")

    def _active_fps(self) -> float:
        if self.state.workflow_step == "review" and self.review_source_store is not None:
            return self.review_source_store.fps
        if self.source_store is not None:
            return self.source_store.fps
        return 24.0

    def _set_view_mode(self, view_mode: str) -> None:
        self.current_view_mode = view_mode
        for key, button in self.view_buttons.items():
            button.setChecked(key == view_mode)
        self._render_monitor()

    def _render_monitor(self) -> None:
        frame = None
        if self.state.workflow_step == "review":
            frame = self._review_frame_for_view_mode()
        elif self.current_view_mode == "mask" and self.state.current_mask_path is not None:
            frame = cv2.imread(str(self.state.current_mask_path), cv2.IMREAD_GRAYSCALE)
        elif self.current_view_mode == "overlay" and self.state.current_preview_path is not None:
            preview = cv2.imread(str(self.state.current_preview_path), cv2.IMREAD_COLOR)
            if preview is not None:
                frame = cv2.cvtColor(preview, cv2.COLOR_BGR2RGB)
        if frame is None:
            frame = self._source_frame()
        self.monitor.mode_label.setText(self.current_view_mode.title())
        self.monitor.surface.set_numpy_image(frame)

    def _source_frame(self) -> np.ndarray | None:
        if self.source_store is None:
            return None
        return self.source_store.read_frame(self.current_playhead_frame)

    def _review_frame_for_view_mode(self) -> np.ndarray | None:
        if self.current_view_mode == "foreground" and self.review_foreground_store is not None:
            return self.review_foreground_store.read_frame(self.current_playhead_frame)
        if self.current_view_mode == "alpha" and self.review_alpha_store is not None:
            return self.review_alpha_store.read_frame(self.current_playhead_frame)
        if self.current_view_mode == "overlay":
            return self._compose_overlay_frame()
        if self.review_source_store is not None:
            return self.review_source_store.read_frame(self.current_playhead_frame)
        return None

    def _compose_overlay_frame(self) -> np.ndarray | None:
        if self.review_source_store is None or self.review_foreground_store is None or self.review_alpha_store is None:
            return None
        source = self.review_source_store.read_frame(self.current_playhead_frame).astype(np.float32)
        foreground = self.review_foreground_store.read_frame(self.current_playhead_frame).astype(np.float32)
        alpha_rgb = self.review_alpha_store.read_frame(self.current_playhead_frame)
        alpha_gray = cv2.cvtColor(alpha_rgb, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
        alpha = np.repeat(alpha_gray[:, :, None], 3, axis=2)
        composite = (foreground * alpha) + (source * (1.0 - alpha))
        return np.clip(composite, 0, 255).astype(np.uint8)

    def _on_source_scrub(self, value: int) -> None:
        self.current_playhead_frame = value
        if self.state.workflow_step != "review":
            self._set_view_mode("source")
        self._update_timeline_labels()
        self._render_monitor()

    def _on_anchor_scrub(self, value: int) -> None:
        if not self.anchor_timeline.isEnabled():
            return
        self.current_playhead_frame = value
        self._set_view_mode("source")
        self._update_timeline_labels()
        self._render_monitor()

    def _apply_anchor_from_slider(self) -> None:
        if self.controller is None:
            return
        self.state = self.controller.apply_anchor(frame_index=self.anchor_timeline.value())
        self.current_playhead_frame = int(self.state.template_frame_index or self.current_playhead_frame)
        self._sync_state_to_ui()
        self._render_monitor()

    def _mark_in(self) -> None:
        self.pending_in_frame = self.current_playhead_frame
        self._maybe_apply_pending_range()

    def _mark_out(self) -> None:
        self.pending_out_frame = self.current_playhead_frame
        self._maybe_apply_pending_range()

    def _maybe_apply_pending_range(self) -> None:
        if self.controller is None:
            return
        start = min(self.pending_in_frame, self.pending_out_frame)
        end = max(self.pending_in_frame, self.pending_out_frame)
        self.state = self.controller.apply_processing_range(start_frame_index=start, end_frame_index=end)
        self.current_playhead_frame = start
        self._set_view_mode("source")
        self._sync_state_to_ui()
        self._render_monitor()

    def _clear_range(self) -> None:
        if self.controller is None or self.source_store is None:
            return
        self.pending_in_frame = 0
        self.pending_out_frame = self.source_store.frame_count - 1
        self.state = self.controller.apply_processing_range(
            start_frame_index=0,
            end_frame_index=self.source_store.frame_count - 1,
        )
        self.current_playhead_frame = 0
        self._set_view_mode("source")
        self._sync_state_to_ui()
        self._render_monitor()

    def _toggle_playback(self) -> None:
        if self.playback_timer.isActive():
            self.playback_timer.stop()
            self.play_button.setText("Play")
            return
        interval_ms = int(1000 / max(1.0, self._active_fps()))
        self.playback_timer.start(interval_ms)
        self.play_button.setText("Pause")

    def _advance_playback(self) -> None:
        store = self.review_source_store if self.state.workflow_step == "review" else self.source_store
        if store is None:
            self.playback_timer.stop()
            self.play_button.setText("Play")
            return
        max_frame = store.frame_count - 1
        next_frame = self.current_playhead_frame + 1
        if next_frame > max_frame:
            self.playback_timer.stop()
            self.play_button.setText("Play")
            return
        self.current_playhead_frame = next_frame
        self.source_timeline.blockSignals(True)
        self.source_timeline.setValue(next_frame)
        self.source_timeline.blockSignals(False)
        self._update_timeline_labels()
        self._render_monitor()

    def _on_monitor_clicked(self, x: int, y: int) -> None:
        if self.controller is None or self.state.workflow_step == "review":
            return
        if self.current_interaction_mode == "positive":
            self.controller.apply_click(x=x, y=y, positive=True)
        elif self.current_interaction_mode == "negative":
            self.controller.apply_click(x=x, y=y, positive=False)
        self.state = self.controller.current_state()
        self._sync_state_to_ui()
        self._set_view_mode("overlay")

    def _on_monitor_stroke(self, points: list[tuple[int, int]]) -> None:
        if self.controller is None or self.state.workflow_step == "review":
            return
        mode_map = {
            "brush_add": "add",
            "brush_remove": "remove",
            "brush_feather": "feather",
        }
        brush_mode = mode_map.get(self.current_interaction_mode)
        if brush_mode is None or not points:
            return
        self.controller.apply_brush(points=points, mode=brush_mode, radius=int(self.brush_size_slider.value()))
        self.state = self.controller.current_state()
        self._sync_state_to_ui()
        self._set_view_mode("overlay")

    def _new_target(self) -> None:
        if self.controller is None:
            return
        self.state = self.controller.create_target()
        self._sync_state_to_ui()

    def _select_target_from_list(self, row: int) -> None:
        if self.controller is None or row < 0:
            return
        item = self.target_list.item(row)
        if item is None:
            return
        self.state = self.controller.select_target(item.data(Qt.UserRole))
        self._sync_state_to_ui()
        self._render_monitor()

    def _apply_target_name(self) -> None:
        if self.controller is None:
            return
        self.state = self.controller.update_active_target(name=self.target_name_input.text())
        self._sync_state_to_ui()

    def _toggle_visible(self, checked: bool) -> None:
        if self.controller is None:
            return
        self.state = self.controller.update_active_target(visible=checked)
        self._sync_state_to_ui()

    def _toggle_locked(self, checked: bool) -> None:
        if self.controller is None:
            return
        self.state = self.controller.update_active_target(locked=checked)
        self._sync_state_to_ui()

    def _on_interaction_mode_changed(self) -> None:
        text = self.interaction_mode.currentText()
        mapping = {
            "Positive": "positive",
            "Negative": "negative",
            "Brush Add": "brush_add",
            "Brush Remove": "brush_remove",
            "Brush Feather": "brush_feather",
        }
        self._set_interaction_mode(mapping[text], sync_combo=False)

    def _set_interaction_mode(self, mode: str, *, sync_combo: bool = True) -> None:
        self.current_interaction_mode = mode
        if sync_combo:
            index = {
                "positive": 0,
                "negative": 1,
                "brush_add": 2,
                "brush_remove": 3,
                "brush_feather": 4,
            }.get(mode, 0)
            self.interaction_mode.blockSignals(True)
            self.interaction_mode.setCurrentIndex(index)
            self.interaction_mode.blockSignals(False)
        self.monitor.surface.set_brush_enabled(self.current_interaction_mode.startswith("brush_"))
        self._sync_interaction_toolbar()
        self._sync_interaction_hint()

    def _sync_interaction_toolbar(self) -> None:
        for mode, button in self.interaction_toolbar_buttons.items():
            button.blockSignals(True)
            button.setChecked(mode == self.current_interaction_mode)
            button.blockSignals(False)

    def _sync_interaction_hint(self) -> None:
        if self.state.workflow_step == "clip":
            if self._is_full_clip_range():
                message = "Whole clip is active by default. Drag the anchor rail to choose the segmentation frame, or use Mark In/Out only if you want to trim the range."
            else:
                message = "Trimmed range is active. Drag the anchor rail inside the selected segment, or use Clear to go back to the whole clip."
        elif self.state.workflow_step == "review":
            message = "Review the processed clip here. Use Export to open outputs or return to Refine."
        elif self.current_interaction_mode == "negative":
            message = "Exclude mode is active. Click the monitor to subtract distracting regions."
        elif self.current_interaction_mode == "brush_add":
            message = "Brush Add is active. Drag on the monitor to recover missing matte detail."
        elif self.current_interaction_mode == "brush_remove":
            message = "Brush Remove is active. Drag on the monitor to trim spill or background."
        elif self.current_interaction_mode == "brush_feather":
            message = "Brush Feather is active. Drag on the monitor to soften edge transitions."
        elif self.state.workflow_step == "refine":
            message = "Select Subject is active. Click the monitor to reinforce the active target before refining."
        else:
            message = "Select Subject is active. Click the monitor to tag the active person or object."
        self.interaction_hint_label.setText(message)

    def _on_refine_controls_changed(self) -> None:
        if self.controller is None:
            return
        preset = self.refine_preset_combo.currentText().lower()
        self.state = self.controller.update_active_target(
            refine_preset=preset,
            preset_strength=self.preset_strength_slider.value() / 100.0,
            motion_strength=self.motion_softness_slider.value() / 100.0,
            temporal_stability=self.temporal_stability_slider.value() / 100.0,
            edge_feather_radius=self.edge_feather_slider.value() / 10.0,
        )
        if self.state.current_preview_path is not None:
            self._set_view_mode("overlay")
        else:
            self._render_monitor()

    def _undo_click(self) -> None:
        if self.controller is None:
            return
        self.state = self.controller.undo_last_click()
        self._sync_state_to_ui()
        self._render_monitor()

    def _reset_target(self) -> None:
        if self.controller is None:
            return
        self.state = self.controller.reset_active_target()
        self._sync_state_to_ui()
        self._render_monitor()

    def _save_target(self) -> None:
        if self.controller is None:
            return
        self.controller.save_active_target()
        self.state = self.controller.current_state()
        self._sync_state_to_ui()

    def _on_saved_mask_selection_changed(self) -> None:
        if self.controller is None:
            return
        selected = []
        for index in range(self.saved_masks_list.count()):
            item = self.saved_masks_list.item(index)
            if item.checkState() == Qt.Checked:
                selected.append(item.text())
        self.state = self.controller.set_selected_masks(selected)
        self._sync_state_to_ui()

    def _submit_job(self) -> None:
        if self.controller is None or self.current_job_handle is not None:
            return
        self.export_status_label.setText("Running MatAnyone2...")
        self.current_job_handle = DesktopJobHandle(self.controller, self.config.runtime_root)
        self.current_job_handle.finished.connect(self._on_job_finished)
        self.current_job_handle.failed.connect(self._on_job_failed)
        self.current_job_handle.start()

    def _on_job_finished(self, payload: dict) -> None:
        self.current_job_handle = None
        self.export_status_label.setText("Review ready")
        self.open_output_button.setEnabled(True)
        self.state = self.controller.current_state()
        self._open_review_stores(payload)
        self._set_view_mode("source")
        self._sync_state_to_ui()
        self._render_monitor()

    def _on_job_failed(self, message: str) -> None:
        self.current_job_handle = None
        self.export_status_label.setText(f"Failed: {message}")
        QMessageBox.critical(self, "MatAnyone2 Job Failed", message)

    def _open_output_folder(self) -> None:
        payload = self.controller.latest_job_payload() if self.controller else None
        if not payload:
            return
        job_dir = Path(payload["job_dir"])
        if job_dir.exists():
            try:
                import os

                os.startfile(str(job_dir))
            except OSError:
                pass

    def _open_review_stores(self, payload: dict) -> None:
        self.review_source_store = self._safe_open_store(payload.get("source_video_path"))
        self.review_foreground_store = self._safe_open_store(payload.get("foreground_video_path"))
        self.review_alpha_store = self._safe_open_store(payload.get("alpha_video_path"))
        store = self.review_source_store or self.review_foreground_store or self.review_alpha_store
        if store is not None:
            self.current_playhead_frame = 0
            self.source_timeline.setMinimum(0)
            self.source_timeline.setMaximum(max(store.frame_count - 1, 0))

    def _safe_open_store(self, video_path: str | None) -> VideoFrameStore | None:
        if not video_path:
            return None
        path = Path(video_path)
        if not path.exists():
            return None
        try:
            return VideoFrameStore(path)
        except ValueError:
            return None

    def _go_back(self) -> None:
        current = self.state.workflow_step
        if current == "review":
            self.state = self.controller.set_workflow_step("refine") if self.controller else self.state
        elif current == "refine":
            self.state = self.controller.set_workflow_step("mask") if self.controller else self.state
        elif current == "mask":
            self.state = self.controller.set_workflow_step("clip") if self.controller else self.state
        self._sync_state_to_ui()
        self._render_monitor()

    def _go_next(self) -> None:
        current = self.state.workflow_step
        if current == "clip" and self.state.can_enter_mask and self.controller:
            self.state = self.controller.set_workflow_step("mask")
        elif current == "mask" and self.controller:
            self.state = self.controller.set_workflow_step("refine")
        elif current == "refine" and self.controller and self.state.latest_job_id:
            self.state = self.controller.set_workflow_step("review")
        self._sync_state_to_ui()
        self._render_monitor()

    def _on_stepper_changed(self, index: int) -> None:
        if self.controller is None:
            return
        mapping = {0: "clip", 1: "mask", 2: "refine", 3: "review"}
        target_step = mapping.get(index, "clip")
        if target_step == "review" and self.state.latest_job_id is None:
            self.stepper.blockSignals(True)
            self.stepper.setCurrentIndex({"clip": 0, "mask": 1, "refine": 2}.get(self.state.workflow_step, 0))
            self.stepper.blockSignals(False)
            return
        self.state = self.controller.set_workflow_step(target_step)
        self._sync_state_to_ui()
        self._render_monitor()

    def _on_inspector_changed(self, index: int) -> None:
        if self.controller is None:
            return
        mapping = {0: "targets", 1: "refine", 2: "export"}
        self.state = self.controller.set_active_sidebar_tab(mapping.get(index, "targets"))

    def _close_video_stores(self) -> None:
        for store in (
            self.source_store,
            self.review_source_store,
            self.review_foreground_store,
            self.review_alpha_store,
        ):
            if store is not None:
                store.close()
        self.source_store = None
        self.review_source_store = None
        self.review_foreground_store = None
        self.review_alpha_store = None

    def closeEvent(self, event):  # noqa: N802
        self._close_video_stores()
        super().closeEvent(event)

    @staticmethod
    def _format_timecode(frame_index: int, fps: float) -> str:
        total_seconds = frame_index / max(fps, 1.0)
        minutes = int(total_seconds // 60)
        seconds = int(total_seconds % 60)
        frames = int(frame_index % max(int(round(fps)), 1))
        return f"{minutes:02d}:{seconds:02d}:{frames:02d}"

    @staticmethod
    def _slider(minimum: int, maximum: int, value: int) -> QSlider:
        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(minimum)
        slider.setMaximum(maximum)
        slider.setValue(value)
        return slider
