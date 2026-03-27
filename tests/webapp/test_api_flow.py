import json

from fastapi.testclient import TestClient
from matanyone2.webapp.models import JobStatus


def test_upload_page_exposes_browser_entrypoint(app_client: TestClient):
    response = app_client.get("/")

    assert response.status_code == 200
    assert 'id="upload-form"' in response.text
    assert 'data-upload-endpoint="/api/uploads"' in response.text
    assert "/static/upload.js" in response.text


def test_submit_flow_keeps_workspace_in_review_state(
    app_client: TestClient,
    sample_video_upload,
):
    upload_response = app_client.post(
        "/api/uploads",
        files={"video": sample_video_upload},
    )
    assert upload_response.status_code == 200
    draft_id = upload_response.json()["draft_id"]
    template_frame_url = upload_response.json()["template_frame_url"]

    template_response = app_client.get(template_frame_url)
    workspace_page = app_client.get(f"/drafts/{draft_id}/workspace")

    assert template_response.status_code == 200
    assert template_response.headers["content-type"] == "image/png"
    assert workspace_page.status_code == 200
    assert draft_id in workspace_page.text

    click_response = app_client.post(
        f"/api/drafts/{draft_id}/click",
        json={"x": 1, "y": 1, "positive": True},
    )
    assert click_response.status_code == 200
    current_preview_url = click_response.json()["current_preview_url"]
    preview_response = app_client.get(current_preview_url)

    assert preview_response.status_code == 200
    assert preview_response.headers["content-type"] == "image/png"
    assert 'id="workspace-app"' in workspace_page.text
    assert f'data-click-endpoint="/api/drafts/{draft_id}/click"' in workspace_page.text
    assert "/static/workspace.js" in workspace_page.text

    save_response = app_client.post(f"/api/drafts/{draft_id}/masks")
    assert save_response.status_code == 200
    assert save_response.json()["mask_name"] == "mask_001"

    annotate_response = app_client.post(
        f"/api/drafts/{draft_id}/submit",
        json={
            "process_start_frame_index": 0,
            "process_end_frame_index": 2,
            "template_frame_index": 0,
            "selected_masks": ["mask_001"],
        },
    )

    assert annotate_response.status_code == 200
    assert annotate_response.json()["status"] == "queued"
    assert annotate_response.json()["workflow_step"] == "review"
    state_response = app_client.get(f"/api/drafts/{draft_id}")
    assert state_response.status_code == 200
    assert state_response.json()["workflow_step"] == "review"
    assert state_response.json()["latest_job_id"] == annotate_response.json()["job_id"]


def test_submit_persists_selected_mask_presets_in_job_params(
    app_client: TestClient,
    sample_video_upload,
):
    upload_response = app_client.post(
        "/api/uploads",
        files={"video": sample_video_upload},
    )
    draft_id = upload_response.json()["draft_id"]

    app_client.patch(
        f"/api/drafts/{draft_id}/targets/target-001",
        json={"refine_preset": "hair"},
    )
    app_client.post(
        f"/api/drafts/{draft_id}/click",
        json={"x": 1, "y": 1, "positive": True},
    )
    app_client.post(f"/api/drafts/{draft_id}/masks")
    submit_response = app_client.post(
        f"/api/drafts/{draft_id}/submit",
        json={
            "process_start_frame_index": 0,
            "process_end_frame_index": 2,
            "template_frame_index": 0,
            "selected_masks": ["mask_001"],
        },
    )

    repository = app_client.app.state.repository
    job = repository.get_job(submit_response.json()["job_id"])
    params = json.loads(job.params_json)

    assert submit_response.status_code == 200
    assert params["selected_mask_presets"] == {"mask_001": "hair"}
    assert params["selected_mask_controls"]["mask_001"]["edge_feather_radius"] == 0.0


