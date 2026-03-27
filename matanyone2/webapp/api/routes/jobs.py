import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from matanyone2.webapp.api.dependencies import get_repository, get_settings
from matanyone2.webapp.models import JobStatus


router = APIRouter()


ARTIFACT_SPECS = (
    ("foreground.mp4", "Foreground pass", "foreground"),
    ("alpha.mp4", "Alpha matte", "alpha"),
    ("rgba_png.zip", "RGBA PNG sequence", "png_sequence"),
    ("output_prores4444.mov", "ProRes 4444", "prores"),
)

TIMELINE_STEPS = (
    ("queued", "Queued"),
    ("preparing", "Preparing"),
    ("running", "Matting"),
    ("exporting", "Export"),
)

TIMELINE_STATE_INDEX = {
    JobStatus.QUEUED: 0,
    JobStatus.PREPARING: 1,
    JobStatus.RUNNING: 2,
    JobStatus.EXPORTING: 3,
    JobStatus.COMPLETED: 3,
    JobStatus.COMPLETED_WITH_WARNING: 3,
    JobStatus.FAILED: 2,
    JobStatus.INTERRUPTED: 2,
}


def _format_status_label(status: JobStatus) -> str:
    return status.value.replace("_", " ").capitalize()


def _format_bytes(size_bytes: int | None) -> str | None:
    if size_bytes is None:
        return None
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    if size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def _parse_job_params(params_json: str) -> dict:
    try:
        payload = json.loads(params_json)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _build_timeline(status: JobStatus) -> list[dict[str, str]]:
    current_index = TIMELINE_STATE_INDEX[status]
    timeline = []
    for index, (key, label) in enumerate(TIMELINE_STEPS):
        if index < current_index:
            state = "complete"
        elif index == current_index:
            state = "current"
        else:
            state = "upcoming"
        timeline.append({"key": key, "label": label, "state": state})
    return timeline


def _build_job_summary(job) -> dict[str, object]:
    params = _parse_job_params(job.params_json)
    selected_masks = params.get("selected_masks")
    if not isinstance(selected_masks, list):
        selected_masks = []

    return {
        "source_name": Path(job.source_video_path).name,
        "template_frame_index": params.get(
            "template_frame_index",
            job.template_frame_index,
        ),
        "selected_mask_count": len(selected_masks),
        "selected_masks": selected_masks,
        "mask_name": Path(job.mask_path).name,
    }


def _build_artifact_payload(job_id: str, runtime_root: Path) -> tuple[dict[str, str], dict[str, dict[str, object]]]:
    job_dir = Path(runtime_root) / "jobs" / job_id
    artifacts: dict[str, str] = {}
    artifact_details: dict[str, dict[str, object]] = {}

    for artifact_name, label, kind in ARTIFACT_SPECS:
        artifact_path = job_dir / artifact_name
        available = artifact_path.exists() and artifact_path.is_file()
        url = f"/api/jobs/{job_id}/artifacts/{artifact_name}" if available else None
        size_bytes = artifact_path.stat().st_size if available else None
        if available and url is not None:
            artifacts[artifact_name] = url
        artifact_details[artifact_name] = {
            "name": artifact_name,
            "label": label,
            "kind": kind,
            "available": available,
            "url": url,
            "size_bytes": size_bytes,
            "size_label": _format_bytes(size_bytes),
        }
    return artifacts, artifact_details


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
    artifacts, artifact_details = _build_artifact_payload(job.job_id, settings.runtime_root)
    return {
        "job_id": job.job_id,
        "status": job.status.value,
        "status_label": _format_status_label(job.status),
        "queue_position": queue_position,
        "warning_text": job.warning_text,
        "error_text": job.error_text,
        "source_video_url": f"/api/jobs/{job.job_id}/source-video",
        "artifacts": artifacts,
        "artifact_details": artifact_details,
        "job_summary": _build_job_summary(job),
        "timeline": _build_timeline(job.status),
    }


@router.get("/api/jobs/{job_id}/source-video")
def get_source_video(
    job_id: str,
    repository=Depends(get_repository),
):
    try:
        job = repository.get_job(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="job not found") from exc

    source_path = Path(job.source_video_path)
    if not source_path.exists() or not source_path.is_file():
        raise HTTPException(status_code=404, detail="source video not found")
    return FileResponse(path=source_path, filename=source_path.name)


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
