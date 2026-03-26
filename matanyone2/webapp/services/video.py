from pathlib import Path
import shutil
import uuid

import cv2

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

        return DraftRecord(
            draft_id=draft_id,
            video_path=staged_video_path,
            template_frame_path=template_frame_path,
            width=width,
            height=height,
            fps=fps,
            frame_count=frame_count,
            duration_seconds=duration_seconds,
        )
