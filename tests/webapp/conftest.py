from pathlib import Path

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from matanyone2.webapp.api.app import create_app
from matanyone2.webapp.config import WebAppSettings


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


@pytest.fixture
def sample_video_upload(sample_video_path):
    return ("sample.mp4", sample_video_path.read_bytes(), "video/mp4")


@pytest.fixture
def app_client(tmp_path) -> TestClient:
    runtime_root = tmp_path / "runtime"
    settings = WebAppSettings(
        runtime_root=runtime_root,
        database_path=runtime_root / "jobs.db",
    )
    app = create_app(settings=settings)
    with TestClient(app) as client:
        yield client
