from pathlib import Path
import shutil
import subprocess
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
        *,
        motion_strength: float = 0.0,
        temporal_stability: float = 0.0,
    ) -> ExportResult:
        foreground_frames, alpha_frames, fps = self._extract_frames(
            foreground_video_path,
            alpha_video_path,
            job_dir,
        )
        rgba_png_dir = self._write_rgba_pngs(
            foreground_frames,
            alpha_frames,
            job_dir,
            motion_strength=motion_strength,
            temporal_stability=temporal_stability,
        )
        png_zip_path = self._zip_directory(rgba_png_dir, job_dir / "rgba_png.zip")
        preview_foreground_path = None
        preview_alpha_path = None

        warning_text = None
        try:
            preview_foreground_path, preview_alpha_path = self._export_preview_videos(
                foreground_video_path,
                alpha_video_path,
                job_dir,
            )
        except RuntimeError as exc:
            warning_text = str(exc)

        prores_path = None
        if self.enable_prores:
            try:
                prores_path = self._export_prores(
                    rgba_png_dir,
                    job_dir / "output_prores4444.mov",
                    fps=fps,
                )
            except RuntimeError as exc:
                warning_text = self._merge_warning_text(warning_text, str(exc))

        return ExportResult(
            rgba_png_dir=rgba_png_dir,
            png_zip_path=png_zip_path,
            preview_foreground_path=preview_foreground_path,
            preview_alpha_path=preview_alpha_path,
            prores_path=prores_path,
            warning_text=warning_text,
        )

    def _extract_frames(
        self,
        foreground_video_path: Path,
        alpha_video_path: Path,
        job_dir: Path,
    ) -> tuple[list[Path], list[Path], float]:
        foreground_dir = ensure_dir(job_dir / "foreground_frames")
        alpha_dir = ensure_dir(job_dir / "alpha_frames")
        foreground_paths: list[Path] = []
        alpha_paths: list[Path] = []

        foreground_capture = cv2.VideoCapture(str(foreground_video_path))
        alpha_capture = cv2.VideoCapture(str(alpha_video_path))
        fps = float(foreground_capture.get(cv2.CAP_PROP_FPS) or 0.0)

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
        if fps <= 0:
            fps = 24.0
        return foreground_paths, alpha_paths, fps

    def _write_rgba_pngs(
        self,
        foreground_frames: list[Path],
        alpha_frames: list[Path],
        job_dir: Path,
        *,
        motion_strength: float,
        temporal_stability: float,
    ) -> Path:
        rgba_dir = ensure_dir(job_dir / "rgba_png")
        processed_alpha_frames = []
        for alpha_path in alpha_frames:
            alpha_image = cv2.imread(str(alpha_path), cv2.IMREAD_UNCHANGED)
            if alpha_image is None:
                raise RuntimeError(f"unable to read alpha frame: {alpha_path}")
            if alpha_image.ndim == 3:
                alpha_gray = cv2.cvtColor(alpha_image, cv2.COLOR_BGR2GRAY)
            else:
                alpha_gray = alpha_image
            processed_alpha_frames.append(
                self._apply_motion_softness(alpha_gray, motion_strength=motion_strength)
            )

        processed_alpha_frames = self._stabilize_alpha_frames(
            processed_alpha_frames,
            temporal_stability=temporal_stability,
        )
        for index, (foreground_path, alpha_path) in enumerate(
            zip(foreground_frames, alpha_frames, strict=True)
        ):
            foreground_rgb = cv2.cvtColor(
                cv2.imread(str(foreground_path), cv2.IMREAD_COLOR),
                cv2.COLOR_BGR2RGB,
            )
            alpha_gray = processed_alpha_frames[index]
            cv2.imwrite(str(alpha_path), alpha_gray)
            rgba_frame = compose_rgba_frame(foreground_rgb, alpha_gray)
            rgba_frame.save(rgba_dir / f"{index:04d}.png")
        return rgba_dir

    def _apply_motion_softness(
        self,
        alpha_frame: np.ndarray,
        *,
        motion_strength: float,
    ) -> np.ndarray:
        if motion_strength <= 0:
            return alpha_frame.astype(np.uint8)
        radius = max(1, int(round(1 + (motion_strength * 4))))
        kernel_size = radius if radius % 2 == 1 else radius + 1
        blurred = cv2.GaussianBlur(alpha_frame, (kernel_size, kernel_size), sigmaX=0)
        return blurred.astype(np.uint8)

    def _stabilize_alpha_frames(
        self,
        alpha_frames: list[np.ndarray],
        *,
        temporal_stability: float,
    ) -> list[np.ndarray]:
        if temporal_stability <= 0 or len(alpha_frames) <= 1:
            return [frame.astype(np.uint8) for frame in alpha_frames]

        stabilized = [alpha_frames[0].astype(np.uint8)]
        blended_previous = alpha_frames[0].astype(np.float32)
        for current in alpha_frames[1:]:
            blended = cv2.addWeighted(
                current.astype(np.float32),
                1.0 - temporal_stability,
                blended_previous,
                temporal_stability,
                0.0,
            )
            stabilized.append(np.clip(blended, 0, 255).astype(np.uint8))
            blended_previous = blended
        return stabilized

    def _zip_directory(self, source_dir: Path, zip_path: Path) -> Path:
        with zipfile.ZipFile(zip_path, "w") as archive:
            for path in sorted(source_dir.rglob("*")):
                if path.is_file():
                    archive.write(path, arcname=path.relative_to(source_dir))
        return zip_path

    def _export_preview_videos(
        self,
        foreground_video_path: Path,
        alpha_video_path: Path,
        job_dir: Path,
    ) -> tuple[Path, Path]:
        ffmpeg_binary = shutil.which("ffmpeg")
        if ffmpeg_binary is None:
            raise RuntimeError("ffmpeg is not installed")

        preview_foreground_path = job_dir / "preview_foreground.mp4"
        preview_alpha_path = job_dir / "preview_alpha.mp4"
        self._export_browser_preview_video(
            ffmpeg_binary,
            foreground_video_path,
            preview_foreground_path,
        )
        self._export_browser_preview_video(
            ffmpeg_binary,
            alpha_video_path,
            preview_alpha_path,
        )
        return preview_foreground_path, preview_alpha_path

    def _export_browser_preview_video(
        self,
        ffmpeg_binary: str,
        input_path: Path,
        output_path: Path,
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        command = [
            ffmpeg_binary,
            "-y",
            "-i",
            str(input_path),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
        self._run_ffmpeg_command(command)
        if not output_path.exists():
            raise RuntimeError(f"ffmpeg did not produce browser preview output: {output_path.name}")
        return output_path

    def _export_prores(self, rgba_png_dir: Path, output_path: Path, *, fps: float) -> Path:
        first_frame = rgba_png_dir / "0000.png"
        if not first_frame.exists():
            raise RuntimeError("rgba png sequence is empty")

        ffmpeg_binary = shutil.which("ffmpeg")
        if ffmpeg_binary is None:
            raise RuntimeError("ffmpeg is not installed")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        command = [
            ffmpeg_binary,
            "-y",
            "-framerate",
            str(fps),
            "-i",
            str(rgba_png_dir / "%04d.png"),
            "-c:v",
            "prores_ks",
            "-profile:v",
            "4444",
            "-pix_fmt",
            "yuva444p10le",
            str(output_path),
        ]
        self._run_ffmpeg_command(command)
        if not output_path.exists():
            raise RuntimeError("ffmpeg did not produce prores output")
        return output_path

    def _run_ffmpeg_command(self, command: list[str]) -> None:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            stderr = completed.stderr.strip() or completed.stdout.strip() or "ffmpeg failed"
            raise RuntimeError(stderr)

    @staticmethod
    def _merge_warning_text(existing: str | None, incoming: str) -> str:
        if not existing:
            return incoming
        return f"{existing}\n{incoming}"
