from matanyone2.webapp.models import JobStatus
from matanyone2.webapp.queue import QueueCoordinator
from matanyone2.webapp.repository import JobRepository


def test_recover_running_jobs_marks_them_interrupted(tmp_path):
    repo = JobRepository.from_path(tmp_path / "jobs.db")
    job = repo.create_job(
        source_video_path="a.mp4",
        template_frame_index=0,
        mask_path="a.png",
        params_json="{}",
    )
    repo.update_status(job.job_id, JobStatus.RUNNING)

    coordinator = QueueCoordinator(repo)
    coordinator.recover_interrupted_jobs()

    assert repo.get_job(job.job_id).status is JobStatus.INTERRUPTED
