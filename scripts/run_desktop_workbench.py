from pathlib import Path
import sys

from _path_bootstrap import ensure_project_root_on_path

PROJECT_ROOT = ensure_project_root_on_path(__file__)

from matanyone2.desktop_app.app import main


if __name__ == "__main__":
    raise SystemExit(main(Path(PROJECT_ROOT)))
