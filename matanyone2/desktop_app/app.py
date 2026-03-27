from pathlib import Path
import sys

from PySide6.QtWidgets import QApplication

from matanyone2.desktop_app.config import DesktopAppConfig
from matanyone2.desktop_app.main_window import DesktopWorkbenchWindow
from matanyone2.desktop_app.session_controller import DesktopWorkbenchController
from matanyone2.webapp.services.export import ExportService
from matanyone2.webapp.services.inference import InferenceService
from matanyone2.webapp.services.masking import MaskingService
from matanyone2.webapp.services.video import VideoDraftService


def build_desktop_config(project_root: str | Path) -> DesktopAppConfig:
    return DesktopAppConfig.for_root(Path(project_root))


def build_controller(config: DesktopAppConfig) -> DesktopWorkbenchController:
    video_service = VideoDraftService(
        runtime_root=config.runtime_root,
        max_video_seconds=config.max_video_seconds,
        max_upload_bytes=config.max_upload_bytes,
    )
    masking_service = MaskingService(
        runtime_root=config.runtime_root,
        sam_backend=config.sam_backend,
        sam3_checkpoint_path=str(config.sam3_checkpoint_path),
    )
    return DesktopWorkbenchController(
        config=config,
        video_service=video_service,
        masking_service=masking_service,
        inference_service=InferenceService(),
        export_service=ExportService(),
    )


def main(project_root: str | Path) -> int:
    config = build_desktop_config(project_root)
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName(config.window_title)
    controller = build_controller(config)
    window = DesktopWorkbenchWindow(config=config, controller=controller)
    window.show()
    return app.exec()
