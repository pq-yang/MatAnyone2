# MatAnyone2 Standalone Desktop Workbench State Feedback Redesign

## Goal

Rebuild the standalone desktop workbench UX around a professional, monitor-centric state machine so the user always knows:

- which step is active
- which tool is active
- whether the app received the last action
- whether the app is computing or idle
- where the latest result is shown
- what the next recommended action is

This redesign targets the current failure mode where selection, refinement, and review technically work but feel disjointed and unreadable during real use.

## Problem Summary

The current desktop workbench has functional controls, but the interaction model is not legible enough for production-style use.

Observed problems:

- tool activation is weak; entering `Select Subject` does not produce a strong enough cursor and monitor-state change
- click feedback is ambiguous; users cannot reliably tell whether a click was received, processed, or ignored
- result feedback is ambiguous; after a click, users do not know whether they should inspect `Overlay`, `Mask`, or keep selecting
- step feedback is weak; users do not feel the transition between `Clip`, `Mask`, `Refine`, and `Review`
- long-running inference/export work presents too little live status and feels static

The root issue is not a single missing widget. The workbench lacks a coherent state feedback system.

## Product Direction

The redesigned desktop app remains a single-window workbench, but shifts from a loose multi-panel tool to a clear professional workflow shell:

- one main monitor remains the center of attention
- a compact top toolbar communicates global state
- a monitor-local tool row communicates the active interaction mode
- a persistent bottom status dock communicates current state, system activity, and next action
- the left inspector holds controls, not workflow explanations

This should feel closer to professional video/compositing software than to a page-style admin tool.

## UX Model

### Global Step Model

The workbench keeps four application steps:

- `Clip`
- `Mask`
- `Refine`
- `Review`

Unlike a rigid wizard, the user can move between steps, but each step must advertise one of these conditions:

- `ready`
- `active`
- `done`
- `needs redo`
- `locked`

Examples:

- changing `In/Out` marks downstream `Mask` and `Refine` work as `needs redo`
- changing the anchor invalidates the prior saved matte authoring state for the active session
- `Review` stays `locked` until inference completes

### Main Monitor Rules

The main monitor is always the primary surface.

- `Source`, `Overlay`, `Mask`, `Alpha`, and `Foreground` all render in the same monitor
- there is no secondary compare monitor as part of the default flow
- all click, brush, hover, and loading feedback should stay visually anchored to this monitor

### Interaction Modes

The monitor tool row exposes:

- `Select Subject`
- `Exclude`
- `Brush Add`
- `Brush Remove`
- `Brush Feather`

Required activation feedback:

- `Select Subject` and `Exclude` use a crosshair cursor
- brush modes use a brush-style cursor or, at minimum, a non-arrow drawing cursor
- the active tool button is visibly latched
- the monitor frame gains an active accent stroke while an interactive tool is armed

The previous implicit “tool selected but cursor unchanged” behavior is not acceptable.

## State Feedback System

### 1. Tool Activation Feedback

When a tool is armed, the user must get immediate confirmation through multiple channels:

- cursor change
- tool button latched state
- monitor border accent
- explicit status message in the bottom dock

Examples:

- `Select Subject active`
- `Exclude active`
- `Brush Add active`

### 2. Click Feedback Lifecycle

Each point-selection action must move through a visible lifecycle:

1. `input received`
2. `processing`
3. `result updated`

Required feedback behaviors:

- on click, show the point marker immediately
- show short-lived processing feedback such as `Updating mask...`
- when the update lands, switch the monitor to `Overlay`
- update the bottom dock with a clear next-action recommendation

Example sequence:

- `Current State: Selection Active`
- `System: Click received`
- `System: Updating mask...`
- `Current State: Mask updated`
- `Next: View Mask, Keep Selecting, or Save Target`

### 3. Result Inspection Feedback

After a successful click or brush update:

- the main monitor defaults to `Overlay`
- `Mask` becomes the recommended inspection target
- the user is explicitly told that the matte can be inspected in the same monitor

Required guidance states:

- when `Overlay` is active after an update:
  - `Selection updated. The main monitor is showing Overlay. Click Mask to inspect the matte, keep selecting to refine, or Save Target when it looks right.`
- when `Mask` is active:
  - `Mask view is live. Inspect the matte here, then return to Overlay or Source to keep refining.`

This avoids the current failure mode where the user does not know where to look after clicking.

