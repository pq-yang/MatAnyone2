# MatAnyone2 Internal Web App Design

**Date:** 2026-03-26

**Status:** Approved for planning

## Summary

Build a single-machine internal web application for short-form human video matting. The first version is a **semi-automatic high-quality tool**, not a zero-interaction platform.

Primary flow:

`upload source video -> choose template frame -> click one or more target people -> submit job -> queue -> generate results -> download transparent deliverables`

The system runs on a fixed internal machine and is optimized for internal testing on TVC and ad-style clips, typically up to 10 seconds at 1080p, on hardware with 128 GB RAM and an RTX 5090 32 GB GPU.

## Why This Scope Fits The Current Repository

The repository already proves the core matting path:

- Command-line inference takes a video plus a first-frame mask and writes both foreground and alpha outputs.
  - `README.md` states that each run requires a video and its first-frame segmentation mask.
  - `inference_matanyone2.py` loads `mask_path` and writes `*_fgr.mp4` and `*_pha.mp4`.
- The interactive demo already fills the missing mask-preparation step through SAM-based clicking on a chosen frame.
  - `hugging_face/app.py` handles point-click refinement, multi-mask collection, and matting execution.
- Device selection already supports CUDA, MPS, and CPU fallback.
  - `matanyone2/utils/device.py` selects the best available device.

The repository also shows why the first version should stay narrow:

- `matanyone2/utils/inference_utils.py` reads the full video into memory.
- `inference_matanyone2.py` and `hugging_face/matanyone2_wrapper.py` accumulate frame tensors and output arrays in memory.
- The demo is an interaction prototype, not a production-shaped web service.

This makes the current codebase a strong base for an internal tool, but not a drop-in zero-touch service.

## Product Goal

Create a stable internal web tool that allows a user to:

1. Upload a short source video.
2. Select a template frame.
3. Click one or more target people on that frame to create the initial mask.
4. Submit the task to a queue.
5. Download transparent deliverables after processing completes.

## Explicit Version 1 Scope

### In Scope

- Fixed internal machine deployment.
- Browser access over the internal network.
- No authentication.
- Single logical worker on one GPU.
- Multiple submitted jobs allowed, with queueing.
- One running inference job at a time.
- One uploaded video per job.
- One combined matte result per job, even when multiple people are selected.
- Template-frame selection before submission.
- Point-based mask creation and refinement on the selected frame.
- Foreground and alpha intermediate outputs.
- Transparent output delivery as:
  - `RGBA PNG` sequence
  - `RGBA PNG` zip package
  - optional `MOV ProRes 4444`
- Basic task status UI and download UI.
- Error messages visible in the web app.

### Out Of Scope

- Fully automatic subject detection or auto-selection.
- Account system, SSO, audit trail, or permission tiers.
- Multi-machine scheduling.
- High-concurrency production serving.
- Long-term result gallery or media asset management.
- Real-time preview while inference is running.
- Per-person separate output packages for multi-target jobs.
- Guaranteed support for long videos.

## Users And Usage Assumptions

- Users are internal testers, not external customers.
- Input videos are usually TVC or ad-style clips and usually no longer than 10 seconds.
- Quality matters more than throughput.
- Operators can tolerate a short wait, including queue wait time.
- Users need downloadable transparent assets for post-production workflows.

## Success Criteria

Version 1 is successful if it can reliably do the following on the target machine:

- Accept a 1080p clip around 10 seconds long.
- Let the user select one or more target people through clicks on a template frame.
- Queue the job instead of rejecting it when another job is already running.
- Generate a combined matte result for the selected targets.
- Produce downloadable transparent output as `RGBA PNG` sequence zip.
- Produce `foreground mp4` and `alpha mp4` for inspection and fallback.
- Optionally produce `MOV ProRes 4444` when export support is available.
- Show clear job state transitions and actionable failure messages.

## Product Definition

### Positioning

This is an internal **semi-automatic matting workstation** exposed through a web browser. It is not a batch automation system and not a general-purpose media processing platform.

### Core Output Contract

Each completed job produces:

- `foreground.mp4`
- `alpha.mp4`
- `rgba_png/` sequence
- `rgba_png.zip`
- optional `output_prores4444.mov`

Important distinction:

- `alpha.mp4` is an alpha-matte video, not the final transparent delivery format.
- `rgba_png.zip` is the primary version-1 delivery artifact.
- `output_prores4444.mov` is a best-effort enhanced export and must not block overall job success if the PNG export succeeded.

