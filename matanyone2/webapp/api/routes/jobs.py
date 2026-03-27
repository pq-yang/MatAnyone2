import json
from pathlib import Path

import mimetypes

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from matanyone2.webapp.api.dependencies import (
    get_repository,
    get_settings,
    get_video_service,
)
from matanyone2.webapp.models import JobStatus


router = APIRouter()


ARTIFACT_SPECS = (
    ("foreground.mp4", "Foreground pass", "foreground"),
    ("alpha.mp4", "Alpha matte", "alpha"),
    ("rgba_png.zip", "RGBA PNG sequence", "png_sequence"),
    ("output_prores4444.mov", "ProRes 4444", "prores"),
)

PREVIEW_ARTIFACT_SPECS = (
    ("foreground", "preview_foreground.mp4"),
    ("alpha", "preview_alpha.mp4"),
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
    selected_mask_presets = params.get("selected_mask_presets")
    if not isinstance(selected_mask_presets, dict):
        selected_mask_presets = {}

    process_start_frame_index = params.get("process_start_frame_index")
    process_end_frame_index = params.get("process_end_frame_index")
    process_range_duration_seconds = params.get("process_range_duration_seconds")
    source_fps = params.get("source_fps")

    return {
        "source_name": Path(job.source_video_path).name,
        "template_frame_index": params.get(
            "template_frame_index",
            job.template_frame_index,
        ),
        "process_start_frame_index": process_start_frame_index,
        "process_end_frame_index": process_end_frame_index,
        "process_range_duration_seconds": process_range_duration_seconds,
        "source_fps": source_fps,
        "selected_mask_count": len(selected_masks),
        "selected_masks": selected_masks,
        "selected_mask_presets": selected_mask_presets,
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


def _build_preview_payload(job_id: str, runtime_root: Path) -> dict[str, str]:
    job_dir = Path(runtime_root) / "jobs" / job_id
    preview_artifacts: dict[str, str] = {}
    for preview_kind, artifact_name in PREVIEW_ARTIFACT_SPECS:
        artifact_path = job_dir / artifact_name
        if artifact_path.exists() and artifact_path.is_file():
            preview_artifacts[preview_kind] = f"/api/jobs/{job_id}/artifacts/{artifact_name}"
    return preview_artifacts


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
        "preview_artifacts": _build_preview_payload(job.job_id, settings.runtime_root),
        "artifact_details": artifact_details,
        "job_summary": _build_job_summary(job),
        "timeline": _build_timeline(job.status),
    }


@router.get("/api/jobs/{job_id}/source-video")
def get_source_video(
    job_id: str,
    repository=Depends(get_repository),
    settings=Depends(get_settings),
    video_service=Depends(get_video_service),
):
    try:
        job = repository.get_job(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="job not found") from exc

    params = _parse_job_params(job.params_json)
    job_dir = Path(settings.runtime_root) / "jobs" / job.job_id
    source_path = Path(job.source_video_path)
    if not source_path.exists() or not source_path.is_file():
        raise HTTPException(status_code=404, detail="source video not found")

    processing_range_start = params.get("process_start_frame_index")
    processing_range_end = params.get("process_end_frame_index")
    clip_source_path = source_path
    preview_path = None

    if (
        isinstance(processing_range_start, int)
        and isinstance(processing_range_end, int)
        and processing_range_start >= 0
        and processing_range_end >= processing_range_start
    ):
        clip_candidate = job_dir / "processing_range.mp4"
        if clip_candidate.exists() and clip_candidate.is_file():
            clip_source_path = clip_candidate
        else:
            try:
                clip_source_path, _ = video_service.write_processing_range_clip(
                    source_path,
                    start_frame_index=processing_range_start,
                    end_frame_index=processing_range_end,
                    output_path=clip_candidate,
                )
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc

        preview_candidate = job_dir / "preview_source.mp4"
        if preview_candidate.exists() and preview_candidate.is_file():
            preview_path = preview_candidate
        else:
            try:
                preview_path = video_service.ensure_browser_preview(
                    clip_source_path,
                    preview_path=preview_candidate,
                )
            except RuntimeError:
                preview_path = None
    else:
        try:
            preview_path = video_service.ensure_browser_preview(
                source_path,
                preview_path=source_path.parent / "preview_source.mp4",
            )
        except RuntimeError:
            preview_path = None

    serving_path = preview_path or clip_source_path
    return FileResponse(
        path=serving_path,
        filename=serving_path.name,
        media_type=mimetypes.guess_type(serving_path.name)[0] or "video/mp4",
    )


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
