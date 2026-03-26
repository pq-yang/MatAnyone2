try:
    from scripts._path_bootstrap import ensure_project_root_on_path
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from _path_bootstrap import ensure_project_root_on_path

ensure_project_root_on_path(__file__)

from matanyone2.webapp.config import WebAppSettings
from matanyone2.webapp.queue import QueueCoordinator
from matanyone2.webapp.repository import JobRepository
from matanyone2.webapp.services.export import ExportService
from matanyone2.webapp.services.inference import InferenceService
from matanyone2.webapp.worker import WorkerLoop


def main() -> None:
    settings = WebAppSettings()
    repository = JobRepository.from_path(settings.database_path)
    worker = WorkerLoop(
        QueueCoordinator(repository),
        repository=repository,
        inference_service=InferenceService(),
        export_service=ExportService(enable_prores=settings.enable_prores_export),
        runtime_root=settings.runtime_root,
    )
    worker.recover()
    worker.run_forever()


if __name__ == "__main__":
    main()