### Multi-Target Behavior

Version 1 supports selecting multiple people on the template frame, but all selected people are merged into one combined mask before inference submission. The job produces one combined output package, not separate outputs per person.

This matches the current repository direction more closely than a per-person export design and keeps the first implementation focused.

## User Experience And Page Flow

The UI should be a simple 3-step job flow rather than a large admin console.

### Step 1: Upload

The upload page allows the user to:

- upload one video
- see basic validation feedback
- inspect extracted metadata such as duration, fps, resolution, and file size
- proceed to frame selection and mask authoring

Validation should reject or stop early on:

- unsupported file format
- empty or unreadable video
- missing frames
- file too large for configured limits
- duration beyond the configured version-1 boundary

### Step 2: Mark Targets

The mask-authoring page allows the user to:

- choose the template frame
- add positive and negative points
- refine the first-frame mask
- add multiple masks
- see a merged mask preview
- confirm the final selection before submission

This interaction should reuse the behavior already proven in `hugging_face/app.py`, but the implementation should be extracted into service modules rather than reusing the Gradio event graph directly.

### Step 3: Queue, Status, And Download

After submission, the user lands on a task page that shows:

- job id
- current state
- queue position when queued
- timestamps
- warning state for partial export success
- final download links when complete

Recommended visible states:

- `queued`
- `preparing`
- `running`
- `exporting`
- `completed`
- `completed_with_warning`
- `failed`
- `interrupted`

## System Design

### Architecture Choice

Use a **single application with clear internal modules**, not multiple deployable services.

Recommended structure:

- Web/API layer
- Mask authoring service
- Job service
- Inference service
- Export service
- Worker process
- Runtime storage layer

This is intentionally more structured than the current Gradio demo but much lighter than a distributed system.

### Web/API Layer

Responsibilities:

- file upload
- request validation
- template-frame preview
- click/mask interaction endpoints
- job submission
- job status queries
- artifact downloads

This layer must never run long GPU inference inline inside the request/response cycle.

### Mask Authoring Service

Responsibilities:

- store click state
- call SAM-backed refinement
- manage multiple masks
- merge selected masks into one final template mask

This should be extracted from the current interaction logic in `hugging_face/app.py`.

### Job Service

Responsibilities:

- create job records
- assign job ids
- persist state transitions
- manage working directories
- expose queue position
- mark retries or reruns as new jobs

### Inference Service

Responsibilities:

- load the selected model
- read the submitted source video
- apply the final template mask
- run MatAnyone2 inference
- write intermediate results

This service should reuse the existing repository inference logic rather than rewriting the model path.

### Export Service

Responsibilities:

- combine foreground and alpha into `RGBA PNG` frames
- zip the PNG sequence
- optionally render `MOV ProRes 4444`
- expose export warnings separately from inference failures

### Worker Process

Use a separate worker process for GPU work.

Reasons:

- current inference paths can be memory-heavy
- isolated process failure is easier to recover from
- GPU memory cleanup is more predictable
- web responsiveness does not depend on inference timing

Only one inference worker should run at a time in version 1.

## Storage Design

Use a lightweight persistent local design:

- `SQLite` for job metadata and status
- per-job directories for inputs, outputs, parameters, and logs

Suggested runtime contents per job:

- original uploaded video
- selected template-frame index
- click history or final click payload
- final merged mask PNG
- parameter JSON
- processing log
- foreground output
- alpha output
- PNG sequence output
- zip archive
- optional ProRes output

This allows:

- queue persistence across web process restarts
- job inspection without reading application memory
- easy cleanup policies later
- future extension to a results page without redesigning storage

## Queue Behavior

Version 1 queue policy:

- allow multiple submissions
- run only one inference job at a time
- show waiting jobs as queued
- show queue order in the UI
- do not deduplicate matching uploads
- do not auto-cancel older jobs

If the server restarts:

- `queued` jobs remain queued
- `running` jobs become `interrupted`
- users can manually resubmit or rerun through a new job submission path later

## Processing Pipeline

### Draft Stage

- upload video
- read minimal metadata
- extract preview frame(s)
- collect click state and template frame choice
- generate final merged mask

### Submitted Job Stage

- persist source video and mask
- persist selected parameters
- create job row in the database
- enqueue the job

