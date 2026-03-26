try:
    from scripts._path_bootstrap import ensure_project_root_on_path
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from _path_bootstrap import ensure_project_root_on_path

ensure_project_root_on_path(__file__)

from matanyone2.webapp.api.app import create_app
from matanyone2.webapp.config import WebAppSettings


app = create_app(settings=WebAppSettings())
