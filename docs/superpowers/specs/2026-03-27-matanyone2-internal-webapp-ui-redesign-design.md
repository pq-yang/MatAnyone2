# MatAnyone2 Internal Web App UI Redesign Design

**Date:** 2026-03-27

**Status:** Approved for planning

## Summary

Redesign the internal MatAnyone2 web app as a **desktop-first professional matting workstation** rather than a thin wrapper around the current demo flow.

The redesign covers all three primary pages:

- upload
- annotation
- results review

The new UI direction is:

- dark, post-production-tool visual language
- desktop-first layout for mouse and keyboard on large screens
- annotation as a real workbench, not a simple point-click page
- multi-target layer management
- a staged workflow:
  - coarse subject selection
  - edge refinement
  - result preview

This redesign is explicitly a **product and interaction redesign**, not an algorithm rewrite. It must make the current system more controllable, more legible, and more credible as an internal tool, while staying compatible with the current MatAnyone2-based backend.

## Why A Full UI Redesign Is Needed

The current UI has three structural problems:

1. It looks like a technical demo, not an internal production tool.
2. It exposes low-level interaction details directly to the user.
3. It does not provide a clear model for refining difficult edges such as hair.

Specific symptoms in the current implementation:

- The annotation page keeps accumulating click points in one continuous session state.
- Old points remain visually present and conceptually active, which makes the page feel noisy and uncontrolled.
- The UI does not separate coarse object identification from edge refinement.
- Multi-target editing is not represented as a first-class layer workflow.
- The results page behaves more like a download list than a review surface.

This makes even valid model behavior feel unreliable, because the product does not communicate what the user is doing at each step or what kind of result should be expected from that step.

## Product Goal

Turn the current internal web app into a **desktop annotation-and-review workstation** for short-form human video matting.

The redesigned workflow should help a user:

1. Upload a short video and confirm it is valid.
2. Enter a dedicated annotation workbench.
3. Build one or more target layers.
4. Move through a staged masking workflow with clear intent.
5. Review the generated result in a visually credible way.
6. Download deliverables when satisfied.

## Explicit Scope

### In Scope

- Full redesign of:
  - upload page
  - annotation page
  - results page
- New desktop-first layout system
- New visual system for a professional post-production-tool aesthetic
- Annotation workbench redesign
- Multi-target layer UI model
- Staged interaction model:
  - coarse selection
  - edge refinement
  - preview
- Improved status, feedback, and review surfaces
- Keyboard shortcut design for annotation tools
- Frontend state model changes needed to support the redesigned workflow
- Light backend/API extensions required for:
  - richer draft state
  - layer metadata
  - history-oriented interaction
  - preview state switching

### Out Of Scope

- New matting model architecture
- Guaranteed hair-quality improvements from algorithm changes alone
- Full Photoshop-class matte painting tools
- Mobile-first experience
- Touch-first tablet workflows
- Long-term asset library or project management
- Multi-user collaborative editing

## Design Principles

### 1. Canvas First

The image and its matte state are the center of the product. Tooling, metadata, and status should frame the canvas, not compete with it.

### 2. Stage Clarity

Users must always know whether they are:

- selecting the subject
- refining edges
- previewing the result

The system should never collapse these into one undifferentiated interaction state.

### 3. Layer-Based Mental Model

Each target person is an independent layer. The UI must not treat multiple targets as an invisible merged state during editing, even if downstream export initially remains combined.

### 4. Professional Restraint

The UI should feel precise and trustworthy, not flashy. Deep color, quiet structure, and strong hierarchy are preferred over decorative effects.

### 5. Feedback Over Logs

The product should communicate workflow meaning, not implementation details. Users should see messages such as "Subject updated" or "Edge refinement applied", not coordinate-heavy click logs as the primary feedback language.

## Users And Usage Assumptions

- Internal operators
- Mouse and keyboard
- Large-screen desktops, typically 1920x1080 or larger
- Short-form videos, usually within the existing internal tool constraints
- Users care about visual judgment, especially around silhouette quality and hair
- Users are comfortable with tool-like interfaces if the workflow is clear

## Information Architecture

The redesigned product remains a three-page flow, but each page becomes a purpose-built surface instead of a minimal form.

### 1. Upload Page

Purpose:

