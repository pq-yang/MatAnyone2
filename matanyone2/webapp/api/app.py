from fastapi import FastAPI


def create_app(settings=None) -> FastAPI:
    app = FastAPI(title="MatAnyone2 Internal Web App")
    app.state.settings = settings

    @app.get("/healthz")
    def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    return app
