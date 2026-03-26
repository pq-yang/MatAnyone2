import json

from fastapi import APIRouter, Depends, HTTPException
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


router = APIRouter()


@router.post("/api/drafts/{draft_id}/click")
def apply_click(
    draft_id: str,
    payload: DraftClickPayload,
    draft_store=Depends(get_draft_store),
    masking_service=Depends(get_masking_service),
):
    session = draft_store.get(draft_id)
    if session is None:
        raise HTTPException(status_code=404, detail="draft not found")
    result = masking_service.apply_click(
        session,
        x=payload.x,
        y=payload.y,
        positive=payload.positive,
    )
    return {
        "current_mask_path": str(result.current_mask_path),
        "current_preview_path": str(result.current_preview_path),
    }


@router.post("/api/drafts/{draft_id}/masks")
def save_mask(
    draft_id: str,
    draft_store=Depends(get_draft_store),
    masking_service=Depends(get_masking_service),
):
    session = draft_store.get(draft_id)
    if session is None:
        raise HTTPException(status_code=404, detail="draft not found")
    try:
        mask_name = masking_service.save_current_mask(session)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"mask_name": mask_name, "mask_names": sorted(session.saved_masks)}


@router.post("/api/drafts/{draft_id}/submit")
def submit_draft(
    draft_id: str,
    payload: DraftSubmitPayload,
    draft_store=Depends(get_draft_store),
    masking_service=Depends(get_masking_service),
    repository=Depends(get_repository),
):
    session = draft_store.get(draft_id)
    if session is None:
        raise HTTPException(status_code=404, detail="draft not found")
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
