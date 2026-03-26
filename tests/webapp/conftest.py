from pathlib import Path

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from matanyone2.webapp.api.app import create_app
from matanyone2.webapp.config import WebAppSettings
from matanyone2.webapp.models import JobStatus
from matanyone2.webapp.services.masking import MaskingService


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

    class FakeController:
        def first_frame_click(self, image, points, labels, multimask=True):
            mask = np.zeros((image.shape[0], image.shape[1]), dtype=np.uint8)
            for x, y in points.tolist():
                mask[y, x] = 1
            return mask, np.zeros_like(mask, dtype=np.float32), Image.fromarray(image)

    app.state.masking_service = MaskingService(
        runtime_root=runtime_root,
        controller_factory=lambda: FakeController(),
    )
    with TestClient(app) as client:
        yield client


@pytest.fixture
def seeded_jobs(app_client):
    repository = app_client.app.state.repository
    first = repository.create_job(
        source_video_path="first.mp4",
        template_frame_index=0,
        mask_path="first.png",
        params_json="{}",
    )
    second = repository.create_job(
        source_video_path="second.mp4",
        template_frame_index=0,
        mask_path="second.png",
        params_json="{}",
    )
    repository.update_status(first.job_id, JobStatus.RUNNING)
    return first.job_id, second.job_id