def test_annotation_page_exposes_workbench_contract(
    app_client: TestClient,
    sample_video_upload,
):
    upload_response = app_client.post(
        "/api/uploads",
        files={"video": sample_video_upload},
    )
    draft_id = upload_response.json()["draft_id"]

    response = app_client.get(f"/drafts/{draft_id}/workspace")

    assert response.status_code == 200
    assert f'data-workbench-endpoint="/api/drafts/{draft_id}"' in response.text
    assert f'data-workflow-step-endpoint="/api/drafts/{draft_id}/workflow-step"' in response.text
    assert f'data-targets-endpoint="/api/drafts/{draft_id}/targets"' in response.text
    assert f'data-brush-endpoint="/api/drafts/{draft_id}/brush"' in response.text
    assert 'id="workflow-stepper"' in response.text
    assert 'id="workspace-sidebar-tabs"' in response.text
    assert 'id="workspace-timeline-dock"' in response.text


def test_target_creation_and_selection_round_trip(
    app_client: TestClient,
    sample_video_upload,
):
    upload_response = app_client.post(
        "/api/uploads",
        files={"video": sample_video_upload},
    )
    draft_id = upload_response.json()["draft_id"]

    state_response = app_client.get(f"/api/drafts/{draft_id}")
    create_response = app_client.post(
        f"/api/drafts/{draft_id}/targets",
        json={"name": "Hero"},
    )
    created = create_response.json()
    select_response = app_client.post(
        f"/api/drafts/{draft_id}/targets/{created['target_id']}/select"
    )
    selected = select_response.json()

    assert state_response.status_code == 200
    assert state_response.json()["stage"] == "coarse"
    assert state_response.json()["active_target_id"] is not None
    assert create_response.status_code == 200
    assert created["name"] == "Hero"
    assert any(target["name"] == "Hero" for target in created["targets"])
    assert select_response.status_code == 200
    assert selected["active_target_id"] == created["target_id"]
    assert any(
        target["target_id"] == created["target_id"] and target["selected"]
        for target in selected["targets"]
    )


def test_target_update_round_trip(
    app_client: TestClient,
    sample_video_upload,
):
    upload_response = app_client.post(
        "/api/uploads",
        files={"video": sample_video_upload},
    )
    draft_id = upload_response.json()["draft_id"]

    create_response = app_client.post(
        f"/api/drafts/{draft_id}/targets",
        json={"name": "Hero"},
    )
    target_id = create_response.json()["target_id"]

    update_response = app_client.patch(
        f"/api/drafts/{draft_id}/targets/{target_id}",
        json={
            "name": "Lead Actor",
            "visible": False,
            "locked": True,
            "refine_preset": "hair",
        },
    )

    assert update_response.status_code == 200
    payload = update_response.json()
    assert payload["active_target_id"] == target_id
    assert payload["can_apply_clicks"] is False
    assert any(
        target["target_id"] == target_id
        and target["name"] == "Lead Actor"
        and target["visible"] is False
        and target["locked"] is True
        and target["refine_preset"] == "hair"
        for target in payload["targets"]
    )


def test_target_update_round_trip_includes_numeric_refine_controls(
    app_client: TestClient,
    sample_video_upload,
):
    upload_response = app_client.post(
        "/api/uploads",
        files={"video": sample_video_upload},
    )
    draft_id = upload_response.json()["draft_id"]

    update_response = app_client.patch(
        f"/api/drafts/{draft_id}/targets/target-001",
        json={
            "refine_preset": "hair",
            "preset_strength": 0.85,
            "motion_strength": 0.55,
            "temporal_stability": 0.7,
            "edge_feather_radius": 9.0,
        },
    )

    assert update_response.status_code == 200
    payload = update_response.json()
    active_target = next(
        target for target in payload["targets"] if target["target_id"] == payload["active_target_id"]
    )
    assert active_target["preset_strength"] == 0.85
    assert active_target["motion_strength"] == 0.55
    assert active_target["temporal_stability"] == 0.7
    assert active_target["edge_feather_radius"] == 9.0


