from pathlib import Path

from matanyone2.desktop_app.config import DesktopAppConfig


def test_desktop_app_config_defaults_runtime_paths(tmp_path: Path):
    config = DesktopAppConfig.for_root(tmp_path)

    assert config.project_root == tmp_path
    assert config.runtime_root == tmp_path / "runtime" / "desktop_workbench"
    assert config.window_title == "MatAnyone2 Desktop Workbench"
    assert config.default_step == "clip"


def test_desktop_app_config_exposes_checkpoint_defaults(tmp_path: Path):
    config = DesktopAppConfig.for_root(tmp_path)

    assert config.sam_backend == "sam3"
    assert config.sam3_checkpoint_path is not None
    assert config.max_video_seconds == 60
