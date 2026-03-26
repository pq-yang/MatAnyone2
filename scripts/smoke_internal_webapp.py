try:
    from scripts._path_bootstrap import ensure_project_root_on_path
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from _path_bootstrap import ensure_project_root_on_path

ensure_project_root_on_path(__file__)

from matanyone2.webapp.smoke import main


if __name__ == "__main__":
    raise SystemExit(main())
