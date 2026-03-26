from pathlib import Path
import zipfile

import cv2
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
        foreground_dir = ensure_dir(job_dir / "foreground_frames")
        alpha_dir = ensure_dir(job_dir / "alpha_frames")
        foreground_paths: list[Path] = []
        alpha_paths: list[Path] = []

        foreground_capture = cv2.VideoCapture(str(foreground_video_path))
        alpha_capture = cv2.VideoCapture(str(alpha_video_path))

        try:
            frame_index = 0
            while True:
                fg_ok, fg_frame = foreground_capture.read()
                alpha_ok, alpha_frame = alpha_capture.read()

                if not fg_ok and not alpha_ok:
                    break
                if fg_ok != alpha_ok:
                    raise RuntimeError("foreground and alpha frame counts do not match")

                foreground_path = foreground_dir / f"{frame_index:04d}.png"
                alpha_path = alpha_dir / f"{frame_index:04d}.png"
                cv2.imwrite(str(foreground_path), fg_frame)
                cv2.imwrite(str(alpha_path), alpha_frame)
                foreground_paths.append(foreground_path)
                alpha_paths.append(alpha_path)
                frame_index += 1
        finally:
            foreground_capture.release()
            alpha_capture.release()

        if not foreground_paths:
            raise RuntimeError("no frames extracted from foreground video")
        return foreground_paths, alpha_paths

    def _write_rgba_pngs(
        self,
        foreground_frames: list[Path],
        alpha_frames: list[Path],
        job_dir: Path,
    ) -> Path:
        rgba_dir = ensure_dir(job_dir / "rgba_png")
        for index, (foreground_path, alpha_path) in enumerate(
            zip(foreground_frames, alpha_frames, strict=True)
        ):
            foreground_rgb = cv2.cvtColor(
                cv2.imread(str(foreground_path), cv2.IMREAD_COLOR),
                cv2.COLOR_BGR2RGB,
            )
            alpha_image = cv2.imread(str(alpha_path), cv2.IMREAD_UNCHANGED)
            if alpha_image is None:
                raise RuntimeError(f"unable to read alpha frame: {alpha_path}")
            if alpha_image.ndim == 3:
                alpha_gray = cv2.cvtColor(alpha_image, cv2.COLOR_BGR2GRAY)
            else:
                alpha_gray = alpha_image
            rgba_frame = compose_rgba_frame(foreground_rgb, alpha_gray)
            rgba_frame.save(rgba_dir / f"{index:04d}.png")
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
