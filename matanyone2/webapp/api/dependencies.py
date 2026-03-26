from fastapi import Request


def get_settings(request: Request):
    return request.app.state.settings


def get_repository(request: Request):
    return request.app.state.repository


def get_queue(request: Request):
    return request.app.state.queue


def get_video_service(request: Request):
    return request.app.state.video_service


def get_draft_store(request: Request):
    return request.app.state.drafts


def get_masking_service(request: Request):
    return request.app.state.masking_service
