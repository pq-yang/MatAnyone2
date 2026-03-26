from matanyone2.webapp.repository import JobRepository


class QueueCoordinator:
    def __init__(self, repository: JobRepository):
        self.repository = repository

    def recover_interrupted_jobs(self) -> None:
        self.repository.mark_running_jobs_interrupted()

    def next_job_id(self) -> str | None:
        next_job = self.repository.next_queued_job()
        return None if next_job is None else next_job.job_id
