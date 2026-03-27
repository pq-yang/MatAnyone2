# MatAnyone2 Standalone Desktop Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a PySide6-based standalone MatAnyone2 desktop workbench that replaces the browser UI while reusing the existing Python draft, masking, inference, and export services.

**Architecture:** Add a new `matanyone2.desktop_app` package containing the Qt bootstrap, single-window workbench UI, and session controller. Reuse the current service layer directly from the desktop app, and run inference/export via background worker threads instead of HTTP routes.

**Tech Stack:** Python 3.10+, PySide6, Qt Multimedia, existing MatAnyone2 Python services, pytest.

---

### Task 1: Add Desktop App Package Skeleton

**Files:**
- Create: `D:\my_app\matanyone2\.worktrees\standalone-app-ui-rebuild\matanyone2\desktop_app\__init__.py`
- Create: `D:\my_app\matanyone2\.worktrees\standalone-app-ui-rebuild\matanyone2\desktop_app\app.py`
- Create: `D:\my_app\matanyone2\.worktrees\standalone-app-ui-rebuild\matanyone2\desktop_app\config.py`
- Create: `D:\my_app\matanyone2\.worktrees\standalone-app-ui-rebuild\scripts\run_desktop_workbench.py`
- Modify: `D:\my_app\matanyone2\.worktrees\standalone-app-ui-rebuild\pyproject.toml`
- Test: `D:\my_app\matanyone2\.worktrees\standalone-app-ui-rebuild\tests\desktop_app\test_app_config.py`

- [ ] **Step 1: Write the failing config/bootstrap tests**
- [ ] **Step 2: Run the new tests and confirm failure**
- [ ] **Step 3: Add desktop config objects and bootstrap entrypoint**
- [ ] **Step 4: Run the tests and make them pass**
- [ ] **Step 5: Commit**

### Task 2: Implement Session Controller

**Files:**
- Create: `D:\my_app\matanyone2\.worktrees\standalone-app-ui-rebuild\matanyone2\desktop_app\session_controller.py`
- Create: `D:\my_app\matanyone2\.worktrees\standalone-app-ui-rebuild\tests\desktop_app\test_session_controller.py`
- Modify: `D:\my_app\matanyone2\.worktrees\standalone-app-ui-rebuild\matanyone2\webapp\models.py`

- [ ] **Step 1: Write failing tests for clip/range/anchor workflow**
- [ ] **Step 2: Run the controller tests and confirm failure**
- [ ] **Step 3: Implement the controller using existing draft/session services**
- [ ] **Step 4: Re-run tests and make them pass**
- [ ] **Step 5: Commit**

### Task 3: Build Main Window and Workbench Layout

**Files:**
- Create: `D:\my_app\matanyone2\.worktrees\standalone-app-ui-rebuild\matanyone2\desktop_app\main_window.py`
- Create: `D:\my_app\matanyone2\.worktrees\standalone-app-ui-rebuild\matanyone2\desktop_app\widgets.py`
- Create: `D:\my_app\matanyone2\.worktrees\standalone-app-ui-rebuild\tests\desktop_app\test_main_window.py`

- [ ] **Step 1: Write failing UI structure tests for stepper, monitor, timeline, and inspector tabs**
- [ ] **Step 2: Run the UI tests and confirm failure**
- [ ] **Step 3: Implement the single-window layout**
- [ ] **Step 4: Re-run tests and make them pass**
- [ ] **Step 5: Commit**

### Task 4: Wire Native Video Scrubbing and Range Controls

**Files:**
- Modify: `D:\my_app\matanyone2\.worktrees\standalone-app-ui-rebuild\matanyone2\desktop_app\main_window.py`
- Modify: `D:\my_app\matanyone2\.worktrees\standalone-app-ui-rebuild\matanyone2\desktop_app\widgets.py`
- Create: `D:\my_app\matanyone2\.worktrees\standalone-app-ui-rebuild\tests\desktop_app\test_timeline_controls.py`

- [ ] **Step 1: Write failing tests for horizontal controls and range/anchor enablement**
- [ ] **Step 2: Run the timeline tests and confirm failure**
- [ ] **Step 3: Implement source monitor scrubbing, mark in/out, clear, and anchor rail behavior**
- [ ] **Step 4: Re-run tests and make them pass**
- [ ] **Step 5: Commit**

### Task 5: Wire Mask and Refine Interaction

**Files:**
- Modify: `D:\my_app\matanyone2\.worktrees\standalone-app-ui-rebuild\matanyone2\desktop_app\main_window.py`
- Modify: `D:\my_app\matanyone2\.worktrees\standalone-app-ui-rebuild\matanyone2\desktop_app\session_controller.py`
- Create: `D:\my_app\matanyone2\.worktrees\standalone-app-ui-rebuild\tests\desktop_app\test_refine_controls.py`

- [ ] **Step 1: Write failing tests for target tab, refine tab, and direct-monitor preview updates**
- [ ] **Step 2: Run the refine tests and confirm failure**
- [ ] **Step 3: Implement target actions and refine sliders, including edge feather**
- [ ] **Step 4: Re-run tests and make them pass**
- [ ] **Step 5: Commit**

### Task 6: Add Background Job Execution and Review Step

**Files:**
- Create: `D:\my_app\matanyone2\.worktrees\standalone-app-ui-rebuild\matanyone2\desktop_app\jobs.py`
- Modify: `D:\my_app\matanyone2\.worktrees\standalone-app-ui-rebuild\matanyone2\desktop_app\main_window.py`
- Create: `D:\my_app\matanyone2\.worktrees\standalone-app-ui-rebuild\tests\desktop_app\test_review_step.py`

- [ ] **Step 1: Write failing tests for submit, review mode, and back-to-refine behavior**
- [ ] **Step 2: Run the review tests and confirm failure**
- [ ] **Step 3: Implement background job runner and review-state transitions**
- [ ] **Step 4: Re-run tests and make them pass**
- [ ] **Step 5: Commit**

### Task 7: Add Desktop Smoke Test and Docs

**Files:**
- Create: `D:\my_app\matanyone2\.worktrees\standalone-app-ui-rebuild\tests\desktop_app\test_smoke_desktop.py`
- Modify: `D:\my_app\matanyone2\.worktrees\standalone-app-ui-rebuild\README.md`
- Modify: `D:\my_app\matanyone2\.worktrees\standalone-app-ui-rebuild\scripts\run_desktop_workbench.py`

- [ ] **Step 1: Write a failing smoke-style desktop test around the session controller**
- [ ] **Step 2: Run the smoke test and confirm failure**
- [ ] **Step 3: Finish the launch path and README usage docs**
- [ ] **Step 4: Run desktop tests and existing critical tests**
- [ ] **Step 5: Commit**
