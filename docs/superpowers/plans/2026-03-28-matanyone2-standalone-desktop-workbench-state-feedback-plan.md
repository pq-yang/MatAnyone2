# MatAnyone2 Standalone Desktop Workbench State Feedback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the standalone desktop workbench UX around a clear professional state-feedback system so users always know the active step, tool, system activity, and next action.

**Architecture:** Keep the existing PySide6 single-window desktop shell and MatAnyone2 service layer, but refactor the desktop UI into a stronger state machine. Add explicit monitor activation feedback, a persistent status dock, clearer step status transitions, and long-task progress reporting without changing the core inference model.

**Tech Stack:** Python 3.10+, PySide6, existing `matanyone2.desktop_app` modules, existing MatAnyone2 video/masking/inference/export services, pytest.

---

### Task 1: Add Monitor Activation State and Cursor Feedback

**Files:**
- Modify: `D:\my_app\matanyone2\.worktrees\standalone-app-ui-rebuild\matanyone2\desktop_app\widgets.py`
- Modify: `D:\my_app\matanyone2\.worktrees\standalone-app-ui-rebuild\matanyone2\desktop_app\main_window.py`
- Modify: `D:\my_app\matanyone2\.worktrees\standalone-app-ui-rebuild\tests\desktop_app\test_main_window.py`

- [ ] **Step 1: Write the failing tests for monitor activation feedback**

```python
def test_select_subject_uses_crosshair_cursor(...):
    window._set_interaction_mode("positive")
    assert window.monitor.surface.cursor().shape() == Qt.CrossCursor


def test_brush_mode_switches_cursor_away_from_arrow(...):
    window._set_interaction_mode("brush_add")
    assert window.monitor.surface.cursor().shape() != Qt.ArrowCursor
```

- [ ] **Step 2: Run the desktop window tests and confirm failure**

Run:  
`D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\.venv\Scripts\python.exe -m pytest .\tests\desktop_app\test_main_window.py -q`

Expected: FAIL on missing cursor behavior and/or missing monitor active state assertions.

- [ ] **Step 3: Implement monitor activation feedback**

Add minimal implementation in `widgets.py` and `main_window.py`:

```python
def set_interaction_cursor(self, mode: str) -> None:
    if mode in {"positive", "negative"}:
        self.setCursor(Qt.CrossCursor)
    elif mode.startswith("brush_"):
        self.setCursor(Qt.PointingHandCursor)
    else:
        self.unsetCursor()
```

Also add a monitor accent-state API so `main_window.py` can visually mark the monitor as armed when a live tool is active.

- [ ] **Step 4: Re-run the tests and make them pass**

Run:  
`D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\.venv\Scripts\python.exe -m pytest .\tests\desktop_app\test_main_window.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add matanyone2/desktop_app/widgets.py matanyone2/desktop_app/main_window.py tests/desktop_app/test_main_window.py
git commit -m "feat: add desktop monitor activation feedback"
```

### Task 2: Replace Weak Inline Text with a Persistent Status Dock

**Files:**
- Modify: `D:\my_app\matanyone2\.worktrees\standalone-app-ui-rebuild\matanyone2\desktop_app\widgets.py`
- Modify: `D:\my_app\matanyone2\.worktrees\standalone-app-ui-rebuild\matanyone2\desktop_app\main_window.py`
- Modify: `D:\my_app\matanyone2\.worktrees\standalone-app-ui-rebuild\tests\desktop_app\test_main_window.py`

- [ ] **Step 1: Write the failing tests for the status dock**

```python
def test_main_window_has_status_dock_sections(...):
    assert window.status_dock.current_state_label.text()
    assert window.status_dock.system_activity_label.text()
    assert window.status_dock.next_action_label.text()
```

- [ ] **Step 2: Run the tests and confirm failure**

Run:  
`D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\.venv\Scripts\python.exe -m pytest .\tests\desktop_app\test_main_window.py -q`

Expected: FAIL because the dock widget and labels do not exist yet.

- [ ] **Step 3: Implement a professional bottom status dock**

Create a focused widget in `widgets.py`:

```python
class StatusDock(QFrame):
    # current state | system activity | next action | progress
```

Wire it into `main_window.py` under the monitor/timeline region and route all status text updates through a single `_update_status_dock(...)` helper.

- [ ] **Step 4: Re-run the tests and make them pass**

