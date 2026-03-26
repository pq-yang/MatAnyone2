from pathlib import Path

import cv2
import numpy as np
from PIL import Image

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
        lambda *args, **kwargs: (
            [tmp_path / "fg-0001.png"],
            [tmp_path / "a-0001.png"],
            24.0,
        ),
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


def test_export_assets_writes_rgba_png_sequence_from_videos(tmp_path):
    foreground = tmp_path / "foreground.mp4"
    alpha = tmp_path / "alpha.mp4"

    fg_writer = cv2.VideoWriter(
        str(foreground),
        cv2.VideoWriter_fourcc(*"mp4v"),
        2.0,
        (4, 4),
    )
    alpha_writer = cv2.VideoWriter(
        str(alpha),
        cv2.VideoWriter_fourcc(*"mp4v"),
        2.0,
        (4, 4),
    )
    fg_writer.write(np.full((4, 4, 3), (10, 20, 30), dtype=np.uint8))
    alpha_writer.write(np.full((4, 4, 3), 128, dtype=np.uint8))
    fg_writer.release()
    alpha_writer.release()

    service = ExportService(enable_prores=False)
    result = service.export_assets(foreground, alpha, tmp_path)

    rgba_frame = Image.open(result.rgba_png_dir / "0000.png")

    assert result.png_zip_path.exists()
    assert rgba_frame.mode == "RGBA"
    assert rgba_frame.getextrema()[3][1] > 0


def test_export_prores_uses_alpha_capable_ffmpeg_command(tmp_path, monkeypatch):
    rgba_dir = tmp_path / "rgba_png"
    rgba_dir.mkdir()
    Image.new("RGBA", (4, 4), color=(10, 20, 30, 128)).save(rgba_dir / "0000.png")

    service = ExportService(enable_prores=True)
    captured = {}

    def fake_run(command):
        captured["command"] = command
        Path(command[-1]).write_bytes(b"mov")

    monkeypatch.setattr(service, "_run_ffmpeg_command", fake_run)

    output_path = service._export_prores(
        rgba_dir,
        tmp_path / "output_prores4444.mov",
        fps=23.976,
    )

    assert output_path.exists()
    assert "prores_ks" in captured["command"]
    assert "yuva444p10le" in captured["command"]
    assert "23.976" in captured["command"]
