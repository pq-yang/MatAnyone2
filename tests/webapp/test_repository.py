from matanyone2.webapp.models import JobStatus
from matanyone2.webapp.repository import JobRepository


def test_repository_creates_job_and_reports_queue_position(tmp_path):
    repo = JobRepository.from_path(tmp_path / "jobs.db")
    first = repo.create_job(
        source_video_path="a.mp4",
        template_frame_index=0,
        mask_path="a.png",
        params_json="{}",
    )
    second = repo.create_job(
        source_video_path="b.mp4",
        template_frame_index=0,
        mask_path="b.png",
        params_json="{}",
    )

    assert repo.get_job(first.job_id).status is JobStatus.QUEUED
    assert repo.get_queue_position(second.job_id) == 2
