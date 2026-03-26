from fastapi import APIRouter, Depends, Request

from matanyone2.webapp.api.dependencies import get_repository


router = APIRouter()


@router.get("/")
def upload_page(request: Request):
    templates = request.app.state.templates
    return templates.TemplateResponse("upload.html", {"request": request})


@router.get("/jobs/{job_id}")
def job_page(request: Request, job_id: str, repository=Depends(get_repository)):
    templates = request.app.state.templates
    job = repository.get_job(job_id)
    return templates.TemplateResponse("job.html", {"request": request, "job": job})