### Worker Stage

- move job to `preparing`
- initialize model and resources
- move job to `running`
- generate foreground and alpha outputs
- move job to `exporting`
- generate transparent deliverables
- move job to final status

## Export Rules

### Required Exports

Required for job success:

- `foreground.mp4`
- `alpha.mp4`
- `rgba_png.zip`

### Optional Export

Best-effort only:

- `output_prores4444.mov`

### Success Semantics

- If inference fails, the job fails.
- If PNG sequence generation fails, the job fails.
- If PNG succeeds but ProRes export fails, the job completes with warning.

This keeps the primary internal post-production path reliable while treating codec-specific export as an enhancement.

## Error Handling

### Validation Errors

Handled before queue submission:

- unreadable video
- no extracted frames
- no target selected
- invalid parameters
- unsupported file type
- configured duration or size limit exceeded

### Runtime Failures

Handled on the worker side:

- model load failure
- GPU or CUDA failure
- inference exception
- filesystem write failure
- export exception

The task page should show a clear, human-readable failure reason. Users should not need terminal access.

### Logging

Each job should write a processing log that captures:

- start and end timestamps
- model used
- template frame index
- selected parameters
- state transitions
- exception traceback on failure
- export warnings

## Non-Functional Requirements

- Stable on the target internal machine for short 1080p clips.
- Responsive web UI even when the worker is busy.
- Persistent queue and job metadata across normal web process restarts.
- Clean failure behavior without hanging the whole web process.
- No requirement for cloud dependencies.

## Technical Recommendation

Recommended implementation stack:

- `FastAPI` for the web/API server
- lightweight server-rendered or light SPA frontend
- `SQLite` for job and queue metadata
- separate worker process for inference and export
- `ffmpeg` for packaging and transparent video export

Avoid starting version 1 with a heavy frontend stack unless the UI requirements expand significantly. The difficult work here is inference orchestration and export reliability, not complex client state.

## Repository Impact

Do not keep layering product behavior directly into `hugging_face/app.py`.

Recommended repository direction:

- keep the existing demo as a demo
- extract reusable masking logic into service modules
- wrap inference into a service boundary
- add dedicated runtime, worker, and web modules for the internal app

This prevents the production-shaped path from being trapped inside a Gradio event graph.

## Risks And Boundaries

### Current Codebase Risk

The current repository is research-oriented and memory-heavy:

- full-video reads into memory
- in-memory tensor accumulation
- output arrays accumulated before final write

This is acceptable for version 1 on the target hardware and target clip length, but it must be treated as a boundary, not as proof that the design scales to longer clips or higher concurrency.

### Export Risk

`MOV ProRes 4444` depends on local `ffmpeg` capabilities and container/codec support. It should be implemented as an optional export profile and tested on the target machine before being treated as required.

### Product Boundary

The first version is intentionally a high-quality operator-assisted workflow. Any future goal of "upload and auto-pick the main person" is a separate project because it requires subject detection and selection logic not present as a stable product feature in the repository today.

## Recommended Delivery Order

Implementation should be planned in this order:

1. service-wrap inference so a video and merged mask can be submitted programmatically
2. add job persistence and single-worker queueing
3. add upload, status, and download API paths
4. add mask-authoring endpoints and UI
5. add PNG sequence export and zip packaging
6. add optional ProRes 4444 export
7. add integration tests and restart behavior checks

This order reduces risk by validating the core processing chain before investing in the full UI.

## Acceptance Checklist

The implementation plan should satisfy all of the following:

- one user can upload a short clip and finish a complete job in the browser
- another user can submit a second job while the first is running
- the second job waits in queue and later completes
- the user can select multiple people and receive one combined output package
- the primary downloadable output is an `RGBA PNG` zip package
- the system also preserves `foreground.mp4` and `alpha.mp4`
- the UI shows clear state transitions and clear failures
- a web-process restart does not silently lose queued jobs

## Decisions Locked By This Spec

- Version 1 is semi-automatic, not zero-interaction.
- Deployment target is one fixed internal machine.
- No authentication in version 1.
- Queueing is allowed and required.
- Multi-target jobs are supported, but merged into one output.
- Transparent delivery is required.
- `RGBA PNG` zip is the primary final artifact.
- `MOV ProRes 4444` is optional best-effort output.
- The existing Gradio demo is reference material, not the production host surface.
