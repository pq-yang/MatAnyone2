from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from matanyone2.webapp.api.dependencies import get_repository, get_settings


router = APIRouter()


def _artifact_urls(job_id: str, runtime_root: Path) -> dict[str, str]:
    job_dir = Path(runtime_root) / "jobs" / job_id
    artifact_names = [
        "foreground.mp4",
        "alpha.mp4",
        "rgba_png.zip",
        "output_prores4444.mov",
    ]
    artifacts = {}
    for artifact_name in artifact_names:
        artifact_path = job_dir / artifact_name
        if artifact_path.exists():
            artifacts[artifact_name] = f"/api/jobs/{job_id}/artifacts/{artifact_name}"
    return artifacts


@router.get("/api/jobs/{job_id}")
def get_job_status(
    job_id: str,
    repository=Depends(get_repository),
    settings=Depends(get_settings),
):
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
        "artifacts": _artifact_urls(job.job_id, settings.runtime_root),
    }


@router.get("/api/jobs/{job_id}/artifacts/{artifact_name}")
def download_artifact(
    job_id: str,
    artifact_name: str,
    repository=Depends(get_repository),
    settings=Depends(get_settings),
):
    try:
        repository.get_job(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="job not found") from exc

    artifact_path = Path(settings.runtime_root) / "jobs" / job_id / artifact_name
    if not artifact_path.exists() or not artifact_path.is_file():
        raise HTTPException(status_code=404, detail="artifact not found")
    return FileResponse(path=artifact_path, filename=artifact_name)