- begin a new session
- validate the media
- show system readiness
- set expectations before entering annotation

Primary areas:

- session header
- large drag-and-drop upload panel
- media information card
- output summary
- primary action bar

### 2. Annotation Workbench

Purpose:

- construct and refine target masks in a controlled environment

Primary layout:

- left tool rail
- central canvas stage
- right layer and inspector panel

Primary page zones:

- top workbench bar
- stage switcher
- canvas and view controls
- target layer list
- tool inspector
- contextual help

### 3. Results Review Page

Purpose:

- inspect the generated outputs
- judge whether the matte is acceptable
- download deliverables
- return to annotation when needed

Primary areas:

- result top bar
- large preview viewport
- preview mode tabs
- artifact panel
- warnings panel
- target review controls

## Visual System

### Visual Direction

The visual reference point is a professional post-production desktop tool, not a generic SaaS admin and not a consumer media site.

The interface should read as:

- stable
- dark
- structured
- detail-oriented

### Color System

Use a restrained dark palette with semantic highlights:

- background:
  - deep graphite
  - cold charcoal
- panel levels:
  - base
  - raised
  - floating
- text:
  - warm off-white to controlled mid-gray
- semantic accents:
  - active: cool cyan-blue
  - success: restrained green
  - warning: amber
  - error: orange-red

Mask and annotation colors:

- active mask fill: blue-violet translucent fill
- edge highlight: warm orange outline
- positive points: green
- negative points: magenta-violet

These colors are functional. They should not be reused as decorative branding flourishes.

### Typography

Typography should feel tool-oriented:

- compact, legible UI typography
- restrained title sizing
- strong small labels and panel headings
- tabular numbers for fps, frame counts, durations, and queue-related data

Avoid:

- marketing-style oversized headlines
- excessive weight contrast
- ornamental font choices

### Panels And Surfaces

Panels should feel like parts of one workstation shell:

- narrow, disciplined radius
- subtle separators
- consistent spacing scale
- low-noise backgrounds
- strong visual priority for the canvas

The UI should avoid looking like a stack of unrelated web cards.

### Motion

Motion should only clarify state changes:

- stage switching
- layer selection
- preview mode changes
- job progress transitions
- compact hover and pressed feedback

Animation rules:

- use transform and opacity only
- respect `prefers-reduced-motion`
- do not animate layout dimensions
- avoid decorative ambient motion

## Upload Page Design

### Purpose

The upload page should confirm media readiness before annotation starts.

### Core Components

- `SessionHeader`
  - product name
  - machine/GPU readiness
  - queue status
- `DropzonePanel`
  - drag/drop target
  - click-to-select fallback
- `MediaInfoCard`
  - file name
  - duration
  - resolution
  - frame rate
  - file size
  - first-frame thumbnail
- `OutputSummary`
  - alpha
  - foreground
  - PNG sequence zip
  - ProRes 4444
- `PrimaryActionBar`
  - primary: enter annotation workbench
  - secondary: reselect media

### UX Rules

- immediate validation feedback
- no tiny form controls as the main interaction
- no hidden assumptions about supported usage
- all key constraints visible before the user commits

## Annotation Workbench Design

### Core Layout

The annotation page becomes a three-column workbench:

- left: tool rail
- center: canvas stage
- right: layers and inspector

### Top Workbench Bar

Displays:

- source video name
- current stage
- active target layer
- save state
- submit action

This is the user's orientation anchor.

### Stage Model

The annotation flow is explicitly staged:

1. `Coarse Selection`
2. `Edge Refinement`
3. `Preview`

Each stage changes which controls are emphasized and how the canvas is interpreted.

### Tool Rail

The left rail contains primary tools:

- browse / pan
- positive point
- negative point
- add region
- subtract region
- edge refinement brush
- compare / inspection

Shortcuts should be visible and standardized.

### Canvas Stage

The center canvas supports:

- zoom
- pan
- fit to screen
- 100% and 200% inspection
- mask overlay opacity
- original / matte / composite / compare modes
- optional transparency grid

The canvas must be visually dominant.

### Layer Panel

The right-side layer panel manages multiple targets:

- create target
- rename target
- show/hide
- lock
- delete
- solo current target
- choose active editing target

Each target is edited independently at the UI level.

### Inspector Panel

The inspector changes based on the active stage and tool.

