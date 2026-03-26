import runpy
import sys
from importlib.util import find_spec
from pathlib import Path

from fastapi.testclient import TestClient

from matanyone2.webapp.api.app import create_app
from matanyone2.webapp.config import WebAppSettings
from scripts._path_bootstrap import ensure_project_root_on_path


def test_create_app_builds_health_route(tmp_path, monkeypatch):
    monkeypatch.setenv("MATANYONE2_WEBAPP_RUNTIME_ROOT", str(tmp_path))
    settings = WebAppSettings()
    app = create_app(settings=settings)

    with TestClient(app) as client:
        response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_app_uses_configured_sam_model_type(tmp_path):
    settings = WebAppSettings(
        runtime_root=tmp_path,
        database_path=tmp_path / "jobs.db",
        sam_model_type="vit_b",
    )

    app = create_app(settings=settings)

    assert app.state.masking_service.sam_model_type == "vit_b"


def test_ensure_project_root_on_path_prepends_repo_root(monkeypatch, tmp_path):
    repo_root = tmp_path / "repo"
    scripts_dir = repo_root / "scripts"
    scripts_dir.mkdir(parents=True)
    script_path = scripts_dir / "run_internal_worker.py"
    script_path.write_text("", encoding="utf-8")
    monkeypatch.setattr(sys, "path", [str(scripts_dir)])

    resolved_root = ensure_project_root_on_path(script_path)

    assert resolved_root == repo_root
    assert sys.path[0] == str(repo_root)


def test_run_internal_worker_script_bootstraps_from_scripts_dir(monkeypatch):
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / "run_internal_worker.py"

    monkeypatch.setattr(sys, "path", [str(script_path.parent)])
    sys.modules.pop("_path_bootstrap", None)
    sys.modules.pop("scripts._path_bootstrap", None)

    globals_after_load = runpy.run_path(str(script_path), run_name="__not_main__")

    assert "main" in globals_after_load


def test_internal_webapp_runtime_has_matplotlib_available():
    assert find_spec("matplotlib") is not None
