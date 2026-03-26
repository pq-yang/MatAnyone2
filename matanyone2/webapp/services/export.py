from pathlib import Path
import zipfile

import numpy as np
from PIL import Image

from matanyone2.webapp.models import ExportResult
from matanyone2.webapp.runtime_paths import ensure_dir


def compose_rgba_frame(foreground_rgb: np.ndarray, alpha_gray: np.ndarray) -> Image.Image:
    rgba = np.dstack([foreground_rgb, alpha_gray]).astype(np.uint8)
    return Image.fromarray(rgba, mode="RGBA")


class ExportService:
    def __init__(self, enable_prores: bool = True):
        self.enable_prores = enable_prores

    def export_assets(
        self,
        foreground_video_path: Path,
        alpha_video_path: Path,
        job_dir: Path,
    ) -> ExportResult:
        foreground_frames, alpha_frames = self._extract_frames(
            foreground_video_path,
            alpha_video_path,
            job_dir,
        )
        rgba_png_dir = self._write_rgba_pngs(
            foreground_frames,
            alpha_frames,
            job_dir,
        )
        png_zip_path = self._zip_directory(rgba_png_dir, job_dir / "rgba_png.zip")

        warning_text = None
        prores_path = None
        if self.enable_prores:
            try:
                prores_path = self._export_prores(rgba_png_dir, job_dir / "output_prores4444.mov")
            except RuntimeError as exc:
                warning_text = str(exc)

        return ExportResult(
            rgba_png_dir=rgba_png_dir,
            png_zip_path=png_zip_path,
            prores_path=prores_path,
            warning_text=warning_text,
        )

    def _extract_frames(
        self,
        foreground_video_path: Path,
        alpha_video_path: Path,
        job_dir: Path,
    ) -> tuple[list[Path], list[Path]]:
        del foreground_video_path, alpha_video_path, job_dir
        raise NotImplementedError

    def _write_rgba_pngs(
        self,
        foreground_frames: list[Path],
        alpha_frames: list[Path],
        job_dir: Path,
    ) -> Path:
        del foreground_frames, alpha_frames
        rgba_dir = ensure_dir(job_dir / "rgba_png")
        return rgba_dir

    def _zip_directory(self, source_dir: Path, zip_path: Path) -> Path:
        with zipfile.ZipFile(zip_path, "w") as archive:
            for path in sorted(source_dir.rglob("*")):
                if path.is_file():
                    archive.write(path, arcname=path.relative_to(source_dir))
        return zip_path

    def _export_prores(self, rgba_png_dir: Path, output_path: Path) -> Path:
        del rgba_png_dir
        return output_path
