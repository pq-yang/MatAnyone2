from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from matanyone2.webapp.config import WebAppSettings
from matanyone2.webapp.db import init_database
from matanyone2.webapp.api.routes import annotation, jobs, pages, uploads
from matanyone2.webapp.queue import QueueCoordinator
from matanyone2.webapp.repository import JobRepository
from matanyone2.webapp.services.masking import MaskingService
from matanyone2.webapp.services.video import VideoDraftService


def create_app(settings=None) -> FastAPI:
    if settings is None:
        settings = WebAppSettings()
    init_database(settings.database_path)
    app = FastAPI(title="MatAnyone2 Internal Web App")
    app.state.settings = settings
    app.state.repository = JobRepository.from_path(settings.database_path)
    app.state.queue = QueueCoordinator(app.state.repository)
    app.state.video_service = VideoDraftService(
        runtime_root=settings.runtime_root,
        max_video_seconds=settings.max_video_seconds,
        max_upload_bytes=settings.max_upload_bytes,
    )
    app.state.masking_service = MaskingService(
        runtime_root=settings.runtime_root,
        sam_backend=settings.sam_backend,
        sam_model_type=settings.sam_model_type,
        sam2_variant=settings.sam2_variant,
        sam2_checkpoint_path=settings.sam2_checkpoint_path,
    )
    app.state.drafts = {}
    app.state.templates = Jinja2Templates(directory="matanyone2/webapp/templates")
    app.state.queue.recover_interrupted_jobs()
    app.mount("/static", StaticFiles(directory="matanyone2/webapp/static"), name="static")
    app.include_router(pages.router)
    app.include_router(uploads.router)
    app.include_router(annotation.router)
    app.include_router(jobs.router)

    @app.get("/healthz")
    def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    return app
