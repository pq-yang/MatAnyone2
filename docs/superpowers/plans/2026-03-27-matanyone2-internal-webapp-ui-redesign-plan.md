# MatAnyone2 Internal Web App UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the internal MatAnyone2 web app into a desktop-first post-production workbench with a professional upload flow, a staged multi-target annotation experience, and a preview-first results page.

**Architecture:** Keep the existing FastAPI + Jinja2 + vanilla JavaScript stack, but refactor the browser layer around a dedicated workbench state model instead of a single accumulating click session. Treat the redesign as a product and interaction rewrite on top of the current backend pipeline: fix the known API/state bugs first, then rebuild the upload shell, annotation workbench, and results review page with richer JSON contracts and page-specific controllers.

**Tech Stack:** Python 3.10+, FastAPI, Jinja2 templates, vanilla JavaScript modules, CSS custom properties, SQLite, pytest, Playwright smoke flow, existing SAM-backed masking service, existing internal webapp scripts

---

## File Structure

### Modify

- `D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\matanyone2\webapp\models.py`
  Expand annotation state from one flat click session into explicit target layers, active tool metadata, and richer page/result view models.
- `D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\matanyone2\webapp\services\masking.py`
  Reset click state between saved targets, add layer-aware preview helpers, and persist independent target metadata for the workbench.
- `D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\matanyone2\webapp\api\routes\uploads.py`
  Convert validation failures into user-facing 4xx responses and return richer upload metadata needed by the redesigned upload page.
- `D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\matanyone2\webapp\api\routes\annotation.py`
  Replace the current thin click/save/submit contract with a richer workbench API for stage changes, active target selection, and target-aware previews.
- `D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\matanyone2\webapp\api\routes\pages.py`
  Return 404 for missing jobs and pass richer template context for the redesigned upload, annotation, and results pages.
- `D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\matanyone2\webapp\templates\base.html`
  Introduce the desktop tool shell, status rail, font loading, and script/module entrypoints.
- `D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\matanyone2\webapp\templates\upload.html`
  Replace the plain upload form with the `New Session` layout and system/media summary cards.
- `D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\matanyone2\webapp\templates\annotate.html`
  Replace the current demo-like page with the three-column workbench layout, stage switcher, layer panel, and inspector panel.
- `D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\matanyone2\webapp\templates\job.html`
  Replace the link list page with a preview-first review surface that surfaces artifacts, warnings, and re-entry to annotation.
- `D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\matanyone2\webapp\static\styles.css`
  Rebuild the visual system using CSS variables, workstation panels, canvas layouts, and preview states.
- `D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\tests\webapp\test_api_flow.py`
  Extend request-level coverage for upload validation, richer page markup, layer actions, and result page contracts.
- `D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\tests\webapp\test_masking_service.py`
  Cover independent target saves, active-target resets, and merged multi-target export behavior.
- `D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\tests\webapp\test_smoke.py`
  Update smoke assertions for the redesigned page flow and richer workbench/result states.
- `D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\README.md`
  Document the redesigned UI workflow, keyboard controls, and updated smoke/launch expectations.

### Create

- `D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\matanyone2\webapp\static\shared.js`
  Shared browser helpers for JSON fetches, status messaging, DOM utilities, and cache-busting.
- `D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\matanyone2\webapp\static\upload.js`
  Upload-page controller for drag-and-drop, file metadata display, and transition into the workbench.
- `D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\matanyone2\webapp\static\workbench.js`
  Annotation workbench controller for stages, tool modes, target layers, canvas interactions, and submission.
- `D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\matanyone2\webapp\static\results.js`
  Results-page controller for polling, preview mode switching, artifact rendering, and warning presentation.
- `D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\tests\webapp\test_page_templates.py`
  Focused assertions for the new upload, workbench, and review HTML shells.

## Task 1: Fix Review Blockers And Establish Layer-Aware Annotation State

**Files:**
- Modify: `D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\matanyone2\webapp\models.py`
- Modify: `D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\matanyone2\webapp\services\masking.py`
- Modify: `D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\matanyone2\webapp\api\routes\uploads.py`
- Modify: `D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\matanyone2\webapp\api\routes\pages.py`
- Modify: `D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\tests\webapp\test_masking_service.py`
- Modify: `D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\tests\webapp\test_api_flow.py`

