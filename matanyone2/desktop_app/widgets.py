from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QMouseEvent, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)
import numpy as np


class MonitorCanvas(QLabel):
    clicked = Signal(int, int)
    strokeFinished = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setMouseTracking(True)
        self.setMinimumSize(960, 540)
        self.setStyleSheet(
            "background:#060a12;border:1px solid #1b2634;border-radius:12px;color:#9db2ca;"
        )
        self._qimage: QImage | None = None
        self._image_size: tuple[int, int] | None = None
        self._display_rect: tuple[int, int, int, int] | None = None
        self._brush_enabled = False
        self._stroke_points: list[tuple[int, int]] = []

    def set_numpy_image(self, image: np.ndarray | None) -> None:
        if image is None:
            self._qimage = None
            self._image_size = None
            self._display_rect = None
            self.setText("No preview")
            return

        if image.ndim == 2:
            qimage = QImage(
                image.data,
                image.shape[1],
                image.shape[0],
                image.strides[0],
                QImage.Format_Grayscale8,
            ).copy()
        else:
            rgb = np.ascontiguousarray(image[..., :3])
            qimage = QImage(
                rgb.data,
                rgb.shape[1],
                rgb.shape[0],
                rgb.strides[0],
                QImage.Format_RGB888,
            ).copy()
        self._qimage = qimage
        self._image_size = (qimage.width(), qimage.height())
        self._refresh_pixmap()

    def set_brush_enabled(self, enabled: bool) -> None:
        self._brush_enabled = enabled
        if not enabled:
            self._stroke_points = []

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        self._refresh_pixmap()

    def mousePressEvent(self, event: QMouseEvent):  # noqa: N802
        image_point = self._map_to_image(event.position().x(), event.position().y())
        if image_point is None:
            return
        x, y = image_point
        if self._brush_enabled:
            self._stroke_points = [(x, y)]
        else:
            self.clicked.emit(x, y)

    def mouseMoveEvent(self, event: QMouseEvent):  # noqa: N802
        if not self._brush_enabled or not self._stroke_points:
            return
        image_point = self._map_to_image(event.position().x(), event.position().y())
        if image_point is None:
            return
        if not self._stroke_points or image_point != self._stroke_points[-1]:
            self._stroke_points.append(image_point)

    def mouseReleaseEvent(self, event: QMouseEvent):  # noqa: N802
        if not self._brush_enabled or not self._stroke_points:
            return
        image_point = self._map_to_image(event.position().x(), event.position().y())
        if image_point is not None and image_point != self._stroke_points[-1]:
            self._stroke_points.append(image_point)
        stroke = [(int(x), int(y)) for x, y in self._stroke_points]
        self._stroke_points = []
        self.strokeFinished.emit(stroke)

    def _refresh_pixmap(self) -> None:
        if self._qimage is None:
            return
        scaled = QPixmap.fromImage(self._qimage).scaled(
            self.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.setPixmap(scaled)
        self._display_rect = (
            int((self.width() - scaled.width()) / 2),
            int((self.height() - scaled.height()) / 2),
            scaled.width(),
            scaled.height(),
        )

    def _map_to_image(self, x: float, y: float) -> tuple[int, int] | None:
        if self._display_rect is None or self._image_size is None:
            return None
        left, top, width, height = self._display_rect
        if width <= 0 or height <= 0:
            return None
        if x < left or y < top or x > left + width or y > top + height:
            return None
        image_width, image_height = self._image_size
        relative_x = (x - left) / width
        relative_y = (y - top) / height
        mapped_x = max(0, min(image_width - 1, int(relative_x * image_width)))
        mapped_y = max(0, min(image_height - 1, int(relative_y * image_height)))
        return mapped_x, mapped_y


class MonitorPane(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("monitorPane")
        self.setFrameShape(QFrame.StyledPanel)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self.mode_label = QLabel("Source")
        self.mode_label.setObjectName("monitorModeLabel")
        self.mode_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        layout.addWidget(self.mode_label)

        self.surface = MonitorCanvas()
        self.surface.setObjectName("monitorSurface")
        self.surface.setText("Main Monitor")
        layout.addWidget(self.surface, 1)


class TimelineDock(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("timelineDock")
        self.setFrameShape(QFrame.StyledPanel)
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        self.source_timeline = QSlider(Qt.Horizontal)
        self.source_timeline.setObjectName("sourceTimeline")
        root.addWidget(self.source_timeline)

        self.timeline_actions_layout = QHBoxLayout()
        self.timeline_actions_layout.setSpacing(8)
        root.addLayout(self.timeline_actions_layout)

        self.mark_in_button = QPushButton("Mark In")
        self.mark_out_button = QPushButton("Mark Out")
        self.clear_range_button = QPushButton("Clear")
        self.play_button = QPushButton("Play")
        self.current_time_label = QLabel("00:00")
        self.in_label = QLabel("In --")
        self.out_label = QLabel("Out --")
        self.duration_label = QLabel("Duration --")

        for widget in (
            self.mark_in_button,
            self.mark_out_button,
            self.clear_range_button,
            self.play_button,
            self.current_time_label,
            self.in_label,
            self.out_label,
            self.duration_label,
        ):
            if isinstance(widget, QPushButton):
                widget.setMinimumHeight(36)
            self.timeline_actions_layout.addWidget(widget)

        self.timeline_actions_layout.addStretch(1)

        self.anchor_timeline = QSlider(Qt.Horizontal)
        self.anchor_timeline.setObjectName("anchorTimeline")
        self.anchor_timeline.setEnabled(False)
        root.addWidget(self.anchor_timeline)


class InspectorPlaceholder(QWidget):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        label = QLabel(title)
        label.setObjectName(f"{title.lower()}InspectorLabel")
        layout.addWidget(label)
        layout.addStretch(1)
