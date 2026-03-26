from pathlib import Path

import cv2
import numpy as np
import pytest


@pytest.fixture
def sample_video_path(tmp_path) -> Path:
    video_path = tmp_path / "sample.mp4"
    writer = cv2.VideoWriter(
        str(video_path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        3.0,
        (16, 12),
    )
    for idx in range(3):
        frame = np.full((12, 16, 3), fill_value=idx * 40, dtype=np.uint8)
        writer.write(frame)
    writer.release()
    return video_path
