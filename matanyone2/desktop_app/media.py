from pathlib import Path

import cv2
import numpy as np


class VideoFrameStore:
    def __init__(self, video_path: str | Path):
        self.video_path = Path(video_path)
        self._capture = cv2.VideoCapture(str(self.video_path))
        if not self._capture.isOpened():
            raise ValueError(f"unable to open video: {self.video_path}")
        self.fps = float(self._capture.get(cv2.CAP_PROP_FPS) or 0.0) or 24.0
        self.frame_count = int(self._capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        self.width = int(self._capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        self.height = int(self._capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)

    def read_frame(self, frame_index: int) -> np.ndarray:
        frame_index = max(0, min(self.frame_count - 1, frame_index)) if self.frame_count else 0
        self._capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ok, frame = self._capture.read()
        if not ok:
            raise ValueError(f"unable to read frame {frame_index} from {self.video_path}")
        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    def close(self) -> None:
        self._capture.release()