Run:  
`D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\.venv\Scripts\python.exe -m pytest .\tests\desktop_app\test_main_window.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add matanyone2/desktop_app/widgets.py matanyone2/desktop_app/main_window.py tests/desktop_app/test_main_window.py
git commit -m "feat: add desktop status dock"
```

### Task 3: Rework Step and Tool State into Explicit Workflow Status

**Files:**
- Modify: `D:\my_app\matanyone2\.worktrees\standalone-app-ui-rebuild\matanyone2\desktop_app\session_controller.py`
- Modify: `D:\my_app\matanyone2\.worktrees\standalone-app-ui-rebuild\matanyone2\desktop_app\main_window.py`
- Modify: `D:\my_app\matanyone2\.worktrees\standalone-app-ui-rebuild\tests\desktop_app\test_session_controller.py`
- Modify: `D:\my_app\matanyone2\.worktrees\standalone-app-ui-rebuild\tests\desktop_app\test_main_window.py`

- [ ] **Step 1: Write failing tests for step-state semantics**

```python
def test_range_change_marks_mask_work_as_needing_redo(...):
    ...


def test_mask_step_defaults_to_select_subject_ready_state(...):
    ...
```

- [ ] **Step 2: Run the controller and window tests and confirm failure**

Run:  
`D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\.venv\Scripts\python.exe -m pytest .\tests\desktop_app\test_session_controller.py .\tests\desktop_app\test_main_window.py -q`

Expected: FAIL because step readiness/redo semantics are not modeled.

- [ ] **Step 3: Add explicit workflow status fields**

Extend desktop state so `main_window.py` can render:

```python
workflow_status = {
    "clip": "active",
    "mask": "needs_redo",
    "refine": "locked",
    "review": "locked",
}
```

Drive this from `session_controller.py` rather than ad-hoc window logic.

- [ ] **Step 4: Re-run the tests and make them pass**

Run:  
`D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\.venv\Scripts\python.exe -m pytest .\tests\desktop_app\test_session_controller.py .\tests\desktop_app\test_main_window.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add matanyone2/desktop_app/session_controller.py matanyone2/desktop_app/main_window.py tests/desktop_app/test_session_controller.py tests/desktop_app/test_main_window.py
git commit -m "feat: add desktop workflow status model"
```

### Task 4: Implement Click Lifecycle Feedback and Main-Monitor Result Guidance

**Files:**
- Modify: `D:\my_app\matanyone2\.worktrees\standalone-app-ui-rebuild\matanyone2\desktop_app\main_window.py`
- Modify: `D:\my_app\matanyone2\.worktrees\standalone-app-ui-rebuild\matanyone2\desktop_app\widgets.py`
- Modify: `D:\my_app\matanyone2\.worktrees\standalone-app-ui-rebuild\tests\desktop_app\test_main_window.py`

- [ ] **Step 1: Write failing tests for click lifecycle and post-click guidance**

```python
def test_click_updates_status_to_processing_then_overlay_guidance(...):
    ...


def test_mask_view_guidance_explains_next_action(...):
    ...
```

- [ ] **Step 2: Run the tests and confirm failure**

Run:  
`D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\.venv\Scripts\python.exe -m pytest .\tests\desktop_app\test_main_window.py -q`

Expected: FAIL because processing and updated states are not surfaced clearly enough.

- [ ] **Step 3: Implement the lifecycle**

Add explicit state transitions in `main_window.py`:

```python
self._set_status("Selection Active", "Click received", "Updating mask...")
# perform click
self._set_view_mode("overlay")
self._set_status("Mask updated", "Overlay refreshed", "View Mask, Keep Selecting, or Save Target")
```

If processing is synchronous, still expose both state changes in sequence using a short queued UI update so the user sees the transition.

- [ ] **Step 4: Re-run the tests and make them pass**

Run:  
`D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\.venv\Scripts\python.exe -m pytest .\tests\desktop_app\test_main_window.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add matanyone2/desktop_app/main_window.py matanyone2/desktop_app/widgets.py tests/desktop_app/test_main_window.py
git commit -m "feat: add desktop click lifecycle feedback"
```

### Task 5: Add Long-Task Progress Reporting for Inference and Export

**Files:**
- Modify: `D:\my_app\matanyone2\.worktrees\standalone-app-ui-rebuild\matanyone2\desktop_app\jobs.py`
- Modify: `D:\my_app\matanyone2\.worktrees\standalone-app-ui-rebuild\matanyone2\desktop_app\main_window.py`
- Modify: `D:\my_app\matanyone2\.worktrees\standalone-app-ui-rebuild\tests\desktop_app\test_review_step.py`

