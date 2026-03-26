from pathlib import Path

from matanyone2.webapp.services.export import ExportService


def test_export_assets_creates_png_zip_even_when_prores_fails(tmp_path, monkeypatch):
    service = ExportService(enable_prores=True)
    foreground = tmp_path / "foreground.mp4"
    alpha = tmp_path / "alpha.mp4"
    foreground.write_bytes(b"fg")
    alpha.write_bytes(b"a")

    monkeypatch.setattr(
        service,
        "_extract_frames",
        lambda *args, **kwargs: ([tmp_path / "fg-0001.png"], [tmp_path / "a-0001.png"]),
    )
    monkeypatch.setattr(
        service,
        "_write_rgba_pngs",
        lambda *args, **kwargs: tmp_path / "rgba_png",
    )
    monkeypatch.setattr(
        service,
        "_zip_directory",
        lambda *args, **kwargs: tmp_path / "rgba_png.zip",
    )
    monkeypatch.setattr(
        service,
        "_export_prores",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("ffmpeg failed")),
    )

    result = service.export_assets(foreground, alpha, tmp_path)

    assert result.png_zip_path.name == "rgba_png.zip"
    assert result.warning_text == "ffmpeg failed"
