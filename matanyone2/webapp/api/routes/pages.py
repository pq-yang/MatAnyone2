from fastapi import APIRouter, Depends, HTTPException, Request

from matanyone2.webapp.api.dependencies import get_draft_store, get_repository


router = APIRouter()


@router.get("/")
def upload_page(request: Request):
    templates = request.app.state.templates
    return templates.TemplateResponse(request, "upload.html")


def _workspace_context(draft_id: str, session):
    return {
        "draft_id": draft_id,
        "draft": session.draft,
        "saved_masks": sorted(session.saved_masks),
        "latest_job_id": session.latest_job_id,
    }


@router.get("/drafts/{draft_id}/workspace")
def workspace_page(request: Request, draft_id: str, draft_store=Depends(get_draft_store)):
    session = draft_store.get(draft_id)
    if session is None:
        raise HTTPException(status_code=404, detail="draft not found")
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "workspace.html",
        _workspace_context(draft_id, session),
    )


@router.get("/drafts/{draft_id}/annotate")
def annotate_page(request: Request, draft_id: str, draft_store=Depends(get_draft_store)):
    session = draft_store.get(draft_id)
    if session is None:
        raise HTTPException(status_code=404, detail="draft not found")
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "workspace.html",
        _workspace_context(draft_id, session),
    )


@router.get("/jobs/{job_id}")
def job_page(request: Request, job_id: str, repository=Depends(get_repository)):
    templates = request.app.state.templates
    try:
        job = repository.get_job(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="job not found") from exc
    return templates.TemplateResponse(request, "job.html", {"job": job})
