from datetime import UTC, datetime
from pathlib import Path
import sqlite3
import uuid

from matanyone2.webapp.db import connect, init_database
from matanyone2.webapp.models import JobRecord, JobStatus


class JobRepository:
    def __init__(self, database_path: Path):
        self.database_path = database_path
        init_database(database_path)

    @classmethod
    def from_path(cls, database_path: Path) -> "JobRepository":
        return cls(database_path=Path(database_path))

    def create_job(
        self,
        *,
        source_video_path: str,
        template_frame_index: int,
        mask_path: str,
        params_json: str,
    ) -> JobRecord:
        job = JobRecord(
            job_id=uuid.uuid4().hex,
            status=JobStatus.QUEUED,
            source_video_path=source_video_path,
            mask_path=mask_path,
            template_frame_index=template_frame_index,
            params_json=params_json,
            warning_text=None,
            error_text=None,
        )
        with connect(self.database_path) as connection:
            connection.execute(
                """
                INSERT INTO jobs (
                    job_id,
                    status,
                    source_video_path,
                    mask_path,
                    template_frame_index,
                    params_json,
                    warning_text,
                    error_text,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job.job_id,
                    job.status.value,
                    job.source_video_path,
                    job.mask_path,
                    job.template_frame_index,
                    job.params_json,
                    job.warning_text,
                    job.error_text,
                    datetime.now(UTC).isoformat(),
                ),
            )
            connection.commit()
        return job

    def get_job(self, job_id: str) -> JobRecord:
        with connect(self.database_path) as connection:
            row = connection.execute(
                """
                SELECT job_id, status, source_video_path, mask_path, template_frame_index,
                       params_json, warning_text, error_text
                FROM jobs
                WHERE job_id = ?
                """,
                (job_id,),
            ).fetchone()
        if row is None:
            raise KeyError(job_id)
        return self._row_to_job(row)

    def get_queue_position(self, job_id: str) -> int:
        with connect(self.database_path) as connection:
            row = connection.execute(
                """
                SELECT COUNT(*)
                FROM jobs AS q
                WHERE q.status = ?
                  AND q.created_at <= (
                      SELECT created_at
                      FROM jobs
                      WHERE job_id = ?
                  )
                """,
                (JobStatus.QUEUED.value, job_id),
            ).fetchone()
        return int(row[0])

    def update_status(
        self,
        job_id: str,
        status: JobStatus,
        *,
        warning_text: str | None = None,
        error_text: str | None = None,
    ) -> None:
        with connect(self.database_path) as connection:
            connection.execute(
                """
                UPDATE jobs
                SET status = ?, warning_text = ?, error_text = ?
                WHERE job_id = ?
                """,
                (status.value, warning_text, error_text, job_id),
            )
            connection.commit()

    def mark_running_jobs_interrupted(self) -> None:
        with connect(self.database_path) as connection:
            connection.execute(
                "UPDATE jobs SET status = ? WHERE status = ?",
                (JobStatus.INTERRUPTED.value, JobStatus.RUNNING.value),
            )
            connection.commit()

    def next_queued_job(self) -> JobRecord | None:
        with connect(self.database_path) as connection:
            row = connection.execute(
                """
                SELECT job_id, status, source_video_path, mask_path, template_frame_index,
                       params_json, warning_text, error_text
                FROM jobs
                WHERE status = ?
                ORDER BY created_at ASC
                LIMIT 1
                """,
                (JobStatus.QUEUED.value,),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_job(row)

    @staticmethod
    def _row_to_job(row: sqlite3.Row) -> JobRecord:
        return JobRecord(
            job_id=row["job_id"],
            status=JobStatus(row["status"]),
            source_video_path=row["source_video_path"],
            mask_path=row["mask_path"],
            template_frame_index=row["template_frame_index"],
            params_json=row["params_json"],
            warning_text=row["warning_text"],
            error_text=row["error_text"],
        )
