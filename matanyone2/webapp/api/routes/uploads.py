from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from matanyone2.webapp.api.dependencies import (
    get_draft_store,
    get_masking_service,
    get_video_service,
)


router = APIRouter()


@router.post("/api/uploads")
def upload_video(
    video: UploadFile = File(...),
    video_service=Depends(get_video_service),
    draft_store=Depends(get_draft_store),
    masking_service=Depends(get_masking_service),
):
    draft = video_service.create_draft_from_upload(video)
    draft_store[draft.draft_id] = masking_service.create_session(draft)
    return {
        "draft_id": draft.draft_id,
        "template_frame_url": f"/api/drafts/{draft.draft_id}/template-frame",
    }


@router.get("/api/drafts/{draft_id}/template-frame")
def get_template_frame(
    draft_id: str,
    draft_store=Depends(get_draft_store),
):
    session = draft_store.get(draft_id)
    if session is None:
        raise HTTPException(status_code=404, detail="draft not found")
    return FileResponse(
        session.draft.template_frame_path,
        media_type="image/png",
        filename=session.draft.template_frame_path.name,
    )