- [ ] **Step 1: Write failing tests for the three known blockers**

```python
def test_upload_validation_errors_return_400(app_client):
    response = app_client.post(
        "/api/uploads",
        files={"video": ("broken.mp4", b"not-a-video", "video/mp4")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "unable to read video frames"


def test_saved_masks_start_with_fresh_click_state(tmp_path):
    session = service.create_session(draft)
    service.apply_click(session, x=1, y=1, positive=True)
    service.save_current_mask(session)
    service.apply_click(session, x=8, y=8, positive=True)

    assert session.active_target.click_points == [(8, 8)]


def test_missing_job_page_returns_404(app_client):
    response = app_client.get("/jobs/missing-job")

    assert response.status_code == 404
```

- [ ] **Step 2: Run only the blocker-focused tests**

Run: `.\.venv\Scripts\python.exe -m pytest tests\webapp\test_masking_service.py tests\webapp\test_api_flow.py -q`

Expected: FAIL for upload validation, independent target clicks, and missing job 404 behavior.

- [ ] **Step 3: Refactor the session model and route error handling**

```python
@dataclass(slots=True)
class AnnotationTarget:
    name: str
    click_points: list[tuple[int, int]] = field(default_factory=list)
    click_labels: list[int] = field(default_factory=list)
    mask_path: Path | None = None
    preview_path: Path | None = None


def upload_video(...):
    try:
        draft = video_service.create_draft_from_upload(video)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def job_page(...):
    try:
        job = repository.get_job(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="job not found") from exc
```

Implementation notes:
- Replace the single `click_points` / `click_labels` fields on `DraftSession` with an explicit active target record.
- `save_current_mask()` must persist the current target and then reset the active target click state before the next target starts.
- Keep merged export behavior unchanged for now: multiple targets still combine into one merged mask when submitted.

- [ ] **Step 4: Re-run the focused tests and then the full webapp suite**

Run: `.\.venv\Scripts\python.exe -m pytest tests\webapp -q`

Expected: PASS, with the blocker regressions covered and the prior suite still green.

- [ ] **Step 5: Commit the stabilization pass**

```bash
git add matanyone2/webapp/models.py matanyone2/webapp/services/masking.py matanyone2/webapp/api/routes/uploads.py matanyone2/webapp/api/routes/pages.py tests/webapp/test_masking_service.py tests/webapp/test_api_flow.py
git commit -m "fix: stabilize webapp review blockers"
```

## Task 2: Introduce Rich Workbench API Contracts

**Files:**
- Modify: `D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\matanyone2\webapp\models.py`
- Modify: `D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\matanyone2\webapp\services\masking.py`
- Modify: `D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\matanyone2\webapp\api\routes\annotation.py`
- Modify: `D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\tests\webapp\test_api_flow.py`

- [ ] **Step 1: Write failing tests for workbench-state endpoints**

```python
def test_annotation_page_exposes_workbench_contract(app_client, sample_video_upload):
    draft_id = app_client.post("/api/uploads", files={"video": sample_video_upload}).json()["draft_id"]

    response = app_client.get(f"/drafts/{draft_id}/annotate")

    assert 'data-workbench-endpoint="/api/drafts/' in response.text
    assert 'data-targets-endpoint="/api/drafts/' in response.text


def test_target_creation_and_selection_round_trip(app_client, sample_video_upload):
    draft_id = app_client.post("/api/uploads", files={"video": sample_video_upload}).json()["draft_id"]

    created = app_client.post(f"/api/drafts/{draft_id}/targets", json={"name": "Hero"}).json()
    selected = app_client.post(
        f"/api/drafts/{draft_id}/targets/{created['target_id']}/select"
    ).json()

    assert created["name"] == "Hero"
    assert selected["active_target_id"] == created["target_id"]
```

- [ ] **Step 2: Run the API-flow tests to confirm the current contract is insufficient**

Run: `.\.venv\Scripts\python.exe -m pytest tests\webapp\test_api_flow.py -q`

Expected: FAIL because the workbench endpoints and target-selection JSON do not exist yet.