### 4. Long-Task Progress Feedback

Submitting inference must no longer feel static.

The desktop app should expose a visible progress state machine:

- `Preparing session`
- `Running MatAnyone2`
- `Exporting foreground and alpha`
- `Packaging outputs`
- `Ready`
- `Failed`

The top toolbar and bottom status dock should both reflect this state.

### 5. Next-Action Guidance

The bottom dock should always answer:

- what state am I in
- what is the app doing
- what should I do next

The dock is the primary workflow guide and replaces the current scattered explanatory text.

## Layout Changes

### Top Toolbar

The top toolbar should contain:

- `Open Video`
- `Back`
- `Next`
- current step
- current target
- current tool
- global system status

This is not a secondary status label. It is the persistent session header.

### Monitor Tool Row

Above the monitor, keep only:

- view switching: `Source`, `Overlay`, `Mask`, `Alpha`, `Foreground`
- tool switching: `Select Subject`, `Exclude`, `Brush Add`, `Brush Remove`, `Brush Feather`

This row should read like a professional monitor toolbar, not a collection of generic buttons.

### Left Inspector

Keep three tabs:

- `Targets`
- `Refine`
- `Export`

But remove workflow explanation from this area. The left side is for control, not orientation.

### Bottom Status Dock

Replace weak, ad-hoc feedback with a dedicated dock containing:

- `Current State`
- `System Activity`
- `Next Action`
- short progress indicator for long tasks

This is the center of the new UX model.

## Clip Step Behavior

Default clip logic:

- if the user does not define `In/Out`, the whole clip is active
- if the user selects `Select Subject` without choosing an anchor, the app defaults the anchor to the start of the active range
- if no trimmed range exists, that means frame `0`
- if a trimmed range exists, that means `process_start_frame_index`

The workbench should explicitly communicate that whole-clip behavior is the default, not an error case.

## Mask Step Behavior

When the user enters `Mask`:

- `Select Subject` should be the default active tool
- the cursor must become a crosshair
- the bottom dock should say the tool is ready for click input
- first successful click should transition the monitor into `Overlay`
- the next action should be explicit: keep selecting, inspect `Mask`, or save

## Refine Step Behavior

`Refine` should behave like continued work on the same monitor result, not a disconnected sub-page.

- the left tab switches to `Refine`
- the active tool and preset remain visible in the top session header
- brush work produces the same `received -> processing -> updated` feedback chain
- the monitor remains the only place where refinement results are judged

## Review Step Behavior

`Review` stays in the same window and the same monitor.

- the top header shows review state
- `Alpha` and `Foreground` become enabled
- the left tab switches to `Export`
- the bottom dock says whether outputs are ready, failed, or partially complete

Users should never need browser-history-like behavior or hidden routing to understand where they are.

## Technical Scope

This redesign is primarily a desktop UI/UX and state-feedback refactor.

It does not require changing the core MatAnyone2 inference model in this phase.

It does require:

- stronger monitor cursor/state control in `matanyone2.desktop_app.widgets`
- richer session state and status messaging in `matanyone2.desktop_app.main_window`
- clearer step and state transitions in `matanyone2.desktop_app.session_controller`
- revised desktop tests covering tool activation, state text, and post-click guidance

## Testing Strategy

### Automated

- tool activation tests for cursor/mode state
- click-flow tests for `clip -> auto-anchor -> mask`
- state-dock text tests for:
  - whole-clip default behavior
  - trimmed-range behavior
  - post-click `Overlay` guidance
  - `Mask` inspection guidance
- review-state tests for long-task transitions

### Manual

- open a real video
- do not mark `In/Out`
- click `Select Subject`
- verify the workbench defaults to whole-clip + frame-0 anchor
- click the subject in the monitor
- verify:
  - crosshair cursor is visible
  - click is acknowledged
  - the monitor switches to `Overlay`
  - the user can immediately find `Mask`
  - the bottom dock clearly explains the next move
- run a full inference and confirm review feedback is not static

## Acceptance Criteria

- `Select Subject` visibly changes the cursor to a crosshair
- the user can always tell the current step, current tool, and current system activity
- clicking the monitor produces immediate acknowledgment and a visible result lifecycle
- after a click, the workbench clearly tells the user where to inspect the matte
- whole-clip processing is the default when no range is defined
- moving through `Clip`, `Mask`, `Refine`, and `Review` feels like one continuous professional workbench