def test_template_frame_selection_round_trip(
    app_client: TestClient,
    sample_video_upload,
):
    upload_response = app_client.post(
        "/api/uploads",
        files={"video": sample_video_upload},
    )
    draft_id = upload_response.json()["draft_id"]

    initial_state = app_client.get(f"/api/drafts/{draft_id}").json()
    update_response = app_client.post(
        f"/api/drafts/{draft_id}/template-frame",
        json={"frame_index": 2},
    )

    assert initial_state["template_frame_index"] == 0
    assert initial_state["frame_count"] == 3
    assert update_response.status_code == 200
    assert update_response.json()["template_frame_index"] == 2
    assert update_response.json()["template_frame_url"] == f"/api/drafts/{draft_id}/template-frame"


def test_workbench_exposes_source_video_scrubber_contract(
    app_client: TestClient,
    sample_video_upload,
):
    upload_response = app_client.post(
        "/api/uploads",
        files={"video": sample_video_upload},
    )
    draft_id = upload_response.json()["draft_id"]

    state_response = app_client.get(f"/api/drafts/{draft_id}")
    payload = state_response.json()
    video_response = app_client.get(payload["source_video_url"])

    assert state_response.status_code == 200
    assert payload["source_video_url"] == f"/api/drafts/{draft_id}/source-video"
    assert payload["fps"] == 3.0
    assert payload["duration_seconds"] == 1.0
    assert payload["process_start_frame_index"] == 0
    assert payload["process_end_frame_index"] == 2
    assert payload["workflow_step"] == "clip"
    assert payload["available_steps"] == ["clip", "mask", "refine", "review"]
    assert payload["can_go_back"] is False
    assert payload["can_go_next"] is True
    assert payload["active_sidebar_tab"] == "targets"
    assert payload["compare_enabled"] is False
    assert payload["latest_job_id"] is None
    assert payload["can_apply_range"] is True
    assert payload["can_apply_template_frame"] is True
    assert video_response.status_code == 200
    assert video_response.headers["content-type"].startswith("video/")


def test_workflow_step_navigation_round_trip(
    app_client: TestClient,
    sample_video_upload,
):
    upload_response = app_client.post(
        "/api/uploads",
        files={"video": sample_video_upload},
    )
    draft_id = upload_response.json()["draft_id"]

    refine_response = app_client.post(
        f"/api/drafts/{draft_id}/workflow-step",
        json={"workflow_step": "refine"},
    )
    clip_response = app_client.post(
        f"/api/drafts/{draft_id}/workflow-step",
        json={"workflow_step": "clip"},
    )

    assert refine_response.status_code == 200
    assert refine_response.json()["workflow_step"] == "refine"
    assert refine_response.json()["can_go_back"] is True
    assert refine_response.json()["can_go_next"] is True
    assert refine_response.json()["active_sidebar_tab"] == "refine"
    assert clip_response.status_code == 200
    assert clip_response.json()["workflow_step"] == "clip"
    assert clip_response.json()["can_go_back"] is False
    assert clip_response.json()["active_sidebar_tab"] == "targets"


