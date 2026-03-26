from pathlib import Path
import json

import numpy as np
from PIL import Image
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from matanyone2.webapp.api.dependencies import get_draft_store, get_repository


class DraftSubmitPayload(BaseModel):
    template_frame_index: int
    selected_masks: list[str]


router = APIRouter()


@router.post("/api/drafts/{draft_id}/submit")
def submit_draft(
    draft_id: str,
    payload: DraftSubmitPayload,
    draft_store=Depends(get_draft_store),
    repository=Depends(get_repository),
):
    draft = draft_store.get(draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="draft not found")

    frame = Image.open(draft.template_frame_path)
    mask_path = Path(draft.template_frame_path).with_name("merged_mask.png")
    Image.fromarray(
        np.full((frame.height, frame.width), 255, dtype=np.uint8),
        mode="L",
    ).save(mask_path)

    job = repository.create_job(
        source_video_path=str(draft.video_path),
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
