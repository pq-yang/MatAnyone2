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
        edge_feather_radius: float = 0.0,
    ) -> ExportResult:
        foreground_frames, alpha_frames, fps = self._extract_frames(
            foreground_video_path,
            alpha_video_path,
            job_dir,
        )
        processed_alpha_frames = self._process_alpha_frames(
            alpha_frames,
            motion_strength=motion_strength,
            temporal_stability=temporal_stability,
            edge_feather_radius=edge_feather_radius,
        )
        self._overwrite_alpha_frames(alpha_frames, processed_alpha_frames)
        self._write_alpha_video(processed_alpha_frames, alpha_video_path, fps=fps)
        rgba_png_dir = self._write_rgba_pngs(
            foreground_frames,
            processed_alpha_frames,
            job_dir,
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

    def _process_alpha_frames(
        self,
        alpha_frames: list[Path],
        *,
        motion_strength: float,
        temporal_stability: float,
        edge_feather_radius: float,
    ) -> list[np.ndarray]:
        processed_alpha_frames: list[np.ndarray] = []
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
        return [
            self._apply_edge_feather(alpha_frame, feather_radius=edge_feather_radius)
            for alpha_frame in processed_alpha_frames
        ]

    def _overwrite_alpha_frames(
        self,
        alpha_frames: list[Path],
        processed_alpha_frames: list[np.ndarray],
    ) -> None:
        for alpha_path, alpha_frame in zip(alpha_frames, processed_alpha_frames, strict=True):
            cv2.imwrite(str(alpha_path), alpha_frame)

    def _write_rgba_pngs(
        self,
        foreground_frames: list[Path],
        processed_alpha_frames: list[np.ndarray],
        job_dir: Path,
    ) -> Path:
        rgba_dir = ensure_dir(job_dir / "rgba_png")
        for index, (foreground_path, alpha_gray) in enumerate(
            zip(foreground_frames, processed_alpha_frames, strict=True)
        ):
            foreground_rgb = cv2.cvtColor(
                cv2.imread(str(foreground_path), cv2.IMREAD_COLOR),
                cv2.COLOR_BGR2RGB,
            )
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

        stabilized: list[np.ndarray] = []
        window_radius = max(1, int(round(1 + (temporal_stability * 2))))
        for index, current in enumerate(alpha_frames):
            start = max(0, index - window_radius)
            end = min(len(alpha_frames), index + window_radius + 1)
            window = np.stack(alpha_frames[start:end]).astype(np.float32)
            median_frame = np.median(window, axis=0)
            mean_frame = np.mean(window, axis=0)
            current_float = current.astype(np.float32)

            binary = np.where(current > 127, 255, 0).astype(np.uint8)
            kernel_size = self._odd_kernel_size(3 + int(round(temporal_stability * 4)))
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
            edge_band = cv2.morphologyEx(binary, cv2.MORPH_GRADIENT, kernel)
            semitransparent = (
                ((current > 8) & (current < 247))
                | ((median_frame > 8) & (median_frame < 247))
            )
            edge_mask = (edge_band > 0) | semitransparent

            core_blend = cv2.addWeighted(
                current_float,
                1.0 - (temporal_stability * 0.25),
                mean_frame,
                temporal_stability * 0.25,
                0.0,
            )
            edge_blend = cv2.addWeighted(
                current_float,
                1.0 - temporal_stability,
                median_frame,
                temporal_stability,
                0.0,
            )
            stabilized_frame = core_blend
            stabilized_frame[edge_mask] = edge_blend[edge_mask]
            stabilized.append(np.clip(stabilized_frame, 0, 255).astype(np.uint8))
        return stabilized

    def _apply_edge_feather(
        self,
        alpha_frame: np.ndarray,
        *,
        feather_radius: float,
    ) -> np.ndarray:
        feather_radius = max(0.0, float(feather_radius))
        base = np.clip(alpha_frame, 0, 255).astype(np.uint8)
        if feather_radius <= 0:
            return base

        kernel_size = self._odd_kernel_size(max(3, int(round(min(feather_radius, 3.0)))))
        blur_size = self._odd_kernel_size(max(3, int(round((feather_radius * 2.0) + 1.0))))
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
        binary = np.where(base > 127, 255, 0).astype(np.uint8)
        edge_band = cv2.morphologyEx(binary, cv2.MORPH_GRADIENT, kernel)
        edge_weight = edge_band.astype(np.float32) / 255.0
        edge_mask = (edge_band > 0) | ((base > 0) & (base < 255))
        blurred = cv2.GaussianBlur(
            base,
            (blur_size, blur_size),
            sigmaX=max(0.8, feather_radius / 2.0),
        )
        feathered = base.astype(np.float32)
        feathered[edge_mask] = (
            (base.astype(np.float32)[edge_mask] * (1.0 - edge_weight[edge_mask]))
            + (blurred.astype(np.float32)[edge_mask] * edge_weight[edge_mask])
        )
        return np.clip(feathered, 0, 255).astype(np.uint8)

    def _write_alpha_video(
        self,
        alpha_frames: list[np.ndarray],
        output_path: Path,
        *,
        fps: float,
    ) -> Path:
        if not alpha_frames:
            raise RuntimeError("cannot write an empty alpha video")
        height, width = alpha_frames[0].shape[:2]
        writer = cv2.VideoWriter(
            str(output_path),
            cv2.VideoWriter_fourcc(*"mp4v"),
            fps if fps > 0 else 24.0,
            (width, height),
        )
        try:
            for frame in alpha_frames:
                writer.write(cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR))
        finally:
            writer.release()
        return output_path

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

    @staticmethod
    def _odd_kernel_size(size: int) -> int:
        return size if size % 2 == 1 else size + 1
