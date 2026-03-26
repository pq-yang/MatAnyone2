from fastapi import FastAPI

from matanyone2.webapp.config import WebAppSettings
from matanyone2.webapp.db import init_database
from matanyone2.webapp.queue import QueueCoordinator
from matanyone2.webapp.repository import JobRepository


def create_app(settings=None) -> FastAPI:
    if settings is None:
        settings = WebAppSettings()
    init_database(settings.database_path)
    app = FastAPI(title="MatAnyone2 Internal Web App")
    app.state.settings = settings
    app.state.repository = JobRepository.from_path(settings.database_path)
    app.state.queue = QueueCoordinator(app.state.repository)
    app.state.queue.recover_interrupted_jobs()

    @app.get("/healthz")
    def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    return app
