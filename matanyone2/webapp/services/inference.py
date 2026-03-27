from pathlib import Path
import shutil

import cv2

from matanyone2.webapp.models import InferenceResult


class InferenceService:
    def __init__(self, model_name: str = "MatAnyone 2"):
        self.model_name = model_name

    def run_job(
        self,
        *,
        source_video_path: Path,
        mask_path: Path,
        job_dir: Path,
        template_frame_index: int,
        process_start_frame_index: int = 0,
        process_end_frame_index: int | None = None,
    ) -> InferenceResult:
        source_video_path = Path(source_video_path)
        mask_path = Path(mask_path)
        job_dir = Path(job_dir)
        clip_source_video_path, relative_anchor_frame_index, _ = self._prepare_processing_clip(
            source_video_path=source_video_path,
            job_dir=job_dir,
            process_start_frame_index=process_start_frame_index,
            process_end_frame_index=process_end_frame_index,
            template_frame_index=template_frame_index,
        )
        if relative_anchor_frame_index > 0:
            foreground_path, alpha_path = self._run_bidirectional_job(
                source_video_path=clip_source_video_path,
                mask_path=mask_path,
                job_dir=job_dir,
                template_frame_index=relative_anchor_frame_index,
            )
        else:
            foreground_path, alpha_path = self._run_model(
                source_video_path=clip_source_video_path,
                mask_path=mask_path,
                job_dir=job_dir,
                template_frame_index=relative_anchor_frame_index,
            )
        return InferenceResult(
            foreground_video_path=foreground_path,
            alpha_video_path=alpha_path,
        )

    def _prepare_processing_clip(
        self,
        *,
        source_video_path: Path,
        job_dir: Path,
        process_start_frame_index: int,
        process_end_frame_index: int | None,
        template_frame_index: int,
    ) -> tuple[Path, int, float | None]:
        if process_end_frame_index is None and process_start_frame_index == 0:
            return source_video_path, template_frame_index, None

        frames, fps = self._read_video_frames(source_video_path)
        if not frames:
            raise RuntimeError("source video has no readable frames")

        resolved_end = process_end_frame_index if process_end_frame_index is not None else len(frames) - 1
        if process_start_frame_index < 0 or process_start_frame_index > resolved_end:
            raise ValueError("processing range start must be before the end")
        if resolved_end >= len(frames):
            raise ValueError("processing range is out of range for source video")
        if not (process_start_frame_index <= template_frame_index <= resolved_end):
            raise ValueError("template frame must fall inside the processing range")

        clipped_frames = frames[process_start_frame_index : resolved_end + 1]
        clip_path = job_dir / "processing_range.mp4"
        self._write_video_frames(clipped_frames, clip_path, fps=fps)
        relative_anchor = template_frame_index - process_start_frame_index
        return clip_path, relative_anchor, fps

    def _run_bidirectional_job(
        self,
        *,
        source_video_path: Path,
        mask_path: Path,
        job_dir: Path,
        template_frame_index: int,
    ) -> tuple[Path, Path]:
        frames, fps = self._read_video_frames(source_video_path)
        if not frames:
            raise RuntimeError("source video has no readable frames")
        if template_frame_index >= len(frames):
            raise ValueError("template frame index is out of range for source video")

        forward_frames = frames[template_frame_index:]
        backward_frames = list(reversed(frames[:template_frame_index + 1]))

        staging_dir = job_dir / "bidirectional"
        staging_dir.mkdir(parents=True, exist_ok=True)
        forward_input = staging_dir / "forward_input.mp4"
        backward_input = staging_dir / "backward_input.mp4"
        self._write_video_frames(forward_frames, forward_input, fps=fps)
        self._write_video_frames(backward_frames, backward_input, fps=fps)

        forward_job_dir = staging_dir / "forward_run"
        backward_job_dir = staging_dir / "backward_run"
        forward_foreground, forward_alpha = self._run_model(
            source_video_path=forward_input,
            mask_path=mask_path,
            job_dir=forward_job_dir,
            template_frame_index=0,
        )
        backward_foreground, backward_alpha = self._run_model(
            source_video_path=backward_input,
            mask_path=mask_path,
            job_dir=backward_job_dir,
            template_frame_index=0,
        )

        foreground_path = job_dir / "foreground.mp4"
        alpha_path = job_dir / "alpha.mp4"
        self._stitch_pass_outputs(
            backward_video_path=backward_foreground,
            forward_video_path=forward_foreground,
            output_path=foreground_path,
            fps=fps,
        )
        self._stitch_pass_outputs(
            backward_video_path=backward_alpha,
            forward_video_path=forward_alpha,
            output_path=alpha_path,
            fps=fps,
        )
        return foreground_path, alpha_path

    def _run_model(
        self,
        *,
        source_video_path: Path,
        mask_path: Path,
        job_dir: Path,
        template_frame_index: int,
    ) -> tuple[Path, Path]:
        del template_frame_index
        from inference_matanyone2 import main as run_inference

        job_dir.mkdir(parents=True, exist_ok=True)

        run_inference(
            input_path=str(source_video_path),
            mask_path=str(mask_path),
            output_path=str(job_dir),
            ckpt_path="pretrained_models/matanyone2.pth",
        )

        stem = source_video_path.stem
        generated_foreground = job_dir / f"{stem}_fgr.mp4"
        generated_alpha = job_dir / f"{stem}_pha.mp4"
        foreground_path = job_dir / "foreground.mp4"
        alpha_path = job_dir / "alpha.mp4"
        shutil.move(generated_foreground, foreground_path)
        shutil.move(generated_alpha, alpha_path)
        return foreground_path, alpha_path

    def _read_video_frames(self, video_path: Path) -> tuple[list, float]:
        capture = cv2.VideoCapture(str(video_path))
        fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
        frames = []
        try:
            while True:
                ok, frame = capture.read()
                if not ok:
                    break
                frames.append(frame)
        finally:
            capture.release()
        return frames, fps if fps > 0 else 24.0

    def _write_video_frames(self, frames: list, output_path: Path, *, fps: float) -> Path:
        if not frames:
            raise RuntimeError("cannot write an empty video")
        height, width = frames[0].shape[:2]
        writer = cv2.VideoWriter(
            str(output_path),
            cv2.VideoWriter_fourcc(*"mp4v"),
            fps if fps > 0 else 24.0,
            (width, height),
        )
        try:
            for frame in frames:
                writer.write(frame)
        finally:
            writer.release()
        return output_path

    def _stitch_pass_outputs(
        self,
        *,
        backward_video_path: Path,
        forward_video_path: Path,
        output_path: Path,
        fps: float,
    ) -> Path:
        backward_frames, _ = self._read_video_frames(backward_video_path)
        forward_frames, _ = self._read_video_frames(forward_video_path)
        restored_backward_frames = list(reversed(backward_frames))
        stitched_frames = restored_backward_frames[:-1] + forward_frames
        return self._write_video_frames(stitched_frames, output_path, fps=fps)