- [ ] **Step 3: Add workbench JSON models and endpoints**

```python
class DraftTargetPayload(BaseModel):
    target_id: str
    name: str
    point_count: int
    visible: bool
    locked: bool


@router.get("/api/drafts/{draft_id}")
def get_workbench_state(...):
    return {
        "draft_id": draft_id,
        "stage": session.stage,
        "active_target_id": session.active_target_id,
        "targets": [...],
    }


@router.post("/api/drafts/{draft_id}/targets")
def create_target(...):
    ...


@router.post("/api/drafts/{draft_id}/targets/{target_id}/select")
def select_target(...):
    ...
```

Implementation notes:
- Keep the current click/save/submit endpoints, but change their responses to include refreshed workbench state so the browser no longer has to infer state from the DOM.
- Add stage-change support even if the first implementation only records `coarse`, `refine`, and `preview` without algorithmic differences.
- Every target returned to the browser must carry stable ids, names, visibility, and selection state.

- [ ] **Step 4: Re-run the API tests and a smoke subset**

Run: `.\.venv\Scripts\python.exe -m pytest tests\webapp\test_api_flow.py tests\webapp\test_smoke.py -q`

Expected: PASS, proving the new workbench contract is available without breaking smoke expectations.

- [ ] **Step 5: Commit the workbench API layer**

```bash
git add matanyone2/webapp/models.py matanyone2/webapp/services/masking.py matanyone2/webapp/api/routes/annotation.py tests/webapp/test_api_flow.py
git commit -m "feat: add workbench annotation state api"
```

## Task 3: Rebuild The Shared Shell And Upload Page

**Files:**
- Modify: `D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\matanyone2\webapp\templates\base.html`
- Modify: `D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\matanyone2\webapp\templates\upload.html`
- Modify: `D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\matanyone2\webapp\static\styles.css`
- Create: `D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\matanyone2\webapp\static\shared.js`
- Create: `D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\matanyone2\webapp\static\upload.js`
- Create: `D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\tests\webapp\test_page_templates.py`
- Modify: `D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\tests\webapp\test_api_flow.py`

- [ ] **Step 1: Write failing template tests for the new upload shell**

```python
def test_upload_page_renders_new_session_shell(app_client):
    response = app_client.get("/")

    assert 'class="app-shell"' in response.text
    assert 'data-page="upload"' in response.text
    assert 'id="dropzone-panel"' in response.text
    assert 'id="media-info-card"' in response.text
```

- [ ] **Step 2: Run the upload-page tests and confirm the old markup fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests\webapp\test_page_templates.py tests\webapp\test_api_flow.py -q`

Expected: FAIL because the current upload page still renders a plain form and loads the legacy monolithic script.

- [ ] **Step 3: Implement the shell, design tokens, and upload controller**

```html
<body data-page="upload">
  <div class="app-shell">
    <header class="topbar">...</header>
    <main class="page upload-page">...</main>
  </div>
  <script type="module" src="/static/upload.js"></script>
</body>
```

```js
export function bindUploadPage(root) {
  const fileInput = root.querySelector("#video-file");
  const infoCard = root.querySelector("#media-info-card");
  ...
}
```

Implementation notes:
- Use CSS variables for the workstation palette, panel elevations, spacing, and semantic colors before styling any page-specific components.
- The upload page must expose system readiness, file metadata, and output expectations in three clear panels.
- Keep the upload action progressive: file selection updates metadata immediately, the primary CTA transitions into the annotation workbench after the draft is created.

- [ ] **Step 4: Re-run page/template tests plus the upload flow test**

Run: `.\.venv\Scripts\python.exe -m pytest tests\webapp\test_page_templates.py tests\webapp\test_api_flow.py -q`

Expected: PASS with the new upload shell and upload-to-annotate transition intact.

- [ ] **Step 5: Commit the shell and upload redesign**

```bash
git add matanyone2/webapp/templates/base.html matanyone2/webapp/templates/upload.html matanyone2/webapp/static/styles.css matanyone2/webapp/static/shared.js matanyone2/webapp/static/upload.js tests/webapp/test_page_templates.py tests/webapp/test_api_flow.py
git commit -m "feat: redesign internal webapp upload shell"
```

## Task 4: Build The Annotation Workbench UI

**Files:**
- Modify: `D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\matanyone2\webapp\templates\annotate.html`
- Modify: `D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\matanyone2\webapp\static\styles.css`
- Modify: `D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\matanyone2\webapp\static\shared.js`
- Create: `D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\matanyone2\webapp\static\workbench.js`
- Modify: `D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\tests\webapp\test_page_templates.py`
- Modify: `D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\tests\webapp\test_api_flow.py`

- [ ] **Step 1: Write failing tests for the new workbench structure**

```python
def test_annotation_page_renders_workbench_layout(app_client, sample_video_upload):
    draft_id = app_client.post("/api/uploads", files={"video": sample_video_upload}).json()["draft_id"]

    response = app_client.get(f"/drafts/{draft_id}/annotate")

    assert 'class="workbench-shell"' in response.text
    assert 'id="tool-rail"' in response.text
    assert 'id="canvas-stage"' in response.text
    assert 'id="layer-panel"' in response.text
    assert 'id="inspector-panel"' in response.text
