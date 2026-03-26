from fastapi.testclient import TestClient

from matanyone2.webapp.api.app import create_app
from matanyone2.webapp.config import WebAppSettings


def test_create_app_builds_health_route(tmp_path, monkeypatch):
    monkeypatch.setenv("MATANYONE2_WEBAPP_RUNTIME_ROOT", str(tmp_path))
    settings = WebAppSettings()
    app = create_app(settings=settings)

    with TestClient(app) as client:
        response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
