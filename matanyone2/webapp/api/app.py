from fastapi import FastAPI

from matanyone2.webapp.config import WebAppSettings
from matanyone2.webapp.db import init_database


def create_app(settings=None) -> FastAPI:
    if settings is None:
        settings = WebAppSettings()
    init_database(settings.database_path)
    app = FastAPI(title="MatAnyone2 Internal Web App")
    app.state.settings = settings

    @app.get("/healthz")
    def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    return app