```

- [ ] **Step 2: Run the annotation template and API tests**

Run: `.\.venv\Scripts\python.exe -m pytest tests\webapp\test_page_templates.py tests\webapp\test_api_flow.py tests\webapp\test_masking_service.py -q`

Expected: FAIL because the current page still renders the demo controls and cannot drive layered workbench state.

- [ ] **Step 3: Implement the three-column workbench and modular browser controller**

```js
const STAGES = ["coarse", "refine", "preview"];

function renderTargets(targets, activeTargetId) {
  ...
}

function setStage(stage) {
  state.stage = stage;
  root.dataset.stage = stage;
}
```

Implementation notes:
- The left rail should own tool mode switches only; do not scatter annotation actions across the page.
- The center column should expose stage tabs, canvas controls, and view modes (`source`, `overlay`, `alpha`) without mixing them into the right inspector.
- The right panel should manage targets, current tool settings, history, and contextual help.
- Default to hiding stale click markers when the stage changes out of coarse mode so the canvas stays readable.

- [ ] **Step 4: Re-run annotation-focused tests and a browser smoke**

Run: `.\.venv\Scripts\python.exe -m pytest tests\webapp\test_page_templates.py tests\webapp\test_api_flow.py tests\webapp\test_masking_service.py -q`

Run: `.\.venv\Scripts\python.exe scripts\smoke_internal_webapp.py --copies 1`

Expected: PASS for the test suite, and the smoke run reaches the redesigned annotate page and submits a job successfully.

- [ ] **Step 5: Commit the annotation workbench**

```bash
git add matanyone2/webapp/templates/annotate.html matanyone2/webapp/static/styles.css matanyone2/webapp/static/shared.js matanyone2/webapp/static/workbench.js tests/webapp/test_page_templates.py tests/webapp/test_api_flow.py tests/webapp/test_masking_service.py
git commit -m "feat: rebuild annotation workbench ui"
```

## Task 5: Rebuild The Results Review Page

**Files:**
- Modify: `D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\matanyone2\webapp\templates\job.html`
- Modify: `D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\matanyone2\webapp\static\styles.css`
- Modify: `D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\matanyone2\webapp\static\shared.js`
- Create: `D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\matanyone2\webapp\static\results.js`
- Modify: `D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\tests\webapp\test_page_templates.py`
- Modify: `D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\tests\webapp\test_api_flow.py`

- [ ] **Step 1: Write failing tests for the preview-first results page**

```python
def test_job_page_renders_review_viewport(app_client):
    job = app_client.app.state.repository.create_job(
        source_video_path="queued.mp4",
        template_frame_index=0,
        mask_path="queued.png",
        params_json="{}",
    )

    response = app_client.get(f"/jobs/{job.job_id}")

    assert 'id="preview-viewport"' in response.text
    assert 'id="preview-mode-tabs"' in response.text
    assert 'id="artifact-panel"' in response.text
```

- [ ] **Step 2: Run the results-page tests and confirm the old page fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests\webapp\test_page_templates.py tests\webapp\test_api_flow.py -q`

