from fastapi import APIRouter, Depends, HTTPException

from matanyone2.webapp.api.dependencies import get_repository


router = APIRouter()


@router.get("/api/jobs/{job_id}")
def get_job_status(job_id: str, repository=Depends(get_repository)):
    try:
        job = repository.get_job(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="job not found") from exc
    queue_position = (
        repository.get_queue_position(job.job_id)
        if job.status.value == "queued"
        else None
    )
    return {
        "job_id": job.job_id,
        "status": job.status.value,
        "queue_position": queue_position,
    }
