# MatAnyone2 Standalone Desktop Workbench Design

## Goal

Build a standalone desktop application for internal MatAnyone2 testing that replaces the browser-centered UI with a native workbench optimized for clip selection, anchor selection, matte authoring, refinement, and result review.

## Why A Desktop App

The current browser workbench is constrained by page-style layout, browser media behavior, limited native navigation, and weak monitor ergonomics for detailed matte review. The user feedback is consistent:

- the monitor must remain dominant
- timeline interaction must feel like a source monitor, not a form
- returning between steps must be app-native, not browser-history based
- hair and edge refinement controls must stay near the main monitor and produce readable feedback

Those constraints fit a native desktop workbench better than a browser page stack.

## Product Direction

The first standalone version is a single-window desktop workbench with one persistent session surface:

- top step navigation: `Clip`, `Mask`, `Refine`, `Review`
- center monitor: the only primary preview surface
- bottom dock: compact timeline, in/out markers, and anchor rail
- left inspector: tabbed controls for targets, refinement, and export
- right side is removed from the main flow unless a transient sheet is needed

The app is optimized for `1920x1080+` desktop use with keyboard and mouse.

## Technical Stack

- Desktop shell: `PySide6`
- Video playback and scrubbing: `QMediaPlayer` and native Qt timeline controls
- Background jobs: Python worker threads over the existing MatAnyone2 services
- Existing reusable services:
  - `matanyone2.webapp.services.video`
  - `matanyone2.webapp.services.masking`
  - `matanyone2.webapp.services.inference`
  - `matanyone2.webapp.services.export`
  - `matanyone2.webapp.repository`

This keeps the proven inference/export path while replacing the browser UI completely.

## Architecture

### 1. Desktop App Layer

Add a new `matanyone2.desktop_app` package that owns:

- Qt application bootstrap
- desktop runtime configuration
- window composition
- native interaction state
- background job orchestration

This layer does not reimplement inference logic.

### 2. Session State Layer

Introduce a desktop session controller that wraps the existing draft/session model and exposes explicit workbench actions:

- open video
- scrub clip
- mark in
- mark out
- clear range
- apply anchor
- add/remove clicks
- paint refine strokes
- save target
- submit job
- enter review
- return to refine

This replaces browser route transitions with explicit application state transitions.

### 3. Service Reuse Layer

Keep the current Python service layer as the authoritative backend for:

- draft creation
- frame extraction
- SAM3-assisted target initialization
- mask persistence
- MatAnyone2 inference
- export generation

The desktop app should call these services directly instead of routing through HTTP.

## UX Structure

### Clip Step

- central source monitor
- one compact source timeline below the monitor
- `Mark In`, `Mark Out`, `Clear`, `Play/Pause` in a single horizontal control row
- a green segment band for the applied processing range
- an anchor rail appears only after the range is valid

Scrubbing updates the monitor immediately. Marking in/out never opens a second viewer.

### Mask Step

- the same monitor remains in place
- clicking in the monitor applies SAM3 point prompts to the selected target
- target switching lives in the left inspector `Targets` tab
- the current target is always visible in a compact status row

### Refine Step

- the same monitor is reused for live matte feedback
- the left `Refine` tab includes:
  - point mode
  - brush mode
  - preset selection
  - preset strength
  - motion softness
  - temporal stability
  - edge feather radius
  - brush size
  - overlay opacity

There is no second compare window. Refinement updates the main monitor directly.

### Review Step

- the same monitor switches among `Source`, `Overlay`, `Alpha`, `Foreground`
- the left `Export` tab shows:
  - current job status
  - selected targets and presets
  - downloadable outputs
  - `Back to Refine`

This keeps review inside the same workbench and avoids context loss.

## Data Flow

1. User opens a local video file.
2. `VideoDraftService` creates the draft and source preview metadata.
3. The desktop session stores range and anchor locally, then applies them to the draft model.
4. `MaskingService` creates or updates masks on demand.
5. Saving a target persists its mask and selected refinement controls.
6. Submitting creates a job record and runs inference/export in a background worker thread.
7. Review mode reads the generated artifacts directly from disk.

## Error Handling

- Missing checkpoint or unreadable video: block session start with an inline dialog.
- Invalid range or anchor: keep the user in `Clip` with direct field-level feedback.
- Failed inference/export: move to `Review` with an error state, logs, and retry path.
- Unsaved changes while leaving a step: use explicit desktop confirmation dialogs.

## Testing Strategy

### Automated

- controller-level tests for step transitions
- range and anchor validation tests
- direct service integration tests for saved masks and job submission
- smoke test that creates a draft, sets a range, applies an anchor, saves a mask, and runs a stubbed job

### Manual

- upload/open a real video
- define a clip with in/out
- set an anchor inside the clip
- create at least one target
- adjust refine controls and confirm the main monitor updates
- run a full inference job
- review source/alpha/foreground outputs in the same workspace

## Acceptance Criteria

- No browser is required to use the workbench.
- The app uses one main monitor throughout the session.
- In/out/clear controls are horizontal and compact.
- The user can return between `Clip`, `Mask`, `Refine`, and `Review` without browser history.
- Refinement controls affect the main monitor, not a secondary miniature compare panel.
- A full end-to-end local test completes on the target machine.
