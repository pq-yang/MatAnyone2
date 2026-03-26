from pathlib import Path
import shutil

import cv2
import numpy as np
import pytest

from matanyone2.utils.inference_utils import read_frame_from_videos


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


def test_read_frame_from_videos_accepts_m4v_extension(tmp_path, sample_video_path):
    m4v_path = tmp_path / "sample.m4v"
    shutil.copy2(sample_video_path, m4v_path)

    frames, fps, length, video_name = read_frame_from_videos(str(m4v_path))

    assert length == 3
    assert tuple(frames.shape) == (3, 3, 12, 16)
    assert fps == 3.0
    assert video_name == "sample"