def test_processing_range_update_clears_existing_anchor_and_masks(
    app_client: TestClient,
    sample_video_upload,
):
    upload_response = app_client.post(
        "/api/uploads",
        files={"video": sample_video_upload},
    )
    draft_id = upload_response.json()["draft_id"]

    app_client.post(
        f"/api/drafts/{draft_id}/click",
        json={"x": 1, "y": 1, "positive": True},
    )
    app_client.post(f"/api/drafts/{draft_id}/masks")

    response = app_client.post(
        f"/api/drafts/{draft_id}/processing-range",
        json={"start_frame_index": 1, "end_frame_index": 2},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["process_start_frame_index"] == 1
    assert payload["process_end_frame_index"] == 2
    assert payload["template_frame_index"] is None
    assert payload["mask_names"] == []
    assert payload["selected_mask_names"] == []
    assert payload["current_mask_url"] is None
    assert payload["current_preview_url"] is None
    assert payload["stage"] == "coarse"
    assert payload["can_apply_clicks"] is False
    assert payload["can_submit"] is False
    assert payload["can_apply_template_frame"] is True


def test_template_frame_must_fall_inside_processing_range(
    app_client: TestClient,
    sample_video_upload,
):
    upload_response = app_client.post(
        "/api/uploads",
        files={"video": sample_video_upload},
    )
    draft_id = upload_response.json()["draft_id"]
    app_client.post(
        f"/api/drafts/{draft_id}/processing-range",
        json={"start_frame_index": 1, "end_frame_index": 2},
    )

    response = app_client.post(
        f"/api/drafts/{draft_id}/template-frame",
        json={"frame_index": 0},
    )

    assert response.status_code == 400
    assert "processing range" in response.json()["detail"]


def test_submit_requires_anchor_inside_processing_range(
    app_client: TestClient,
    sample_video_upload,
):
    upload_response = app_client.post(
        "/api/uploads",
        files={"video": sample_video_upload},
    )
    draft_id = upload_response.json()["draft_id"]

    app_client.post(
        f"/api/drafts/{draft_id}/processing-range",
        json={"start_frame_index": 1, "end_frame_index": 2},
    )
    app_client.post(
        f"/api/drafts/{draft_id}/template-frame",
        json={"frame_index": 1},
    )
    app_client.post(
        f"/api/drafts/{draft_id}/click",
        json={"x": 1, "y": 1, "positive": True},
    )
    app_client.post(f"/api/drafts/{draft_id}/masks")

    response = app_client.post(
        f"/api/drafts/{draft_id}/submit",
        json={
            "process_start_frame_index": 1,
            "process_end_frame_index": 2,
            "template_frame_index": 0,
            "selected_masks": ["mask_001"],
        },
    )

    assert response.status_code == 400
    assert "processing range" in response.json()["detail"]


def test_draft_source_video_endpoint_prefers_browser_preview(app_client: TestClient, sample_video_upload):
    upload_response = app_client.post(
        "/api/uploads",
        files={"video": sample_video_upload},
    )
    draft_id = upload_response.json()["draft_id"]
    session = app_client.app.state.drafts[draft_id]
    preview_path = session.draft.video_path.parent / "preview_source.mp4"
    preview_path.write_bytes(b"preview-source")
    session.draft.browser_preview_path = preview_path

    response = app_client.get(f"/api/drafts/{draft_id}/source-video")

    assert response.status_code == 200
    assert response.content == b"preview-source"


def test_job_status_exposes_browser_preview_artifacts(
    app_client: TestClient,
):
    repository = app_client.app.state.repository
    runtime_root = app_client.app.state.settings.runtime_root
    job = repository.create_job(
        source_video_path="queued.mp4",
        template_frame_index=0,
        mask_path="queued.png",
        params_json="{}",
    )
    job_dir = runtime_root / "jobs" / job.job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / "preview_foreground.mp4").write_bytes(b"preview-fg")
    (job_dir / "preview_alpha.mp4").write_bytes(b"preview-alpha")

    response = app_client.get(f"/api/jobs/{job.job_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["preview_artifacts"]["foreground"] == f"/api/jobs/{job.job_id}/artifacts/preview_foreground.mp4"
    assert payload["preview_artifacts"]["alpha"] == f"/api/jobs/{job.job_id}/artifacts/preview_alpha.mp4"


def test_target_preset_change_rebuilds_current_mask_preview(
    app_client: TestClient,
    sample_video_upload,
):
    upload_response = app_client.post(
        "/api/uploads",
        files={"video": sample_video_upload},
    )
    draft_id = upload_response.json()["draft_id"]

    app_client.post(
        f"/api/drafts/{draft_id}/click",
        json={"x": 1, "y": 1, "positive": True},
    )
    initial_mask = app_client.get(f"/api/drafts/{draft_id}/current-mask").content

    update_response = app_client.patch(
        f"/api/drafts/{draft_id}/targets/target-001",
        json={"refine_preset": "hair"},
    )
    updated_mask = app_client.get(f"/api/drafts/{draft_id}/current-mask").content

    assert update_response.status_code == 200
    assert update_response.json()["current_mask_url"] is not None
    assert update_response.json()["current_preview_url"] is not None
    assert updated_mask != initial_mask


def test_temporal_stability_change_rebuilds_current_mask_render(
    app_client: TestClient,
    sample_video_upload,
):
    upload_response = app_client.post(
        "/api/uploads",
        files={"video": sample_video_upload},
    )
    draft_id = upload_response.json()["draft_id"]

    app_client.post(
        f"/api/drafts/{draft_id}/click",
        json={"x": 1, "y": 1, "positive": True},
    )
    initial_mask = app_client.get(f"/api/drafts/{draft_id}/current-mask").content

    update_response = app_client.patch(
        f"/api/drafts/{draft_id}/targets/target-001",
        json={"temporal_stability": 1.0},
    )
    updated_mask = app_client.get(f"/api/drafts/{draft_id}/current-mask").content

    assert update_response.status_code == 200
    assert update_response.json()["current_mask_url"] is not None
    assert update_response.json()["current_preview_url"] is not None
    assert updated_mask != initial_mask


def test_stage_change_round_trip(
    app_client: TestClient,
    sample_video_upload,
):
    upload_response = app_client.post(
        "/api/uploads",
        files={"video": sample_video_upload},
    )
    draft_id = upload_response.json()["draft_id"]

    response = app_client.post(
        f"/api/drafts/{draft_id}/stage",
        json={"stage": "refine"},
    )
    preview_response = app_client.post(
        f"/api/drafts/{draft_id}/stage",
        json={"stage": "preview"},
    )

    assert response.status_code == 200
    assert response.json()["stage"] == "refine"
    assert response.json()["stage_label"] == "Edge Refinement"
    assert response.json()["can_apply_clicks"] is True
    assert response.json()["can_create_target"] is True
    assert preview_response.status_code == 200
    assert preview_response.json()["stage"] == "preview"
    assert preview_response.json()["stage_label"] == "Preview"
    assert preview_response.json()["can_apply_clicks"] is False
    assert preview_response.json()["can_create_target"] is False


def test_preview_stage_locks_save_and_brush_actions(
    app_client: TestClient,
    sample_video_upload,
):
    upload_response = app_client.post(
        "/api/uploads",
        files={"video": sample_video_upload},
    )
    draft_id = upload_response.json()["draft_id"]

    app_client.post(
        f"/api/drafts/{draft_id}/click",
        json={"x": 1, "y": 1, "positive": True},
    )
    preview_response = app_client.post(
        f"/api/drafts/{draft_id}/stage",
        json={"stage": "preview"},
    )
    brush_response = app_client.post(
        f"/api/drafts/{draft_id}/brush",
        json={"mode": "add", "radius": 20, "points": [[2, 2]]},
    )

    assert preview_response.status_code == 200
    assert preview_response.json()["can_save_current_target"] is False
    assert brush_response.status_code == 400
    assert brush_response.json()["detail"] == "preview mode is read-only"


def test_brush_round_trip_updates_current_mask_preview(
    app_client: TestClient,
    sample_video_upload,
):
    upload_response = app_client.post(
        "/api/uploads",
        files={"video": sample_video_upload},
    )
    draft_id = upload_response.json()["draft_id"]

    response = app_client.post(
        f"/api/drafts/{draft_id}/brush",
        json={"mode": "add", "radius": 20, "points": [[2, 2], [3, 3]]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["current_mask_url"] is not None
    assert payload["current_preview_url"] is not None
    assert payload["can_save_current_target"] is True


def test_saved_mask_is_selected_for_export_and_unlocks_submit(
    app_client: TestClient,
    sample_video_upload,
):
    upload_response = app_client.post(
        "/api/uploads",
        files={"video": sample_video_upload},
    )
    draft_id = upload_response.json()["draft_id"]

    app_client.post(
        f"/api/drafts/{draft_id}/click",
        json={"x": 1, "y": 1, "positive": True},
    )
    save_response = app_client.post(f"/api/drafts/{draft_id}/masks")
    state_response = app_client.get(f"/api/drafts/{draft_id}")

    assert save_response.status_code == 200
    assert save_response.json()["mask_name"] == "mask_001"
    assert save_response.json()["selected_mask_names"] == ["mask_001"]
    assert save_response.json()["can_submit"] is True
    assert save_response.json()["active_mask_url"].endswith(
        f"/api/drafts/{draft_id}/masks/mask_001"
    )
    assert state_response.status_code == 200
    assert state_response.json()["selected_mask_names"] == ["mask_001"]
    assert state_response.json()["active_mask_url"].endswith(
        f"/api/drafts/{draft_id}/masks/mask_001"
    )


def test_saved_mask_endpoint_serves_named_mask(
    app_client: TestClient,
    sample_video_upload,
):
    upload_response = app_client.post(
        "/api/uploads",
        files={"video": sample_video_upload},
    )
    draft_id = upload_response.json()["draft_id"]

    app_client.post(
        f"/api/drafts/{draft_id}/click",
        json={"x": 1, "y": 1, "positive": True},
    )
    app_client.post(f"/api/drafts/{draft_id}/masks")

    response = app_client.get(f"/api/drafts/{draft_id}/masks/mask_001")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"


def test_undo_click_and_reset_target_round_trip(
    app_client: TestClient,
    sample_video_upload,
):
    upload_response = app_client.post(
        "/api/uploads",
        files={"video": sample_video_upload},
    )
    draft_id = upload_response.json()["draft_id"]

    app_client.post(
        f"/api/drafts/{draft_id}/click",
        json={"x": 1, "y": 1, "positive": True},
    )
    app_client.post(
        f"/api/drafts/{draft_id}/click",
        json={"x": 2, "y": 2, "positive": False},
    )

    undo_response = app_client.post(f"/api/drafts/{draft_id}/undo")
    reset_response = app_client.post(f"/api/drafts/{draft_id}/reset-target")

    assert undo_response.status_code == 200
    assert undo_response.json()["targets"][0]["point_count"] == 1
    assert undo_response.json()["current_preview_url"] is not None
    assert reset_response.status_code == 200
    assert reset_response.json()["targets"][0]["point_count"] == 0
    assert reset_response.json()["current_preview_url"] is None


def test_upload_validation_errors_return_400(app_client: TestClient):
    with TestClient(app_client.app, raise_server_exceptions=False) as client:
        response = client.post(
            "/api/uploads",
            files={"video": ("broken.mp4", b"not-a-video", "video/mp4")},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "unable to read video frames"


def test_second_job_waits_until_first_job_finishes(app_client, seeded_jobs):
    first_job_id, second_job_id = seeded_jobs

    first_status = app_client.get(f"/api/jobs/{first_job_id}").json()
    second_status = app_client.get(f"/api/jobs/{second_job_id}").json()

    assert first_status["status"] == "running"
    assert second_status["status"] == "queued"
    assert second_status["queue_position"] == 1


def test_job_page_exposes_polling_entrypoint(app_client):
    repository = app_client.app.state.repository
    job = repository.create_job(
        source_video_path="queued.mp4",
        template_frame_index=0,
        mask_path="queued.png",
        params_json="{}",
    )

    response = app_client.get(f"/jobs/{job.job_id}")

    assert response.status_code == 200
    assert 'id="job-app"' in response.text
    assert f'data-status-endpoint="/api/jobs/{job.job_id}"' in response.text
    assert f'data-source-video-endpoint="/api/jobs/{job.job_id}/source-video"' in response.text
    assert 'id="preview-viewport"' in response.text
    assert 'id="preview-mode-tabs"' in response.text
    assert 'id="artifact-panel"' in response.text
    assert "/static/results.js" in response.text


def test_job_source_video_endpoint_serves_source_file(app_client):
    runtime_root = app_client.app.state.settings.runtime_root
    source_path = runtime_root / "jobs" / "source.mp4"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_bytes(b"video-bytes")

    repository = app_client.app.state.repository
    job = repository.create_job(
        source_video_path=str(source_path),
        template_frame_index=0,
        mask_path="queued.png",
        params_json="{}",
    )

    response = app_client.get(f"/api/jobs/{job.job_id}/source-video")

    assert response.status_code == 200
    assert response.content == b"video-bytes"


def test_job_source_video_endpoint_prefers_browser_preview_when_present(app_client):
    runtime_root = app_client.app.state.settings.runtime_root
    source_dir = runtime_root / "jobs" / "source-preview"
    source_dir.mkdir(parents=True, exist_ok=True)
    source_path = source_dir / "source.mp4"
    preview_path = source_dir / "preview_source.mp4"
    source_path.write_bytes(b"video-bytes")
    preview_path.write_bytes(b"preview-video-bytes")

    repository = app_client.app.state.repository
    job = repository.create_job(
        source_video_path=str(source_path),
        template_frame_index=0,
        mask_path="queued.png",
        params_json="{}",
    )

    response = app_client.get(f"/api/jobs/{job.job_id}/source-video")

    assert response.status_code == 200
    assert response.content == b"preview-video-bytes"


def test_job_source_video_endpoint_prefers_processing_range_preview_when_present(app_client):
    runtime_root = app_client.app.state.settings.runtime_root
    source_dir = runtime_root / "jobs" / "source-range-preview"
    source_dir.mkdir(parents=True, exist_ok=True)
    source_path = source_dir / "source.mp4"
    source_preview_path = source_dir / "preview_source.mp4"
    source_path.write_bytes(b"video-bytes")
    source_preview_path.write_bytes(b"full-preview-bytes")

    repository = app_client.app.state.repository
    job = repository.create_job(
        source_video_path=str(source_path),
        template_frame_index=1,
        mask_path="queued.png",
        params_json='{"process_start_frame_index": 1, "process_end_frame_index": 2}',
    )

    job_dir = runtime_root / "jobs" / job.job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / "processing_range.mp4").write_bytes(b"clip-bytes")
    (job_dir / "preview_source.mp4").write_bytes(b"range-preview-bytes")

    response = app_client.get(f"/api/jobs/{job.job_id}/source-video")

    assert response.status_code == 200
    assert response.content == b"range-preview-bytes"


def test_missing_job_page_returns_404(app_client: TestClient):
    with TestClient(app_client.app, raise_server_exceptions=False) as client:
        response = client.get("/jobs/missing-job")

    assert response.status_code == 404
    assert response.json()["detail"] == "job not found"


def test_completed_job_exposes_artifacts_and_downloads_zip(app_client):
    repository = app_client.app.state.repository
    runtime_root = app_client.app.state.settings.runtime_root
    job = repository.create_job(
        source_video_path="finished.mp4",
        template_frame_index=0,
        mask_path="finished.png",
        params_json="{}",
    )
    repository.update_status(job.job_id, JobStatus.COMPLETED)

    job_dir = runtime_root / "jobs" / job.job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = job_dir / "rgba_png.zip"
    artifact_path.write_bytes(b"zip")

    status_response = app_client.get(f"/api/jobs/{job.job_id}")
    download_response = app_client.get(
        f"/api/jobs/{job.job_id}/artifacts/rgba_png.zip"
    )

    assert status_response.status_code == 200
    assert status_response.json()["artifacts"]["rgba_png.zip"].endswith("rgba_png.zip")
    assert download_response.status_code == 200
    assert download_response.content == b"zip"


def test_job_status_exposes_warning_and_error_text(app_client):
    repository = app_client.app.state.repository
    warning_job = repository.create_job(
        source_video_path="warning.mp4",
        template_frame_index=0,
        mask_path="warning.png",
        params_json="{}",
    )
    failed_job = repository.create_job(
        source_video_path="failed.mp4",
        template_frame_index=0,
        mask_path="failed.png",
        params_json="{}",
    )

    repository.update_status(
        warning_job.job_id,
        JobStatus.COMPLETED_WITH_WARNING,
        warning_text="prores export skipped",
    )
    repository.update_status(
        failed_job.job_id,
        JobStatus.FAILED,
        error_text="gpu worker crashed",
    )

    warning_response = app_client.get(f"/api/jobs/{warning_job.job_id}")
    failed_response = app_client.get(f"/api/jobs/{failed_job.job_id}")

    assert warning_response.status_code == 200
    assert warning_response.json()["warning_text"] == "prores export skipped"
    assert warning_response.json()["error_text"] is None
    assert failed_response.status_code == 200
    assert failed_response.json()["warning_text"] is None
    assert failed_response.json()["error_text"] == "gpu worker crashed"


def test_job_status_exposes_review_summary_and_artifact_metadata(app_client):
    repository = app_client.app.state.repository
    runtime_root = app_client.app.state.settings.runtime_root
    source_path = runtime_root / "inputs" / "hero.mp4"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_bytes(b"source")

    job = repository.create_job(
        source_video_path=str(source_path),
        template_frame_index=12,
        mask_path="hero_mask.png",
        params_json='{"process_start_frame_index": 10, "process_end_frame_index": 20, "process_range_duration_seconds": 0.46, "template_frame_index": 12, "selected_masks": ["mask_001", "mask_002"], "selected_mask_presets": {"mask_001": "hair"}}',
    )
    repository.update_status(
        job.job_id,
        JobStatus.COMPLETED_WITH_WARNING,
        warning_text="prores export skipped",
    )

    job_dir = runtime_root / "jobs" / job.job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / "foreground.mp4").write_bytes(b"foreground-bytes")
    (job_dir / "alpha.mp4").write_bytes(b"alpha-bytes")
    (job_dir / "rgba_png.zip").write_bytes(b"zip-bytes")

    response = app_client.get(f"/api/jobs/{job.job_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status_label"] == "Completed with warning"
    assert payload["job_summary"]["source_name"] == "hero.mp4"
    assert payload["job_summary"]["template_frame_index"] == 12
    assert payload["job_summary"]["process_start_frame_index"] == 10
    assert payload["job_summary"]["process_end_frame_index"] == 20
    assert payload["job_summary"]["process_range_duration_seconds"] == 0.46
    assert payload["job_summary"]["selected_mask_count"] == 2
    assert payload["job_summary"]["selected_masks"] == ["mask_001", "mask_002"]
    assert payload["job_summary"]["selected_mask_presets"] == {"mask_001": "hair"}
    assert [step["state"] for step in payload["timeline"]] == [
        "complete",
        "complete",
        "complete",
        "current",
    ]
    assert payload["artifact_details"]["foreground.mp4"]["label"] == "Foreground pass"
    assert payload["artifact_details"]["foreground.mp4"]["size_bytes"] == len(b"foreground-bytes")
    assert payload["artifact_details"]["rgba_png.zip"]["kind"] == "png_sequence"
    assert payload["artifact_details"]["output_prores4444.mov"]["available"] is False