- [ ] **Step 1: Write failing tests for job-stage progress**

```python
def test_submit_job_reports_running_and_exporting_states(...):
    ...


def test_failed_job_updates_status_dock(...):
    ...
```

- [ ] **Step 2: Run the review tests and confirm failure**

Run:  
`D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\.venv\Scripts\python.exe -m pytest .\tests\desktop_app\test_review_step.py -q`

Expected: FAIL because the job runner does not emit staged progress updates.

- [ ] **Step 3: Extend desktop job reporting**

Emit intermediate stages from `jobs.py`, then surface them in `main_window.py`:

```python
Preparing session
Running MatAnyone2
Exporting foreground and alpha
Packaging outputs
Ready
```

Keep the implementation minimal: signal-based progress text is enough for this phase; do not add a second worker architecture.

- [ ] **Step 4: Re-run the review tests and make them pass**

Run:  
`D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\.venv\Scripts\python.exe -m pytest .\tests\desktop_app\test_review_step.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add matanyone2/desktop_app/jobs.py matanyone2/desktop_app/main_window.py tests/desktop_app/test_review_step.py
git commit -m "feat: add desktop inference progress feedback"
```

### Task 6: Tighten Review-State UX and Output Readiness

**Files:**
- Modify: `D:\my_app\matanyone2\.worktrees\standalone-app-ui-rebuild\matanyone2\desktop_app\main_window.py`
- Modify: `D:\my_app\matanyone2\.worktrees\standalone-app-ui-rebuild\tests\desktop_app\test_review_step.py`
- Modify: `D:\my_app\matanyone2\.worktrees\standalone-app-ui-rebuild\tests\desktop_app\test_main_window.py`

- [ ] **Step 1: Write failing tests for review readiness messaging**

```python
def test_review_state_enables_alpha_and_foreground_with_ready_message(...):
    ...
```

- [ ] **Step 2: Run the tests and confirm failure**

Run:  
`D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\.venv\Scripts\python.exe -m pytest .\tests\desktop_app\test_review_step.py .\tests\desktop_app\test_main_window.py -q`

Expected: FAIL because review messaging is still too generic.

- [ ] **Step 3: Implement explicit review readiness states**

When outputs are ready:

```python
Current State: Review ready
System Activity: Alpha and foreground generated
Next Action: Inspect Alpha, Foreground, or open output folder
```

Also ensure `Export` tab is selected automatically in review.

- [ ] **Step 4: Re-run the tests and make them pass**

Run:  
`D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\.venv\Scripts\python.exe -m pytest .\tests\desktop_app\test_review_step.py .\tests\desktop_app\test_main_window.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add matanyone2/desktop_app/main_window.py tests/desktop_app/test_review_step.py tests/desktop_app/test_main_window.py
git commit -m "feat: tighten desktop review readiness UX"
```

### Task 7: Full Desktop Regression, Smoke, and Docs Refresh

**Files:**
- Modify: `D:\my_app\matanyone2\.worktrees\standalone-app-ui-rebuild\README.md`
- Modify: `D:\my_app\matanyone2\.worktrees\standalone-app-ui-rebuild\scripts\smoke_desktop_workbench.py`
- Verify: `D:\my_app\matanyone2\.worktrees\standalone-app-ui-rebuild\runtime\desktop_workbench`

- [ ] **Step 1: Update README to describe the new state-feedback workflow**

Document:
- whole-clip default behavior
- automatic anchor-at-range-start behavior
- `Select Subject -> Overlay -> Mask -> Save Target` flow
- progress stages during inference/export

- [ ] **Step 2: Run the full desktop test suite**

Run:  
`D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\.venv\Scripts\python.exe -m pytest .\tests\desktop_app -q`

Expected: PASS

- [ ] **Step 3: Run the real desktop smoke**

Run:  
`D:\my_app\matanyone2\.worktrees\internal-webapp-ui-rebuild\.venv\Scripts\python.exe .\scripts\smoke_desktop_workbench.py`

Expected:
- a new `runtime\desktop_workbench\smoke-*` directory
- generated `foreground.mp4`
- generated `alpha.mp4`
- generated `rgba_png.zip`

- [ ] **Step 4: Record verification paths in README or release notes if needed**

- [ ] **Step 5: Commit**

```bash
git add README.md scripts/smoke_desktop_workbench.py
git commit -m "docs: refresh desktop workbench workflow guidance"
```
