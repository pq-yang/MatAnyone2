from pathlib import Path
import shutil
import subprocess
import uuid

import cv2
from fastapi import UploadFile

from matanyone2.webapp.models import DraftRecord
from matanyone2.webapp.runtime_paths import ensure_dir


class VideoDraftService:
    def __init__(
        self,
        *,
        runtime_root: Path,
        max_video_seconds: int,
        max_upload_bytes: int,
    ):
        self.runtime_root = Path(runtime_root)
        self.max_video_seconds = max_video_seconds
        self.max_upload_bytes = max_upload_bytes

    def create_draft(self, source_video_path: Path) -> DraftRecord:
        source_video_path = Path(source_video_path)
        if source_video_path.stat().st_size > self.max_upload_bytes:
            raise ValueError("video exceeds max upload size")

        draft_id = uuid.uuid4().hex
        draft_dir = ensure_dir(self.runtime_root / "drafts" / draft_id)
        staged_video_path = draft_dir / source_video_path.name
        shutil.copy2(source_video_path, staged_video_path)

        cap = cv2.VideoCapture(str(staged_video_path))
        try:
            fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
            ok, frame = cap.read()
        finally:
            cap.release()

        if not ok or frame_count <= 0 or fps <= 0:
            raise ValueError("unable to read video frames")

        duration_seconds = frame_count / fps
        if duration_seconds > self.max_video_seconds:
            raise ValueError("video exceeds max duration")

        template_frame_path = draft_dir / "template_frame.png"
        cv2.imwrite(str(template_frame_path), frame)
        browser_preview_path = draft_dir / "preview_source.mp4"
        try:
            browser_preview_path = self.ensure_browser_preview(
                staged_video_path,
                preview_path=browser_preview_path,
            )
        except RuntimeError:
            browser_preview_path = None

        return DraftRecord(
            draft_id=draft_id,
            video_path=staged_video_path,
            browser_preview_path=browser_preview_path,
            template_frame_path=template_frame_path,
            width=width,
            height=height,
            fps=fps,
            frame_count=frame_count,
            duration_seconds=duration_seconds,
            process_start_frame_index=0,
            process_end_frame_index=frame_count - 1,
            template_frame_index=0,
        )

    def create_draft_from_upload(self, upload_file: UploadFile) -> DraftRecord:
        uploads_dir = ensure_dir(self.runtime_root / "uploads")
        upload_path = uploads_dir / upload_file.filename
        upload_path.write_bytes(upload_file.file.read())
        return self.create_draft(upload_path)

    def select_template_frame(self, draft: DraftRecord, frame_index: int) -> DraftRecord:
        if frame_index < 0 or frame_index >= draft.frame_count:
            raise ValueError("frame index is out of range")
        if not (draft.process_start_frame_index <= frame_index <= draft.process_end_frame_index):
            raise ValueError("template frame must fall inside the processing range")
        frame = self._read_frame(draft.video_path, frame_index)
        template_frame_path = draft.template_frame_path.parent / "template_frame.png"
        if not cv2.imwrite(str(template_frame_path), frame):
            raise ValueError("unable to write template frame")
        draft.template_frame_path = template_frame_path
        draft.template_frame_index = frame_index
        return draft

    def select_processing_range(
        self,
        draft: DraftRecord,
        *,
        start_frame_index: int,
        end_frame_index: int,
    ) -> DraftRecord:
        if start_frame_index < 0 or end_frame_index < 0:
            raise ValueError("processing range cannot be negative")
        if start_frame_index > end_frame_index:
            raise ValueError("processing range start must be before the end")
        if end_frame_index >= draft.frame_count:
            raise ValueError("processing range is out of range")
        draft.process_start_frame_index = start_frame_index
        draft.process_end_frame_index = end_frame_index
        draft.template_frame_index = None
        return draft

    def ensure_browser_preview(
        self,
        video_path: Path,
        *,
        preview_path: Path | None = None,
    ) -> Path:
        preview_path = preview_path or self._default_preview_path(video_path)
        if preview_path.exists() and preview_path.is_file():
            return preview_path

        ffmpeg_binary = shutil.which("ffmpeg")
        if ffmpeg_binary is None:
            raise RuntimeError("ffmpeg is not installed")

        preview_path.parent.mkdir(parents=True, exist_ok=True)
        command = [
            ffmpeg_binary,
            "-y",
            "-i",
            str(video_path),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(preview_path),
        ]
        self._run_ffmpeg_command(command)
        if not preview_path.exists():
            raise RuntimeError("ffmpeg did not produce browser preview output")
        return preview_path

    def write_processing_range_clip(
        self,
        video_path: Path,
        *,
        start_frame_index: int,
        end_frame_index: int,
        output_path: Path,
    ) -> tuple[Path, float]:
        capture = cv2.VideoCapture(str(video_path))
        fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        writer = cv2.VideoWriter(
            str(output_path),
            cv2.VideoWriter_fourcc(*"mp4v"),
            fps if fps > 0 else 24.0,
            (width, height),
        )
        frames_written = 0
        try:
            capture.set(cv2.CAP_PROP_POS_FRAMES, start_frame_index)
            for _ in range(start_frame_index, end_frame_index + 1):
                ok, frame = capture.read()
                if not ok:
                    break
                writer.write(frame)
                frames_written += 1
        finally:
            writer.release()
            capture.release()
        if frames_written == 0:
            raise ValueError("unable to extract the requested processing range")
        return output_path, fps if fps > 0 else 24.0

    @staticmethod
    def _read_frame(video_path: Path, frame_index: int):
        capture = cv2.VideoCapture(str(video_path))
        try:
            capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            ok, frame = capture.read()
        finally:
            capture.release()
        if not ok:
            raise ValueError("unable to read requested frame")
        return frame

    @staticmethod
    def _default_preview_path(video_path: Path) -> Path:
        return video_path.parent / "preview_source.mp4"

    @staticmethod
    def _run_ffmpeg_command(command: list[str]) -> None:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            stderr = completed.stderr.strip() or completed.stdout.strip() or "ffmpeg failed"
            raise RuntimeError(stderr)