Expected: FAIL because the current results page only renders status text and a plain artifact list.

- [ ] **Step 3: Implement the review layout and results controller**

```js
const PREVIEW_MODES = ["source", "overlay", "alpha", "foreground"];

function renderArtifacts(artifacts) {
  ...
}

function applyStatus(payload) {
  statusNode.textContent = payload.status;
  warningNode.textContent = payload.warning_text || payload.error_text || "";
}
```

Implementation notes:
- Keep status polling, but move the primary emphasis to the preview surface and mode tabs.
- Surface warnings separately from normal status so `completed_with_warning` reads clearly.
- Preserve the existing artifact download routes; the results page is a redesign of presentation, not the transport layer.

- [ ] **Step 4: Re-run the results tests and end-to-end smoke**

Run: `.\.venv\Scripts\python.exe -m pytest tests\webapp\test_page_templates.py tests\webapp\test_api_flow.py tests\webapp\test_smoke.py -q`

Expected: PASS with the redesigned results page still showing downloads and terminal states correctly.

- [ ] **Step 5: Commit the review page**

```bash
git add matanyone2/webapp/templates/job.html matanyone2/webapp/static/styles.css matanyone2/webapp/static/shared.js matanyone2/webapp/static/results.js tests/webapp/test_page_templates.py tests/webapp/test_api_flow.py tests/webapp/test_smoke.py
git commit -m "feat: redesign result review page"
```

## Task 6: Refresh Documentation, Smoke Coverage, And Final Verification

**Files:**
- Modify: `D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\README.md`
- Modify: `D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\tests\webapp\test_smoke.py`
- Modify: `D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\scripts\smoke_internal_webapp.py`

- [ ] **Step 1: Write failing tests for the redesigned smoke expectations**

```python
def test_poll_jobs_accepts_completed_with_warning():
    statuses = poll_jobs(...)
    assert statuses["job-1"]["status"] in {"completed", "completed_with_warning"}
```

- [ ] **Step 2: Run smoke-related tests before adjusting docs/scripts**

Run: `.\.venv\Scripts\python.exe -m pytest tests\webapp\test_smoke.py tests\webapp\test_service_scripts.py -q`

Expected: FAIL or require updates because the redesigned pages expose new selectors, labels, and status expectations.

- [ ] **Step 3: Update smoke helpers and README for the new UI workflow**

```markdown
1. Launch the desktop workstation shell with `scripts/start_internal_webapp.ps1`.
2. Create a draft from the upload page.
3. Build one or more targets in the annotation workbench.
4. Review `source / overlay / alpha / foreground` before downloading artifacts.
```

Implementation notes:
- Keep the smoke runner CLI stable if possible; prefer extending selectors and assertions over changing the operator-facing command.
- Document the keyboard shortcuts introduced by the workbench (`V`, `P`, `N`, `B`, `E`, `[`, `]`, `Ctrl+Z`).
- Update the README screenshots and wording only after the implementation is verified.

- [ ] **Step 4: Run the full verification set**

Run: `.\.venv\Scripts\python.exe -m pytest tests\webapp -q`

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_inference_utils.py -q`

Run: `.\.venv\Scripts\python.exe -m compileall matanyone2\webapp scripts\run_internal_webapp.py scripts\run_internal_worker.py scripts\smoke_internal_webapp.py`

Expected: PASS, with the redesigned UI fully covered and no regressions in the inference utility patch.

- [ ] **Step 5: Commit docs and smoke updates**

```bash
git add README.md tests/webapp/test_smoke.py scripts/smoke_internal_webapp.py
git commit -m "docs: update webapp redesign workflow"
```

## Manual Review Checklist

- [ ] Upload page reads like an internal tool entrypoint, not a raw form.
- [ ] Annotation page keeps the canvas visually dominant at 1920x1080.
- [ ] Saving one target does not pollute the next target's clicks.
- [ ] `coarse`, `refine`, and `preview` stages are obvious without reading code.
- [ ] Results page makes `source / overlay / alpha / foreground` easy to compare.
- [ ] Warning states are visually distinct from success states.
- [ ] The smoke flow still completes on the `.venv` CUDA environment.