Examples:

- current tool description
- point counts
- brush size
- edge intensity or refinement settings
- history list
- undo / redo
- clear current stage

### Why The Current "Too Many Points" Problem Happens

The current implementation keeps accumulating clicks into one persistent interaction state and visually exposes that history too directly.

The redesign fixes this by changing the model:

- clicks belong to the active target layer
- clicks are stage-aware
- only active or recent points are shown by default
- history is managed in the inspector, not sprayed permanently across the canvas
- refinement is not treated as "add more points forever"

### Annotation Interaction Rules

- coarse selection is for identifying the subject, not perfect edges
- edge refinement is where the product focuses the user on hair, shoulders, and semi-transparent boundaries
- preview hides annotation clutter and focuses on output judgment
- feedback messages describe workflow meaning, not raw implementation logs

## Results Review Page Design

### Purpose

The result page is a review surface first and a download surface second.

### Core Components

- `ResultTopbar`
  - job status
  - back to annotation
  - re-export or rerun entry
- `PreviewViewport`
  - large preview area
- `PreviewModeTabs`
  - original
  - alpha
  - foreground
  - composite
- `ArtifactPanel`
  - direct downloads and export metadata
- `WarningPanel`
  - export caveats
  - degraded outputs
- `TargetReviewPanel`
  - per-target review toggles if supported by the frontend state
- `JobTimeline`
  - queued
  - running
  - exporting
  - completed

### UX Rules

- preview is visually prioritized over raw metadata
- status is visible without pushing the preview off screen
- download links are organized and named like deliverables, not implementation leftovers
- users can clearly return to editing if quality is not acceptable

## Frontend State Model Changes

The redesign requires a richer frontend state model than the current flat page logic.

The annotation workbench should track:

- active stage
- active tool
- active target layer
- target layer collection
- per-layer click state
- per-layer visibility and lock state
- history entries
- canvas view mode
- canvas zoom and pan state
- current preview assets
- unsaved change state

This is a structural shift away from the current single-page event handling model.

## Backend And API Implications

The redesign should avoid unnecessary backend rewrites, but some API growth is expected.

Recommended additions or adjustments:

- draft/session endpoints should be able to return richer editor state
- layer metadata should be serializable
- history-oriented interaction should be supported
- preview resources should support multiple view modes cleanly
- submission should preserve the distinction between UI layers and downstream merged masks

The backend does not need to become algorithmically smarter in the first phase, but it must support the product model cleanly.

## Naming And Language Adjustments

The redesign should reduce technical demo language in the UI.

De-emphasize or replace phrases such as:

- "Create Draft"
- "Save Mask"
- coordinate-heavy click logs

Prefer workflow-oriented language such as:

- "Start Session"
- "Save Target"
- "Refine Edge"
- "Preview Result"
- "Submit For Processing"

## Accessibility And Input Rules

The redesign must keep strong desktop usability:

- visible focus states
- keyboard navigability
- minimum usable target sizes
- semantic labeling
- error messages near the related area
- contrast-safe overlays and panel text

Desktop-first does not remove the need for accessibility discipline.

## What This Redesign Does Not Promise

This redesign will improve:

- clarity
- controllability
- workflow quality
- confidence in result review

It does not, by itself, guarantee materially better hair quality at the algorithm level.

The product should make that boundary clear by:

- separating coarse selection from edge refinement
- surfacing better preview modes
- making quality judgment easier
- leaving room for later algorithm or matte-editing upgrades

## Acceptance Criteria

The redesign is successful when:

- the product no longer feels like a technical demo
- the upload page clearly communicates readiness and constraints
- the annotation page feels like a controlled workbench
- multi-target editing is visually and conceptually layer-based
- users can distinguish coarse subject selection from edge refinement
- the interface no longer overwhelms the user with persistent point clutter
- the results page supports visual review before download
- the three pages feel like one coherent tool, not three unrelated templates

## Recommended Implementation Order

1. Rebuild the base shell, layout grid, and global visual system.
2. Rebuild the annotation frontend state model and workbench layout.
3. Add layer-oriented target management and staged tool surfaces.
4. Rebuild the results page as a review-first surface.
5. Only after the above, refine supporting API responses where required.

This order ensures the redesign fixes the interaction model first instead of only repainting the existing behavior.
