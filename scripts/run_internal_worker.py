from matanyone2.webapp.config import WebAppSettings
from matanyone2.webapp.queue import QueueCoordinator
from matanyone2.webapp.repository import JobRepository
from matanyone2.webapp.worker import WorkerLoop


def main() -> None:
    settings = WebAppSettings()
    repository = JobRepository.from_path(settings.database_path)
    worker = WorkerLoop(QueueCoordinator(repository))
    worker.recover()


if __name__ == "__main__":
    main()
