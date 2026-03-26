import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from matanyone2.webapp.api.dependencies import (
    get_draft_store,
    get_masking_service,
    get_repository,
)


class DraftClickPayload(BaseModel):
    x: int
    y: int
    positive: bool = True


class DraftSubmitPayload(BaseModel):
    template_frame_index: int
    selected_masks: list[str]


class DraftTargetCreatePayload(BaseModel):
    name: str | None = None


class DraftStagePayload(BaseModel):
    stage: str


router = APIRouter()


def _require_session(draft_store, draft_id: str):
    session = draft_store.get(draft_id)
    if session is None:
        raise HTTPException(status_code=404, detail="draft not found")
    return session


def _target_payload(target, session):
    return {
        "target_id": target.target_id,
        "name": target.name,
        "point_count": len(target.click_points),
        "visible": target.visible,
        "locked": target.locked,
        "saved_mask_name": target.saved_mask_name,
        "selected": target.target_id == session.active_target_id,
    }


def _workbench_payload(session, draft_id: str):
    return {
        "draft_id": draft_id,
        "stage": session.stage,
        "active_target_id": session.active_target_id,
        "template_frame_url": f"/api/drafts/{draft_id}/template-frame",
        "current_mask_url": (
            f"/api/drafts/{draft_id}/current-mask"
            if session.current_mask_path is not None
            else None
        ),
        "current_preview_url": (
            f"/api/drafts/{draft_id}/current-preview"
            if session.current_preview_path is not None
            else None
        ),
        "mask_names": sorted(session.saved_masks),
        "targets": [
            _target_payload(target, session)
            for target in session.targets.values()
        ],
    }


@router.get("/api/drafts/{draft_id}")
def get_workbench_state(draft_id: str, draft_store=Depends(get_draft_store)):
    session = _require_session(draft_store, draft_id)
    return _workbench_payload(session, draft_id)


@router.post("/api/drafts/{draft_id}/targets")
def create_target(
    draft_id: str,
    payload: DraftTargetCreatePayload,
    draft_store=Depends(get_draft_store),
    masking_service=Depends(get_masking_service),
):
    session = _require_session(draft_store, draft_id)
    target = masking_service.create_target(session, name=payload.name)
    response = _workbench_payload(session, draft_id)
    response.update(_target_payload(target, session))
    return response


@router.post("/api/drafts/{draft_id}/targets/{target_id}/select")
def select_target(
    draft_id: str,
    target_id: str,
    draft_store=Depends(get_draft_store),
    masking_service=Depends(get_masking_service),
):
    session = _require_session(draft_store, draft_id)
    try:
        masking_service.select_target(session, target_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"target not found: {target_id}") from exc
    return _workbench_payload(session, draft_id)


@router.post("/api/drafts/{draft_id}/stage")
def set_stage(
    draft_id: str,
    payload: DraftStagePayload,
    draft_store=Depends(get_draft_store),
    masking_service=Depends(get_masking_service),
):
    session = _require_session(draft_store, draft_id)
    try:
        masking_service.set_stage(session, payload.stage)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _workbench_payload(session, draft_id)


@router.post("/api/drafts/{draft_id}/click")
def apply_click(
    draft_id: str,
    payload: DraftClickPayload,
    draft_store=Depends(get_draft_store),
    masking_service=Depends(get_masking_service),
):
    session = _require_session(draft_store, draft_id)
    result = masking_service.apply_click(
        session,
        x=payload.x,
        y=payload.y,
        positive=payload.positive,
    )
    response = _workbench_payload(session, draft_id)
    response.update(
        {
        "current_mask_path": str(result.current_mask_path),
        "current_preview_path": str(result.current_preview_path),
        "current_mask_url": f"/api/drafts/{draft_id}/current-mask",
        "current_preview_url": f"/api/drafts/{draft_id}/current-preview",
        }
    )
    return response


@router.post("/api/drafts/{draft_id}/masks")
def save_mask(
    draft_id: str,
    draft_store=Depends(get_draft_store),
    masking_service=Depends(get_masking_service),
):
    session = _require_session(draft_store, draft_id)
    try:
        mask_name = masking_service.save_current_mask(session)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    response = _workbench_payload(session, draft_id)
    response.update({"mask_name": mask_name})
    return response


@router.post("/api/drafts/{draft_id}/submit")
def submit_draft(
    draft_id: str,
    payload: DraftSubmitPayload,
    draft_store=Depends(get_draft_store),
    masking_service=Depends(get_masking_service),
    repository=Depends(get_repository),
):
    session = _require_session(draft_store, draft_id)
    try:
        mask_path = masking_service.write_merged_mask(session, payload.selected_masks)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"unknown mask: {exc.args[0]}") from exc

    job = repository.create_job(
        source_video_path=str(session.draft.video_path),
        template_frame_index=payload.template_frame_index,
        mask_path=str(mask_path),
        params_json=json.dumps(
            {
                "template_frame_index": payload.template_frame_index,
                "selected_masks": payload.selected_masks,
            }
        ),
    )
    return {"job_id": job.job_id, "status": job.status.value}


@router.get("/api/drafts/{draft_id}/current-preview")
def get_current_preview(draft_id: str, draft_store=Depends(get_draft_store)):
    session = _require_session(draft_store, draft_id)
    if session.current_preview_path is None:
        raise HTTPException(status_code=404, detail="current preview not found")
    return FileResponse(
        session.current_preview_path,
        media_type="image/png",
        filename=session.current_preview_path.name,
    )


@router.get("/api/drafts/{draft_id}/current-mask")
def get_current_mask(draft_id: str, draft_store=Depends(get_draft_store)):
    session = _require_session(draft_store, draft_id)
    if session.current_mask_path is None:
        raise HTTPException(status_code=404, detail="current mask not found")
    return FileResponse(
        session.current_mask_path,
        media_type="image/png",
        filename=session.current_mask_path.name,
    )
