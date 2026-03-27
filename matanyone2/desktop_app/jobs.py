from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import QObject, QThread, Signal

from matanyone2.desktop_app.session_controller import DesktopWorkbenchController


class DesktopJobWorker(QObject):
    finished = Signal(dict)
    failed = Signal(str)
    progress = Signal(str, int, bool)

    def __init__(self, controller: DesktopWorkbenchController, runtime_root: Path):
        super().__init__()
        self.controller = controller
        self.runtime_root = Path(runtime_root)

    def run(self) -> None:
        job_dir = self.runtime_root / "jobs" / uuid4().hex
        try:
            self.progress.emit("Preparing session", 5, False)
            payload = self.controller.submit_job(job_dir, progress_callback=self.progress.emit)
        except Exception as exc:  # pragma: no cover - exercised in manual flows
            self.failed.emit(str(exc))
            return
        self.finished.emit(payload)


class DesktopJobHandle(QObject):
    finished = Signal(dict)
    failed = Signal(str)
    progress = Signal(str, int, bool)

    def __init__(self, controller: DesktopWorkbenchController, runtime_root: Path):
        super().__init__()
        self.thread = QThread()
        self.worker = DesktopJobWorker(controller, runtime_root)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.progress.emit)
        self.worker.finished.connect(self._on_finished)
        self.worker.failed.connect(self._on_failed)

    def start(self) -> None:
        self.thread.start()

    def _on_finished(self, payload: dict) -> None:
        self.finished.emit(payload)
        self.thread.quit()
        self.thread.wait()

    def _on_failed(self, message: str) -> None:
        self.failed.emit(message)
        self.thread.quit()
        self.thread.wait()
