import {
  formatDuration,
  parseJson,
  setStatus,
  withCacheBust,
} from "/static/shared.js";

const PRESET_META = {
  balanced: {
    label: "Balanced",
    note: "Use this when the silhouette is already close and you want an even starting point.",
  },
  hair: {
    label: "Hair Priority",
    note: "Bias your cleanup around flyaway strands and soft hairline gaps before committing the layer.",
  },
  edge: {
    label: "Edge Priority",
    note: "Use this when the boundary should stay tight around shoulders, jaw lines, or wardrobe edges.",
  },
  motion: {
    label: "Motion Blur",
    note: "Use this when motion softness matters more than a perfectly hard cut on the outer contour.",
  },
};

const TERMINAL_JOB_STATES = new Set([
  "completed",
  "completed_with_warning",
  "failed",
  "interrupted",
]);

function bindWorkbench() {
  const root = document.getElementById("workspace-app");
  if (!root) {
    return;
  }

  const status = document.getElementById("workspace-status");
  const image = document.getElementById("workspace-monitor-image");
  const canvasFrame = document.getElementById("workspace-monitor-frame");
  const saveButton = document.getElementById("save-mask");
  const submitButton = document.getElementById("submit-job");
  const createTargetButton = document.getElementById("create-target");
  const undoButton = document.getElementById("undo-click");
  const resetButton = document.getElementById("reset-target");
  const savedMaskList = document.getElementById("saved-mask-list");
  const targetList = document.getElementById("target-list");
  const positiveButton = document.getElementById("positive-mode");
  const negativeButton = document.getElementById("negative-mode");
  const brushButtons = Array.from(root.querySelectorAll(".brush-button"));
  const presetButtons = Array.from(root.querySelectorAll(".preset-button"));
  const workflowButtons = Array.from(root.querySelectorAll(".workflow-stepper__step"));
  const sidebarTabButtons = Array.from(root.querySelectorAll(".workspace-sidebar-tab"));
  const stageButtons = [];
  const viewButtons = Array.from(root.querySelectorAll(".canvas-view-tab"));
  const inspectorStage = document.getElementById("inspector-stage");
  const inspectorTarget = document.getElementById("inspector-target");
  const inspectorPreset = document.getElementById("inspector-preset");
  const inspectorPoints = document.getElementById("inspector-points");
  const inspectorMask = document.getElementById("inspector-mask");
  const canvasModeLabel = document.getElementById("canvas-mode-label");
  const canvasStageNote = document.getElementById("canvas-stage-note");
  const guidanceTitle = document.getElementById("stage-guidance-title");
  const guidanceCopy = document.getElementById("stage-guidance-copy");
  const selectionNote = document.getElementById("selection-note");
  const presetNote = document.getElementById("preset-note");
  const brushNote = document.getElementById("brush-note");
  const workflowStageChip = document.getElementById("workflow-stage-chip");
  const targetNameInput = document.getElementById("target-name-input");
  const applyTargetNameButton = document.getElementById("apply-target-name");
  const toggleTargetLockButton = document.getElementById("toggle-target-lock");
  const targetSummary = document.getElementById("target-summary");
  const brushRadiusInput = document.getElementById("brush-radius");
  const brushRadiusValue = document.getElementById("brush-radius-value");
  const overlayOpacityInput = document.getElementById("overlay-opacity");
  const overlayOpacityValue = document.getElementById("overlay-opacity-value");
  const sourcePlayheadSlider = document.getElementById("source-playhead-slider");
  const markRangeInButton = document.getElementById("mark-range-in");
  const markRangeOutButton = document.getElementById("mark-range-out");
  const clearRangeSelectionButton = document.getElementById("clear-range-selection");
  const toggleSourcePlaybackButton = document.getElementById("toggle-source-playback");
  const timelineCurrentLabel = document.getElementById("timeline-current-label");
  const timelineSelectedLabel = document.getElementById("timeline-selected-label");
  const timelineAppliedLabel = document.getElementById("timeline-applied-label");
  const timelineInChip = document.getElementById("timeline-in-chip");
  const timelineOutChip = document.getElementById("timeline-out-chip");
  const timelineDurationChip = document.getElementById("timeline-duration-chip");
  const timelineRangeRail = document.getElementById("clip-primary-rail");
  const timelineRangeSelection = document.getElementById("timeline-range-selection");
  const templateFrameSlider = document.getElementById("anchor-frame-slider");
  const templateFrameValue = document.getElementById("anchor-frame-value");
  const anchorRail = document.getElementById("anchor-rail");
  const anchorFrameSummary = null;
  const keyframeVideo = document.getElementById("workspace-monitor-video");
  const keyframeSelectedLabel = document.getElementById("keyframe-selected-label");
  const keyframeAppliedLabel = document.getElementById("keyframe-applied-label");
  const keyframeTimeLabel = document.getElementById("keyframe-time-label");
  const presetStrengthInput = document.getElementById("preset-strength");
  const presetStrengthValue = document.getElementById("preset-strength-value");
  const motionStrengthInput = document.getElementById("motion-strength");
  const motionStrengthValue = document.getElementById("motion-strength-value");
  const temporalStabilityInput = document.getElementById("temporal-stability");
  const temporalStabilityValue = document.getElementById("temporal-stability-value");
  const edgeFeatherRadiusInput = document.getElementById("edge-feather-radius");
  const edgeFeatherRadiusValue = document.getElementById("edge-feather-radius-value");
  const reviewSidebar = document.getElementById("workspace-review-sidebar");
  const reviewSummaryList = document.getElementById("review-summary-list");
  const reviewSummaryListSide = document.getElementById("review-summary-list-side");
  const targetReviewList = document.getElementById("target-review-list");
  const artifactSummaryList = document.getElementById("artifact-summary-list");
  const jobTimeline = document.getElementById("job-timeline");
  const warningPanel = document.getElementById("warning-panel");
  const warningTitle = document.getElementById("warning-title");
  const warningCopy = document.getElementById("warning-copy");
  const overlayCanvas = document.getElementById("workspace-overlay-canvas");
  const overlayForegroundVideo = document.getElementById("workspace-overlay-foreground-video");
  const overlayAlphaVideo = document.getElementById("workspace-overlay-alpha-video");
  const workspaceNavBack = document.getElementById("workspace-nav-back");
  const workspaceNavNext = document.getElementById("workspace-nav-next");
  const workspaceReturnToClip = document.getElementById("workspace-return-to-clip");
  const workspaceReturnToRefine = document.getElementById("workspace-return-to-refine");

  const state = {
    activeTool: "point-positive",
    canvasMode: root.dataset.defaultCanvasMode || "source",
    workbench: null,
    selectedMasks: new Set(),
    brushRadius: Number(brushRadiusInput?.value || 28),
    overlayOpacity: Number(overlayOpacityInput?.value || 72),
    playheadFrame: Number(sourcePlayheadSlider?.value || 0),
    rangeSelectionStart: 0,
    rangeSelectionEnd: 0,
    rangeSelectionTouchedStart: false,
    rangeSelectionTouchedEnd: false,
    rangeAppliedStart: 0,
    rangeAppliedEnd: 0,
    templateFrameSelection: Number(templateFrameSlider?.value || 0),
    templateFrameApplied: templateFrameSlider?.value === "" ? null : Number(templateFrameSlider?.value || 0),
    fps: Number(root.dataset.fps || 0),
    durationSeconds: Number(root.dataset.durationSeconds || 0),
    livePatchTimer: null,
    livePatchRevision: 0,
    lastAppliedLivePatchRevision: 0,
    jobPollTimer: null,
    reviewPayload: null,
    reviewMode: "source",
    overlayFrameHandle: null,
    overlayVideosBound: false,
    foregroundCanvas: document.createElement("canvas"),
    alphaCanvas: document.createElement("canvas"),
  };

  const WORKFLOW_STEPS = ["clip", "mask", "refine", "review"];
  const SIDEBAR_TABS = ["targets", "refine", "export"];
  const foregroundContext = state.foregroundCanvas.getContext("2d", { willReadFrequently: true });
  const alphaContext = state.alphaCanvas.getContext("2d", { willReadFrequently: true });
  const overlayContext = overlayCanvas?.getContext("2d", { willReadFrequently: true }) || null;

  function isTypingContext(target) {
    if (!(target instanceof HTMLElement)) {
      return false;
    }
    const tagName = target.tagName;
    return (
      tagName === "INPUT" ||
      tagName === "TEXTAREA" ||
      tagName === "SELECT" ||
      target.isContentEditable
    );
  }

  function selectedMaskNames() {
    return Array.from(state.selectedMasks).sort();
  }

  function activeTarget(payload = state.workbench) {
    return payload?.targets?.find((target) => target.target_id === payload.active_target_id) || null;
  }

  function activePreset(payload = state.workbench) {
    return activeTarget(payload)?.refine_preset || "balanced";
  }

  function reviewStatusEndpoint(jobId = state.workbench?.latest_job_id) {
    return jobId ? `/api/jobs/${jobId}` : null;
  }

  function sourceVideoEndpointFor(jobId = state.workbench?.latest_job_id) {
    return jobId ? `/api/jobs/${jobId}/source-video` : root.dataset.sourceVideoUrl;
  }

  function reviewPreviewEndpoint(jobId, kind) {
    return jobId ? `/api/jobs/${jobId}/artifacts/${kind}` : null;
  }

  function workflowStepIndex(step = state.workbench?.workflow_step) {
    return WORKFLOW_STEPS.indexOf(step || "clip");
  }

  function activeSidebarTab(payload = state.workbench) {
    return payload?.active_sidebar_tab || "targets";
  }

  function updateRangeOutput(outputElement, value, suffix = "%") {
    if (!outputElement) {
      return;
    }
    outputElement.value = `${value}${suffix}`;
    outputElement.textContent = `${value}${suffix}`;
  }

  function syncSidebarPanels(payload = state.workbench) {
    const activeTab = activeSidebarTab(payload);
    sidebarTabButtons.forEach((button) => {
      button.toggleAttribute("data-active", button.dataset.sidebarTab === activeTab);
    });
    ["targets", "refine", "export"].forEach((tabName) => {
      const panel = document.getElementById(`sidebar-panel-${tabName}`);
      if (!panel) {
        return;
      }
      panel.hidden = tabName !== activeTab;
    });
  }

  function syncWorkflowStepper(payload = state.workbench) {
    const step = payload?.workflow_step || "clip";
    workflowButtons.forEach((button) => {
      const disableReview = button.dataset.workflowStep === "review" && !payload?.latest_job_id;
      button.toggleAttribute("disabled", disableReview);
      button.toggleAttribute("data-active", button.dataset.workflowStep === step);
    });
    workspaceNavBack?.toggleAttribute("disabled", !payload?.can_go_back);
    workspaceNavNext?.toggleAttribute("disabled", !payload?.can_go_next);
    if (workspaceReturnToClip) {
      workspaceReturnToClip.hidden = step !== "review";
    }
    if (workspaceReturnToRefine) {
      workspaceReturnToRefine.hidden = step !== "review";
    }
    if (reviewSidebar) {
      reviewSidebar.hidden = step !== "review";
    }
  }

  function frameToSeconds(frameIndex, payload = state.workbench) {
    const fps = Number(payload?.fps || state.fps || 0);
    if (!Number.isFinite(fps) || fps <= 0) {
      return 0;
    }
    return frameIndex / fps;
  }

  function formatFrameTimestamp(frameIndex, payload = state.workbench) {
    return formatDuration(frameToSeconds(frameIndex, payload));
  }

  function hasTemplateFrame(payload = state.workbench) {
    return payload?.template_frame_index !== null && payload?.template_frame_index !== undefined;
  }

  function clampFrame(frameIndex, minFrame, maxFrame) {
    return Math.max(minFrame, Math.min(maxFrame, frameIndex));
  }

  function cancelOverlayLoop() {
    if (state.overlayFrameHandle !== null) {
      window.cancelAnimationFrame(state.overlayFrameHandle);
      state.overlayFrameHandle = null;
    }
  }

  function clearOverlayCanvas() {
    cancelOverlayLoop();
    if (overlayContext && overlayCanvas) {
      overlayContext.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
    }
    if (overlayCanvas) {
      overlayCanvas.hidden = true;
    }
    overlayForegroundVideo?.pause();
    overlayAlphaVideo?.pause();
  }

  function ensureMediaSource(videoNode, url) {
    if (!videoNode || !url) {
      return false;
    }
    if (videoNode.dataset.assetUrl === url) {
      return false;
    }
    videoNode.dataset.assetUrl = url;
    videoNode.src = withCacheBust(url);
    videoNode.load();
    return true;
  }

  function previewCaption(mode, payload = state.reviewPayload || state.workbench) {
    if (mode === "overlay") {
      return payload?.preview_artifacts?.foreground && payload?.preview_artifacts?.alpha
        ? "Overlay preview is compositing browser-safe foreground and alpha streams."
        : "Overlay preview becomes available after foreground and alpha preview streams are ready.";
    }
    if (mode === "alpha") {
      return payload?.preview_artifacts?.alpha
        ? "Alpha preview is using the browser-safe matte stream."
        : "Alpha preview becomes available after export preview generation.";
    }
    if (mode === "foreground") {
      return payload?.preview_artifacts?.foreground
        ? "Foreground preview is using the browser-safe rendered foreground stream."
        : "Foreground preview becomes available after export preview generation.";
    }
    return "Source preview uses the browser-safe clip preview for clip selection and result comparison.";
  }

  function renderReviewSummaryList(targetNode, summary, payload) {
    if (!targetNode) {
      return;
    }
    const rows = [];
    if (summary) {
      rows.push(["Source", summary.source_name || "Unknown source"]);
      if (Number.isInteger(summary.process_start_frame_index) && Number.isInteger(summary.process_end_frame_index)) {
        const fps = Number(summary.source_fps || 0);
        const label = fps > 0
          ? `Frame ${summary.process_start_frame_index}-${summary.process_end_frame_index} | ${formatDuration(summary.process_start_frame_index / fps)} - ${formatDuration(summary.process_end_frame_index / fps)}`
          : `Frame ${summary.process_start_frame_index}-${summary.process_end_frame_index}`;
        rows.push(["Process range", label]);
      }
      rows.push(["Anchor", `Frame ${summary.template_frame_index ?? "-"}`]);
      rows.push(["Selected masks", Array.isArray(summary.selected_masks) && summary.selected_masks.length ? summary.selected_masks.join(", ") : "None"]);
      const presetMap = summary.selected_mask_presets || {};
      if (Object.keys(presetMap).length > 0) {
        rows.push(["Presets", Object.entries(presetMap).map(([mask, preset]) => `${mask}: ${preset}`).join(" | ")]);
      }
      if (summary.process_range_duration_seconds) {
        rows.push(["Duration", formatDuration(summary.process_range_duration_seconds)]);
      }
    }
    if (payload?.status_label) {
      rows.splice(1, 0, ["Status", payload.status_label]);
    }
    targetNode.innerHTML = "";
    rows.forEach(([labelText, valueText]) => {
      const row = document.createElement("div");
      const dt = document.createElement("dt");
      const dd = document.createElement("dd");
      dt.textContent = labelText;
      dd.textContent = valueText;
      row.append(dt, dd);
      targetNode.appendChild(row);
    });
  }

  function renderReviewTargets(summary) {
    if (!targetReviewList) {
      return;
    }
    const selectedMasks = Array.isArray(summary?.selected_masks) ? summary.selected_masks : [];
    const presetMap = summary?.selected_mask_presets || {};
    targetReviewList.innerHTML = "";
    if (selectedMasks.length === 0) {
      const empty = document.createElement("li");
      empty.className = "target-review-card target-review-card--empty";
      empty.textContent = "No saved masks selected for export.";
      targetReviewList.appendChild(empty);
      return;
    }
    selectedMasks.forEach((maskName, index) => {
      const item = document.createElement("li");
      item.className = "target-review-card";
      item.innerHTML = `
        <div class="target-review-card__header">
          <div>
            <p class="target-review-card__title">Target ${index + 1}</p>
            <p class="target-review-card__subtitle">${maskName}</p>
          </div>
          <span class="artifact-card__state">Included</span>
        </div>
      `;
      const meta = document.createElement("dl");
      meta.className = "target-review-meta";
      [["Mask", maskName], ["Preset", presetMap[maskName] || "balanced"], ["Export", "Merged in current job"]].forEach(([labelText, valueText]) => {
        const row = document.createElement("div");
        const dt = document.createElement("dt");
        const dd = document.createElement("dd");
        dt.textContent = labelText;
        dd.textContent = valueText;
        row.append(dt, dd);
        meta.appendChild(row);
      });
      item.appendChild(meta);
      targetReviewList.appendChild(item);
    });
  }

  function renderReviewArtifacts(artifactDetails) {
    if (!artifactSummaryList) {
      return;
    }
    artifactSummaryList.innerHTML = "";
    Object.values(artifactDetails || {}).forEach((artifact) => {
      const item = document.createElement("li");
      item.className = "artifact-card";
      item.dataset.available = artifact.available ? "true" : "false";
      item.innerHTML = `
        <div class="artifact-card__header">
          <div>
            <p class="artifact-card__label">${artifact.label}</p>
            <p class="artifact-card__name">${artifact.name}</p>
          </div>
          <span class="artifact-card__state">${artifact.available ? "Ready" : "Pending"}</span>
        </div>
        <p class="artifact-card__meta">${artifact.available ? `${artifact.kind.replace("_", " ")} | ${artifact.size_label || "Available"}` : `${artifact.kind.replace("_", " ")} | Waiting for export`}</p>
      `;
      if (artifact.available && artifact.url) {
        const link = document.createElement("a");
        link.className = "artifact-card__link";
        link.href = artifact.url;
        link.textContent = "Download";
        item.appendChild(link);
      }
      artifactSummaryList.appendChild(item);
    });
  }

  function renderReviewTimeline(timeline) {
    if (!jobTimeline) {
      return;
    }
    jobTimeline.innerHTML = "";
    (timeline || []).forEach((step) => {
      const item = document.createElement("li");
      item.className = "timeline-step";
      item.dataset.state = step.state;
      item.innerHTML = `
        <span class="timeline-step__dot" aria-hidden="true"></span>
        <div class="timeline-step__copy">
          <p class="timeline-step__label">${step.label}</p>
          <p class="timeline-step__state">${step.state}</p>
        </div>
      `;
      jobTimeline.appendChild(item);
    });
  }

  function renderReviewWarning(payload) {
    if (!warningPanel || !warningTitle || !warningCopy) {
      return;
    }
    const copy = payload?.error_text || payload?.warning_text;
    if (!copy) {
      warningPanel.hidden = true;
      warningTitle.textContent = "";
      warningCopy.textContent = "";
      return;
    }
    warningPanel.hidden = false;
    warningPanel.dataset.state = payload.error_text ? "error" : "warning";
    warningTitle.textContent = payload.error_text ? "Failure reported" : "Warning";
    warningCopy.textContent = copy;
  }

  function drawOverlayFrame() {
    if (
      state.canvasMode !== "overlay" ||
      !overlayCanvas ||
      !overlayContext ||
      !keyframeVideo ||
      !overlayForegroundVideo ||
      !overlayAlphaVideo
    ) {
      cancelOverlayLoop();
      return;
    }

    if (
      overlayForegroundVideo.readyState < 2 ||
      overlayAlphaVideo.readyState < 2 ||
      keyframeVideo.readyState < 2
    ) {
      state.overlayFrameHandle = window.requestAnimationFrame(drawOverlayFrame);
      return;
    }

    const width = overlayForegroundVideo.videoWidth || keyframeVideo.videoWidth;
    const height = overlayForegroundVideo.videoHeight || keyframeVideo.videoHeight;
    if (!width || !height) {
      state.overlayFrameHandle = window.requestAnimationFrame(drawOverlayFrame);
      return;
    }

    if (overlayCanvas.width !== width || overlayCanvas.height !== height) {
      overlayCanvas.width = width;
      overlayCanvas.height = height;
      state.foregroundCanvas.width = width;
      state.foregroundCanvas.height = height;
      state.alphaCanvas.width = width;
      state.alphaCanvas.height = height;
    }

    foregroundContext.clearRect(0, 0, width, height);
    alphaContext.clearRect(0, 0, width, height);
    foregroundContext.drawImage(overlayForegroundVideo, 0, 0, width, height);
    alphaContext.drawImage(overlayAlphaVideo, 0, 0, width, height);

    const foregroundFrame = foregroundContext.getImageData(0, 0, width, height);
    const alphaFrame = alphaContext.getImageData(0, 0, width, height);
    const composed = foregroundFrame.data;
    const matte = alphaFrame.data;

    for (let index = 0; index < composed.length; index += 4) {
      composed[index + 3] = matte[index];
    }

    overlayContext.clearRect(0, 0, width, height);
    overlayContext.putImageData(foregroundFrame, 0, 0);
    state.overlayFrameHandle = window.requestAnimationFrame(drawOverlayFrame);
  }

  function syncOverlayPlayback() {
    if (!keyframeVideo || !overlayForegroundVideo || !overlayAlphaVideo || state.canvasMode !== "overlay") {
      return;
    }
    const targetTime = keyframeVideo.currentTime || 0;
    const tolerance = 0.08;
    [overlayForegroundVideo, overlayAlphaVideo].forEach((videoNode) => {
      try {
        if (Math.abs((videoNode.currentTime || 0) - targetTime) > tolerance) {
          videoNode.currentTime = targetTime;
        }
      } catch (_error) {
        // Ignore sync jitter while metadata is loading.
      }
      videoNode.playbackRate = keyframeVideo.playbackRate || 1;
      if (keyframeVideo.paused) {
        videoNode.pause();
      } else {
        videoNode.play().catch(() => {});
      }
    });
  }

  function bindOverlayVideoSync() {
    if (!keyframeVideo || state.overlayVideosBound) {
      return;
    }
    const syncAndMaybeDraw = () => {
      syncOverlayPlayback();
      if (state.canvasMode === "overlay" && state.overlayFrameHandle === null) {
        state.overlayFrameHandle = window.requestAnimationFrame(drawOverlayFrame);
      }
    };
    ["play", "pause", "seeking", "seeked", "timeupdate", "ratechange", "loadeddata"].forEach((eventName) => {
      keyframeVideo.addEventListener(eventName, syncAndMaybeDraw);
    });
    state.overlayVideosBound = true;
  }

  function renderReviewPayload(payload) {
    state.reviewPayload = payload;
    renderReviewSummaryList(reviewSummaryList, payload.job_summary, payload);
    renderReviewSummaryList(reviewSummaryListSide, payload.job_summary, payload);
    renderReviewTargets(payload.job_summary);
    renderReviewArtifacts(payload.artifact_details);
    renderReviewTimeline(payload.timeline);
    renderReviewWarning(payload);
  }

  async function refreshReview(jobId = state.workbench?.latest_job_id) {
    const endpoint = reviewStatusEndpoint(jobId);
    if (!endpoint) {
      return null;
    }
    const payload = await parseJson(await fetch(endpoint));
    renderReviewPayload(payload);
    return payload;
  }

  function stopReviewPolling() {
    if (state.jobPollTimer !== null) {
      window.clearInterval(state.jobPollTimer);
      state.jobPollTimer = null;
    }
  }

  function ensureReviewPolling() {
    if (state.jobPollTimer !== null || !state.workbench?.latest_job_id) {
      return;
    }
    state.jobPollTimer = window.setInterval(async () => {
      try {
        const payload = await refreshReview();
        if (payload && TERMINAL_JOB_STATES.has(payload.status)) {
          stopReviewPolling();
        }
        if (state.workbench?.workflow_step === "review") {
          syncCanvasMode(state.workbench);
        }
      } catch (error) {
        stopReviewPolling();
        setStatus(status, error.message, true);
      }
    }, 2000);
  }

  function syncTimelineRangeRail(payload) {
    if (!timelineRangeRail || !timelineRangeSelection || !payload) {
      return;
    }
    const maxFrame = Math.max(1, (payload.frame_count || 1) - 1);
    const pendingStart = Math.min(state.rangeSelectionStart, state.rangeSelectionEnd);
    const pendingEnd = Math.max(state.rangeSelectionStart, state.rangeSelectionEnd);
    const appliedStartPercent = (state.rangeAppliedStart / maxFrame) * 100;
    const appliedEndPercent = (state.rangeAppliedEnd / maxFrame) * 100;
    const pendingStartPercent = (pendingStart / maxFrame) * 100;
    const pendingEndPercent = (pendingEnd / maxFrame) * 100;
    const rangeDirty = pendingStart !== state.rangeAppliedStart || pendingEnd !== state.rangeAppliedEnd;

    timelineRangeRail.style.setProperty("--applied-range-start", `${appliedStartPercent}%`);
    timelineRangeRail.style.setProperty("--applied-range-end", `${appliedEndPercent}%`);
    timelineRangeRail.style.setProperty("--pending-range-start", `${pendingStartPercent}%`);
    timelineRangeRail.style.setProperty("--pending-range-end", `${pendingEndPercent}%`);
    timelineRangeRail.dataset.rangeState = rangeDirty ? "pending" : "applied";
    timelineRangeSelection.dataset.rangeState = rangeDirty ? "pending" : "applied";
  }

  function syncKeyframeSummary(payload) {
    if (!payload) {
      return;
    }
    const maxFrame = Math.max(0, (payload.frame_count || 1) - 1);
    state.fps = Number(payload.fps || state.fps || 0);
    state.durationSeconds = Number(payload.duration_seconds || state.durationSeconds || 0);
    state.rangeAppliedStart = Number(payload.process_start_frame_index || 0);
    state.rangeAppliedEnd = Number(
      payload.process_end_frame_index ?? maxFrame
    );

    if (
      state.rangeSelectionStart === undefined
      || Number.isNaN(state.rangeSelectionStart)
      || state.rangeSelectionStart < 0
    ) {
      state.rangeSelectionStart = state.rangeAppliedStart;
    }
    if (
      state.rangeSelectionEnd === undefined
      || Number.isNaN(state.rangeSelectionEnd)
      || state.rangeSelectionEnd < 0
    ) {
      state.rangeSelectionEnd = state.rangeAppliedEnd;
    }

    state.rangeSelectionStart = clampFrame(state.rangeSelectionStart, 0, maxFrame);
    state.rangeSelectionEnd = clampFrame(state.rangeSelectionEnd, 0, maxFrame);
    if (state.rangeSelectionStart > state.rangeSelectionEnd) {
      const nextStart = state.rangeSelectionEnd;
      state.rangeSelectionEnd = state.rangeSelectionStart;
      state.rangeSelectionStart = nextStart;
    }

    state.templateFrameApplied = hasTemplateFrame(payload)
      ? Number(payload.template_frame_index)
      : null;
    if (
      state.templateFrameSelection === undefined
      || Number.isNaN(state.templateFrameSelection)
      || state.templateFrameSelection < state.rangeAppliedStart
      || state.templateFrameSelection > state.rangeAppliedEnd
    ) {
      state.templateFrameSelection = state.templateFrameApplied ?? state.rangeAppliedStart;
    }
    if (
      state.playheadFrame === undefined
      || Number.isNaN(state.playheadFrame)
      || state.playheadFrame < 0
      || state.playheadFrame > maxFrame
    ) {
      state.playheadFrame = state.templateFrameApplied ?? state.rangeAppliedStart;
    }

    if (sourcePlayheadSlider) {
      sourcePlayheadSlider.max = String(maxFrame);
      sourcePlayheadSlider.value = String(clampFrame(state.playheadFrame, 0, maxFrame));
    }

    if (timelineCurrentLabel) {
      timelineCurrentLabel.textContent = `Playhead · Frame ${state.playheadFrame} · ${formatFrameTimestamp(state.playheadFrame, payload)}`;
    }
    if (timelineSelectedLabel) {
      timelineSelectedLabel.textContent = `Pending range · Frame ${state.rangeSelectionStart} - ${state.rangeSelectionEnd}`;
    }
    if (timelineAppliedLabel) {
      timelineAppliedLabel.textContent = `Processing range · Frame ${state.rangeAppliedStart} - ${state.rangeAppliedEnd}`;
    }
    if (timelineInChip) {
      timelineInChip.textContent = `In · ${formatFrameTimestamp(state.rangeSelectionStart, payload)} · F${state.rangeSelectionStart}`;
    }
    if (timelineOutChip) {
      timelineOutChip.textContent = `Out · ${formatFrameTimestamp(state.rangeSelectionEnd, payload)} · F${state.rangeSelectionEnd}`;
    }
    if (timelineDurationChip) {
      const durationFrames = Math.max(1, state.rangeSelectionEnd - state.rangeSelectionStart + 1);
      const fps = Number(payload.fps || state.fps || 0);
      const duration = fps > 0 ? durationFrames / fps : 0;
      timelineDurationChip.textContent = `Duration · ${formatDuration(duration)} · ${durationFrames}f`;
    }

    if (templateFrameSlider) {
      templateFrameSlider.min = String(state.rangeAppliedStart);
      templateFrameSlider.max = String(state.rangeAppliedEnd);
      templateFrameSlider.value = String(state.templateFrameSelection);
    }
    updateRangeOutput(templateFrameValue, Number(state.templateFrameSelection || 0), "");

    if (anchorFrameSummary) {
      anchorFrameSummary.textContent = state.templateFrameApplied === null
        ? "Anchor · Not set"
        : `Anchor · Frame ${state.templateFrameApplied} · ${formatFrameTimestamp(state.templateFrameApplied, payload)}`;
    }
    if (keyframeSelectedLabel) {
      keyframeSelectedLabel.textContent = `Selected frame ${state.templateFrameSelection}`;
    }
    if (keyframeAppliedLabel) {
      keyframeAppliedLabel.textContent = state.templateFrameApplied === null
        ? "Applied frame Not set"
        : `Applied frame ${state.templateFrameApplied}`;
    }
    if (keyframeTimeLabel) {
      keyframeTimeLabel.textContent = `${formatFrameTimestamp(state.templateFrameSelection, payload)} / ${formatFrameTimestamp(state.rangeAppliedEnd, payload)}`;
    }

    syncTimelineRangeRail(payload);

    if (keyframeVideo) {
      if (!keyframeVideo.src) {
        keyframeVideo.src = root.dataset.sourceVideoUrl;
      }
      const desiredTime = frameToSeconds(state.playheadFrame, payload);
      if (Number.isFinite(desiredTime) && Math.abs((keyframeVideo.currentTime || 0) - desiredTime) > 0.04) {
        try {
          keyframeVideo.currentTime = desiredTime;
        } catch (_error) {
          // Ignore transient seek failures before metadata is ready.
        }
      }
    }
  }

  function syncTargetControls(payload) {
    const currentTarget = activeTarget(payload);
    if (!currentTarget) {
      return;
    }
    if (presetStrengthInput) {
      presetStrengthInput.value = String(Math.round((currentTarget.preset_strength || 0) * 100));
      updateRangeOutput(presetStrengthValue, Number(presetStrengthInput.value));
    }
    if (motionStrengthInput) {
      motionStrengthInput.value = String(Math.round((currentTarget.motion_strength || 0) * 100));
      updateRangeOutput(motionStrengthValue, Number(motionStrengthInput.value));
    }
    if (temporalStabilityInput) {
      temporalStabilityInput.value = String(Math.round((currentTarget.temporal_stability || 0) * 100));
      updateRangeOutput(temporalStabilityValue, Number(temporalStabilityInput.value));
    }
    if (edgeFeatherRadiusInput) {
      edgeFeatherRadiusInput.value = String(Math.round(currentTarget.edge_feather_radius || 0));
      updateRangeOutput(edgeFeatherRadiusValue, Number(edgeFeatherRadiusInput.value), " px");
    }
  }

  function applyImagePresentation() {
    if (!image || !keyframeVideo) {
      return;
    }
    const reviewMode = state.workbench?.workflow_step === "review";
    const showVideo = reviewMode || state.canvasMode === "source" || state.canvasMode === "alpha" || state.canvasMode === "foreground";
    keyframeVideo.hidden = !showVideo;
    image.hidden = showVideo || reviewMode;
    canvasFrame?.setAttribute("data-canvas-mode", state.canvasMode);

    if (showVideo) {
      image.style.opacity = "1";
      syncSourcePlaybackButton();
      return;
    }
    if (!keyframeVideo.paused) {
      keyframeVideo.pause();
    }
    image.style.opacity = String(state.overlayOpacity / 100);
    syncSourcePlaybackButton();
  }

  function syncSelectedMasks(payload) {
    const availableMaskNames = payload.mask_names || [];
    const available = new Set(availableMaskNames);
    const serverSelected = new Set(payload.selected_mask_names || []);

    if (state.selectedMasks.size === 0) {
      state.selectedMasks = serverSelected.size > 0
        ? serverSelected
        : new Set(availableMaskNames);
      return;
    }

    state.selectedMasks = new Set(
      Array.from(state.selectedMasks).filter((maskName) => available.has(maskName))
    );
    if (state.selectedMasks.size === 0 && serverSelected.size > 0) {
      state.selectedMasks = serverSelected;
    }
  }

  function syncToolButtons(payload) {
    const canEdit = payload?.can_apply_clicks ?? false;
    const pointPositive = state.activeTool === "point-positive";
    const pointNegative = state.activeTool === "point-negative";

    positiveButton?.toggleAttribute("data-active", pointPositive);
    negativeButton?.toggleAttribute("data-active", pointNegative);
    positiveButton?.toggleAttribute("disabled", !canEdit);
    negativeButton?.toggleAttribute("disabled", !canEdit);

    brushButtons.forEach((button) => {
      const isActive = state.activeTool === `brush-${button.dataset.brushMode}`;
      button.toggleAttribute("data-active", isActive);
      button.toggleAttribute("disabled", !canEdit);
    });

    if (image) {
      image.dataset.editable = canEdit ? "true" : "false";
      image.style.cursor = canEdit ? "crosshair" : "default";
    }
  }

  function renderSavedMasks(maskNames) {
    if (!savedMaskList) {
      return;
    }
    savedMaskList.innerHTML = "";
    maskNames.forEach((maskName) => {
      const label = document.createElement("label");
      const input = document.createElement("input");
      input.type = "checkbox";
      input.name = "mask_name";
      input.value = maskName;
      input.checked = state.selectedMasks.has(maskName);
      input.addEventListener("change", () => {
        if (input.checked) {
          state.selectedMasks.add(maskName);
        } else {
          state.selectedMasks.delete(maskName);
        }
        syncActionState(state.workbench);
      });
      label.appendChild(input);
      label.append(` ${maskName}`);
      savedMaskList.appendChild(label);
    });
  }

  async function updateTarget(targetId, patch, pendingMessage, successMessage) {
    setStatus(status, pendingMessage, false);
    try {
      const payload = await requestTargetPatch(targetId, patch);
      renderWorkbench(payload);
      setStatus(status, successMessage(payload), false);
    } catch (error) {
      setStatus(status, error.message, true);
    }
  }

  async function requestTargetPatch(targetId, patch) {
    return parseJson(
      await fetch(`${root.dataset.targetsEndpoint}/${targetId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(patch),
      })
    );
  }

  function renderTargets(targets, activeTargetId) {
    if (!targetList) {
      return;
    }
    targetList.innerHTML = "";
    targets.forEach((target) => {
      const card = document.createElement("article");
      card.className = "target-card";
      card.dataset.selected = target.target_id === activeTargetId ? "true" : "false";
      card.dataset.hidden = target.visible ? "false" : "true";
      card.dataset.locked = target.locked ? "true" : "false";

      const selectButton = document.createElement("button");
      selectButton.type = "button";
      selectButton.className = "target-card__select";
      selectButton.innerHTML = `
        <span class="target-card__name">${target.name}</span>
        <span class="target-card__meta">${target.point_count} point${target.point_count === 1 ? "" : "s"} | ${PRESET_META[target.refine_preset]?.label || "Balanced"} | ${target.saved_mask_name || "unsaved"} | ${target.visible ? "visible" : "hidden"} | ${target.locked ? "locked" : "editable"}</span>
      `;
      selectButton.addEventListener("click", async () => {
        if (target.target_id === activeTargetId) {
          return;
        }
        setStatus(status, `Switching to ${target.name}...`, false);
        try {
          const payload = await parseJson(
            await fetch(`${root.dataset.targetsEndpoint}/${target.target_id}/select`, {
              method: "POST",
            })
          );
          renderWorkbench(payload);
          setStatus(status, `Active target: ${target.name}.`, false);
        } catch (error) {
          setStatus(status, error.message, true);
        }
      });

      const actions = document.createElement("div");
      actions.className = "target-card__actions";

      const visibilityButton = document.createElement("button");
      visibilityButton.type = "button";
      visibilityButton.className = "target-chip";
      visibilityButton.textContent = target.visible ? "Hide" : "Show";
      visibilityButton.addEventListener("click", () => {
        const nextVisible = !target.visible;
        updateTarget(
          target.target_id,
          { visible: nextVisible },
          `${nextVisible ? "Showing" : "Hiding"} ${target.name}...`,
          () => `${target.name} is now ${nextVisible ? "visible" : "hidden"}.`
        );
      });

      const lockButton = document.createElement("button");
      lockButton.type = "button";
      lockButton.className = "target-chip";
      lockButton.textContent = target.locked ? "Unlock" : "Lock";
      lockButton.addEventListener("click", () => {
        const nextLocked = !target.locked;
        updateTarget(
          target.target_id,
          { locked: nextLocked },
          `${nextLocked ? "Locking" : "Unlocking"} ${target.name}...`,
          () => `${target.name} is now ${nextLocked ? "locked" : "editable"}.`
        );
      });

      actions.append(visibilityButton, lockButton);
      card.append(selectButton, actions);
      targetList.appendChild(card);
    });
  }

  function syncActionState(payload) {
    if (!payload) {
      return;
    }
    const canSubmit = payload.workflow_step !== "review"
      && payload.can_submit
      && state.selectedMasks.size > 0
      && hasTemplateFrame(payload);
    const rangeDirty = (
      state.rangeSelectionStart !== state.rangeAppliedStart
      || state.rangeSelectionEnd !== state.rangeAppliedEnd
    );
    const rangePendingCompletion = (
      state.rangeSelectionTouchedStart !== state.rangeSelectionTouchedEnd
    );
    root.dataset.stage = payload.stage;
    root.dataset.editable = payload.can_apply_clicks ? "true" : "false";
    root.dataset.workflowStep = payload.workflow_step || "clip";

    createTargetButton?.toggleAttribute("disabled", !payload.can_create_target);
    undoButton?.toggleAttribute("disabled", !payload.can_undo_clicks);
    resetButton?.toggleAttribute("disabled", !payload.can_reset_target);
    saveButton?.toggleAttribute("disabled", !payload.can_save_current_target);
    submitButton?.toggleAttribute("disabled", !canSubmit);
    applyTargetNameButton?.toggleAttribute("disabled", !payload.active_target_id);
    markRangeInButton?.toggleAttribute("disabled", !payload.can_apply_range);
    markRangeOutButton?.toggleAttribute("disabled", !payload.can_apply_range);
    clearRangeSelectionButton?.toggleAttribute("disabled", !payload.can_apply_range);
    sourcePlayheadSlider?.toggleAttribute("disabled", !payload.can_apply_range);
    templateFrameSlider?.toggleAttribute("disabled", !payload.can_change_template_frame || rangeDirty || rangePendingCompletion);
    toggleSourcePlaybackButton?.toggleAttribute("disabled", state.canvasMode !== "source");
    const currentTarget = activeTarget(payload);
    toggleTargetLockButton?.toggleAttribute("disabled", !currentTarget);
    if (toggleTargetLockButton && currentTarget) {
      toggleTargetLockButton.textContent = currentTarget.locked ? "Unlock Target" : "Lock Target";
    }

    if (submitButton) {
      submitButton.textContent = payload.workflow_step === "review"
        ? "Job Queued"
        : "Submit Matting Job";
    }
    if (timelineSelectedLabel) {
      timelineSelectedLabel.dataset.pending = rangeDirty || rangePendingCompletion ? "true" : "false";
    }
    if (anchorRail) {
      anchorRail.hidden = !hasTemplateFrame(payload) && payload.workflow_step === "clip";
    }

    syncToolButtons(payload);
    syncWorkflowStepper(payload);
    syncSidebarPanels(payload);
  }

  function resolveCanvasUrl(payload) {
    if (state.canvasMode === "mask") {
      return payload.active_mask_url || payload.current_mask_url || payload.template_frame_url || root.dataset.templateFrameUrl;
    }
    if (state.canvasMode === "source") {
      return payload.template_frame_url || root.dataset.templateFrameUrl;
    }
    return payload.current_preview_url || payload.template_frame_url || root.dataset.templateFrameUrl;
  }

  function syncCanvasMode(payload) {
    const reviewMode = payload.workflow_step === "review";
    if (!reviewMode && !hasTemplateFrame(payload) && state.canvasMode !== "source") {
      state.canvasMode = "source";
    }
    if (!reviewMode && state.canvasMode === "mask" && !payload.active_mask_url && !payload.current_mask_url) {
      state.canvasMode = payload.current_preview_url ? "overlay" : "source";
    }

    const modeLabelMap = {
      source: "Source plate",
      overlay: reviewMode ? "Overlay review" : "Overlay preview",
      mask: "Mask inspection",
      alpha: "Alpha review",
      foreground: "Foreground review",
    };
    if (canvasModeLabel) {
      canvasModeLabel.textContent = `${payload.canvas_mode_label || "Guided silhouette pass"} | ${modeLabelMap[state.canvasMode] || "Source plate"}`;
    }

    viewButtons.forEach((button) => {
      const mode = button.dataset.canvasMode;
      const isReviewOnly = mode === "alpha" || mode === "foreground";
      const disabled = reviewMode
        ? (mode === "overlay" && !(state.reviewPayload?.preview_artifacts?.foreground && state.reviewPayload?.preview_artifacts?.alpha))
          || (mode === "alpha" && !state.reviewPayload?.preview_artifacts?.alpha)
          || (mode === "foreground" && !state.reviewPayload?.preview_artifacts?.foreground)
          || false
        : isReviewOnly
          || (mode === "mask" && (!hasTemplateFrame(payload) || (!payload.active_mask_url && !payload.current_mask_url)))
          || (mode === "overlay" && !hasTemplateFrame(payload));
      button.toggleAttribute("disabled", disabled);
      button.toggleAttribute("data-active", mode === state.canvasMode);
    });

    if (reviewMode) {
      const sourceUrl = sourceVideoEndpointFor(payload.latest_job_id);
      const foregroundUrl = reviewPreviewEndpoint(payload.latest_job_id, "preview_foreground.mp4");
      const alphaUrl = reviewPreviewEndpoint(payload.latest_job_id, "preview_alpha.mp4");
      clearOverlayCanvas();
      image.hidden = true;
      if (state.canvasMode === "overlay" && sourceUrl && foregroundUrl && alphaUrl) {
        bindOverlayVideoSync();
        ensureMediaSource(keyframeVideo, sourceUrl);
        ensureMediaSource(overlayForegroundVideo, foregroundUrl);
        ensureMediaSource(overlayAlphaVideo, alphaUrl);
        keyframeVideo.hidden = false;
        overlayCanvas.hidden = false;
        syncOverlayPlayback();
        if (state.overlayFrameHandle === null) {
          state.overlayFrameHandle = window.requestAnimationFrame(drawOverlayFrame);
        }
      } else {
        const previewUrl = state.canvasMode === "alpha"
          ? alphaUrl
          : state.canvasMode === "foreground"
            ? foregroundUrl
            : sourceUrl;
        ensureMediaSource(keyframeVideo, previewUrl || sourceUrl);
        keyframeVideo.hidden = false;
      }
      return;
    }

    clearOverlayCanvas();
    ensureMediaSource(keyframeVideo, root.dataset.sourceVideoUrl);
    if (image) {
      image.src = withCacheBust(resolveCanvasUrl(payload));
      image.alt = {
        source: `Template frame for ${payload.draft_id}`,
        overlay: `Overlay preview for ${payload.draft_id}`,
        mask: `Mask preview for ${payload.draft_id}`,
      }[state.canvasMode];
    }
    applyImagePresentation();
  }

  function syncPresetButtons(payload) {
    const preset = activePreset(payload);
    presetButtons.forEach((button) => {
      button.toggleAttribute("data-active", button.dataset.preset === preset);
    });
    if (inspectorPreset) {
      inspectorPreset.textContent = PRESET_META[preset]?.label || "Balanced";
    }
    if (presetNote) {
      presetNote.textContent = PRESET_META[preset]?.note || PRESET_META.balanced.note;
    }
  }

  function renderWorkbench(payload) {
    const rangeChangedOnServer = (
      state.rangeAppliedStart !== Number(payload.process_start_frame_index || 0)
      || state.rangeAppliedEnd !== Number(payload.process_end_frame_index ?? Math.max(0, (payload.frame_count || 1) - 1))
    );
    const templateChangedOnServer = (
      state.templateFrameApplied !== (hasTemplateFrame(payload) ? Number(payload.template_frame_index) : null)
    );
    state.workbench = payload;
    syncSelectedMasks(payload);
    if (rangeChangedOnServer || (!state.rangeSelectionTouchedStart && !state.rangeSelectionTouchedEnd)) {
      state.rangeSelectionStart = Number(payload.process_start_frame_index || 0);
      state.rangeSelectionEnd = Number(
        payload.process_end_frame_index ?? Math.max(0, (payload.frame_count || 1) - 1)
      );
      state.rangeSelectionTouchedStart = false;
      state.rangeSelectionTouchedEnd = false;
    }
    if (
      templateChangedOnServer
      || state.templateFrameSelection === state.templateFrameApplied
      || state.templateFrameApplied === null
    ) {
      state.templateFrameSelection = hasTemplateFrame(payload)
        ? Number(payload.template_frame_index)
        : Number(payload.process_start_frame_index || 0);
    }
    if (rangeChangedOnServer || templateChangedOnServer || state.playheadFrame === undefined || Number.isNaN(state.playheadFrame)) {
      state.playheadFrame = hasTemplateFrame(payload)
        ? Number(payload.template_frame_index)
        : Number(payload.process_start_frame_index || 0);
    }

    const currentTarget = activeTarget(payload);
    syncTargetControls(payload);

    syncCanvasMode(payload);
    syncPresetButtons(payload);

    if (canvasStageNote) {
      canvasStageNote.textContent = hasTemplateFrame(payload)
        ? (payload.stage_note || "")
        : "Range changed. Re-apply an anchor frame to continue annotation.";
    }
    if (guidanceTitle) {
      guidanceTitle.textContent = payload.stage_label || "Coarse Selection";
    }
    if (guidanceCopy) {
      guidanceCopy.textContent = payload.stage_note || "";
    }
    if (workflowStageChip) {
      workflowStageChip.textContent = (payload.workflow_step || payload.stage || "clip").toUpperCase();
    }
    if (selectionNote) {
      selectionNote.textContent = !hasTemplateFrame(payload)
        ? "Mark the processing segment, then choose an anchor frame before placing points."
        : payload.stage === "preview"
        ? "Preview is locked. Return to coarse or refine before placing more points."
        : "Use points to establish the person first, then switch into presets or brush cleanup.";
    }
    if (brushNote) {
      brushNote.textContent = !hasTemplateFrame(payload)
        ? "Brush refinement stays locked until an anchor frame has been applied inside the green processing segment."
        : payload.stage === "preview"
        ? "Brush refinement is disabled in preview mode."
        : "Brush actions edit the active mask directly, which is useful when SAM3 gets the rough silhouette but misses small edge corrections.";
    }
    if (presetNote && payload.active_sidebar_tab === "refine") {
      presetNote.textContent = `${PRESET_META[activePreset(payload)]?.note || PRESET_META.balanced.note} Every refine control updates the main monitor directly.`;
    }

    if (inspectorStage) {
      inspectorStage.textContent = payload.workflow_step || payload.stage;
    }
    if (inspectorTarget) {
      inspectorTarget.textContent = currentTarget
        ? `${currentTarget.name}${currentTarget.locked ? " | Locked" : ""}${currentTarget.visible ? "" : " | Hidden"}`
        : "-";
    }
    if (inspectorPoints) {
      inspectorPoints.textContent = String(currentTarget?.point_count || 0);
    }
    if (inspectorMask) {
      inspectorMask.textContent = currentTarget?.saved_mask_name || "Not saved yet";
    }
    if (targetNameInput && currentTarget) {
      targetNameInput.value = currentTarget.name;
      targetNameInput.disabled = false;
    }
    syncKeyframeSummary(payload);
    if (targetSummary) {
      targetSummary.textContent = currentTarget
        ? `${currentTarget.name} is ${currentTarget.visible ? "visible" : "hidden"}, ${currentTarget.locked ? "locked" : "editable"}, and uses the ${PRESET_META[currentTarget.refine_preset]?.label || "Balanced"} preset.`
        : "No active target selected.";
    }

    renderTargets(payload.targets || [], payload.active_target_id);
    renderSavedMasks(payload.mask_names || []);
    syncActionState(payload);
    if (payload.latest_job_id) {
      void refreshReview(payload.latest_job_id).then((reviewPayload) => {
        if (reviewPayload && payload.workflow_step === "review") {
          syncCanvasMode(payload);
        }
      }).catch((error) => {
        setStatus(status, error.message, true);
      });
      ensureReviewPolling();
    } else {
      stopReviewPolling();
      state.reviewPayload = null;
      renderReviewSummaryList(reviewSummaryList, null, null);
      renderReviewSummaryList(reviewSummaryListSide, null, null);
      renderReviewTargets(null);
      renderReviewArtifacts({});
      renderReviewTimeline([]);
      renderReviewWarning({});
    }
  }

  async function refreshWorkbench() {
    const payload = await parseJson(await fetch(root.dataset.workbenchEndpoint));
    renderWorkbench(payload);
    return payload;
  }

  function setActiveTool(nextTool) {
    state.activeTool = nextTool;
    syncToolButtons(state.workbench);
  }

  function setCanvasMode(nextCanvasMode) {
    state.canvasMode = nextCanvasMode;
    if (state.workbench) {
      syncCanvasMode(state.workbench);
    }
  }

  positiveButton?.addEventListener("click", () => setActiveTool("point-positive"));
  negativeButton?.addEventListener("click", () => setActiveTool("point-negative"));

  brushButtons.forEach((button) => {
    button.addEventListener("click", () => {
      setActiveTool(`brush-${button.dataset.brushMode}`);
      setStatus(status, `${button.textContent} tool ready. Click the canvas to refine the mask.`, false);
    });
  });

  brushRadiusInput?.addEventListener("input", () => {
    state.brushRadius = Number(brushRadiusInput.value);
    if (brushRadiusValue) {
      brushRadiusValue.value = `${state.brushRadius} px`;
      brushRadiusValue.textContent = `${state.brushRadius} px`;
    }
  });

  overlayOpacityInput?.addEventListener("input", () => {
    state.overlayOpacity = Number(overlayOpacityInput.value);
    updateRangeOutput(overlayOpacityValue, state.overlayOpacity);
    applyImagePresentation();
  });

  function seekVideoToFrame(frameIndex, payload = state.workbench) {
    if (!keyframeVideo || !payload) {
      return;
    }
    const desiredTime = frameToSeconds(frameIndex, payload);
    if (!Number.isFinite(desiredTime)) {
      return;
    }
    try {
      keyframeVideo.currentTime = desiredTime;
    } catch (_error) {
      // Ignore transient seek failures before metadata is ready.
    }
  }

  function syncSourcePlaybackButton() {
    if (!toggleSourcePlaybackButton || !keyframeVideo) {
      return;
    }
    const canPlay = state.canvasMode === "source";
    toggleSourcePlaybackButton.disabled = !canPlay;
    toggleSourcePlaybackButton.textContent = keyframeVideo.paused ? "Play" : "Pause";
  }

  function syncPlayheadFromVideo() {
    const payload = state.workbench;
    if (!payload) {
      return;
    }
    const fps = Number(payload.fps || state.fps || 0);
    if (!Number.isFinite(fps) || fps <= 0) {
      return;
    }
    const nextFrame = clampFrame(
      Math.round((keyframeVideo?.currentTime || 0) * fps),
      0,
      Math.max(0, (payload.frame_count || 1) - 1)
    );
    state.playheadFrame = nextFrame;
    if (sourcePlayheadSlider) {
      sourcePlayheadSlider.value = String(nextFrame);
    }
    syncKeyframeSummary(payload);
    syncActionState(payload);
  }

  function clearPendingRangeSelection() {
    const payload = state.workbench;
    if (!payload) {
      return;
    }
    state.rangeSelectionStart = state.rangeAppliedStart;
    state.rangeSelectionEnd = state.rangeAppliedEnd;
    state.rangeSelectionTouchedStart = false;
    state.rangeSelectionTouchedEnd = false;
    syncKeyframeSummary(payload);
    syncActionState(payload);
  }

  async function applyRangeSelection() {
    const payload = state.workbench;
    if (!payload) {
      return;
    }
    const nextStart = Math.min(state.rangeSelectionStart, state.rangeSelectionEnd);
    const nextEnd = Math.max(state.rangeSelectionStart, state.rangeSelectionEnd);
    if (
      nextStart === state.rangeAppliedStart
      && nextEnd === state.rangeAppliedEnd
    ) {
      state.rangeSelectionTouchedStart = false;
      state.rangeSelectionTouchedEnd = false;
      syncKeyframeSummary(payload);
      syncActionState(payload);
      return;
    }

    const hasExistingAnnotations = (
      (payload.mask_names || []).length > 0
      || hasTemplateFrame(payload)
      || payload.current_mask_url
      || payload.current_preview_url
    );
    if (hasExistingAnnotations) {
      const shouldContinue = window.confirm(
        "Changing the processing segment will clear the current anchor, current preview, and every saved mask. Continue?"
      );
      if (!shouldContinue) {
        clearPendingRangeSelection();
        return;
      }
    }

    setStatus(status, `Applying segment ${nextStart} - ${nextEnd}...`, false);
    try {
      const nextPayload = await parseJson(
        await fetch(root.dataset.processingRangeEndpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            start_frame_index: nextStart,
            end_frame_index: nextEnd,
          }),
        })
      );
      state.rangeSelectionTouchedStart = false;
      state.rangeSelectionTouchedEnd = false;
      state.canvasMode = "source";
      renderWorkbench(nextPayload);
      setStatus(
        status,
        "Range changed. Re-apply an anchor frame to continue annotation.",
        false
      );
    } catch (error) {
      setStatus(status, error.message, true);
    }
  }

  function markRangeBoundary(boundary) {
    const payload = state.workbench;
    if (!payload) {
      return;
    }
    if (state.canvasMode !== "source") {
      setCanvasMode("source");
    }
    const frame = clampFrame(
      state.playheadFrame,
      0,
      Math.max(0, (payload.frame_count || 1) - 1)
    );
    if (boundary === "start") {
      state.rangeSelectionStart = frame;
      state.rangeSelectionTouchedStart = true;
      if (state.rangeSelectionStart > state.rangeSelectionEnd) {
        state.rangeSelectionEnd = state.rangeSelectionStart;
      }
    } else {
      state.rangeSelectionEnd = frame;
      state.rangeSelectionTouchedEnd = true;
      if (state.rangeSelectionEnd < state.rangeSelectionStart) {
        state.rangeSelectionStart = state.rangeSelectionEnd;
      }
    }

    syncKeyframeSummary(payload);
    syncActionState(payload);
    if (state.rangeSelectionTouchedStart && state.rangeSelectionTouchedEnd) {
      void applyRangeSelection();
      return;
    }

    setStatus(
      status,
      boundary === "start"
        ? `In point set to frame ${state.rangeSelectionStart}. Mark Out to confirm the segment.`
        : `Out point set to frame ${state.rangeSelectionEnd}. Mark In to confirm the segment.`,
      false
    );
  }

  async function applyTemplateFrameSelection() {
    const payload = state.workbench;
    if (!payload || !templateFrameSlider || templateFrameSlider.disabled) {
      return;
    }
    const nextFrame = clampFrame(
      state.templateFrameSelection,
      state.rangeAppliedStart,
      state.rangeAppliedEnd
    );
    if (hasTemplateFrame(payload) && nextFrame === Number(payload.template_frame_index || 0)) {
      return;
    }
    setStatus(status, `Switching template frame to ${nextFrame}...`, false);
    try {
      const nextPayload = await parseJson(
        await fetch(root.dataset.templateFrameEndpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ frame_index: nextFrame }),
        })
      );
      state.playheadFrame = nextFrame;
      renderWorkbench(nextPayload);
      setStatus(
        status,
        `Template frame ${nextPayload.template_frame_index} is now active. Existing unsaved annotations were reset.`,
        false
      );
    } catch (error) {
      setStatus(status, error.message, true);
    }
  }

  sourcePlayheadSlider?.addEventListener("input", () => {
    const payload = state.workbench;
    if (!payload) {
      return;
    }
    if (state.canvasMode !== "source") {
      setCanvasMode("source");
    }
    state.playheadFrame = clampFrame(
      Number(sourcePlayheadSlider.value),
      0,
      Math.max(0, (payload.frame_count || 1) - 1)
    );
    syncKeyframeSummary(payload);
    syncActionState(payload);
    seekVideoToFrame(state.playheadFrame, payload);
  });

  markRangeInButton?.addEventListener("click", () => {
    if (markRangeInButton.disabled) {
      return;
    }
    markRangeBoundary("start");
  });

  markRangeOutButton?.addEventListener("click", () => {
    if (markRangeOutButton.disabled) {
      return;
    }
    markRangeBoundary("end");
  });

  clearRangeSelectionButton?.addEventListener("click", () => {
    if (clearRangeSelectionButton.disabled) {
      return;
    }
    clearPendingRangeSelection();
    setStatus(status, "Pending range marks cleared.", false);
  });

  templateFrameSlider?.addEventListener("input", () => {
    const payload = state.workbench;
    if (!payload) {
      return;
    }
    state.templateFrameSelection = clampFrame(
      Number(templateFrameSlider.value),
      state.rangeAppliedStart,
      state.rangeAppliedEnd
    );
    state.playheadFrame = state.templateFrameSelection;
    syncKeyframeSummary(payload);
    syncActionState(payload);
    seekVideoToFrame(state.playheadFrame, payload);
  });

  templateFrameSlider?.addEventListener("change", () => {
    void applyTemplateFrameSelection();
  });

  toggleSourcePlaybackButton?.addEventListener("click", async () => {
    if (!keyframeVideo || toggleSourcePlaybackButton.disabled) {
      return;
    }
    try {
      if (keyframeVideo.paused) {
        await keyframeVideo.play();
      } else {
        keyframeVideo.pause();
      }
    } catch (_error) {
      setStatus(status, "Video playback is temporarily unavailable.", true);
    }
    syncSourcePlaybackButton();
  });

  keyframeVideo?.addEventListener("loadedmetadata", () => {
    syncKeyframeSummary(state.workbench);
    syncSourcePlaybackButton();
  });
  keyframeVideo?.addEventListener("seeked", syncPlayheadFromVideo);
  keyframeVideo?.addEventListener("timeupdate", syncPlayheadFromVideo);
  keyframeVideo?.addEventListener("play", syncSourcePlaybackButton);
  keyframeVideo?.addEventListener("pause", syncSourcePlaybackButton);

  async function patchActiveTarget(patch, pendingMessage, successMessage) {
    const currentTarget = activeTarget();
    if (!currentTarget) {
      return;
    }
    await updateTarget(
      currentTarget.target_id,
      patch,
      pendingMessage,
      successMessage
    );
  }

  function scheduleLiveTargetPatch(patch, pendingMessage, successMessage) {
    const currentTarget = activeTarget();
    if (!currentTarget) {
      return;
    }
    if (state.livePatchTimer) {
      clearTimeout(state.livePatchTimer);
    }

    state.livePatchTimer = window.setTimeout(async () => {
      const revision = ++state.livePatchRevision;
      setStatus(status, pendingMessage, false);
      try {
        const payload = await requestTargetPatch(currentTarget.target_id, patch);
        if (revision < state.lastAppliedLivePatchRevision) {
          return;
        }
        state.lastAppliedLivePatchRevision = revision;
        renderWorkbench(payload);
        setStatus(status, successMessage(payload), false);
      } catch (error) {
        setStatus(status, error.message, true);
      }
    }, 140);
  }

  presetStrengthInput?.addEventListener("input", () => {
    updateRangeOutput(presetStrengthValue, Number(presetStrengthInput.value));
    scheduleLiveTargetPatch(
      { preset_strength: Number(presetStrengthInput.value) / 100 },
      "Refreshing live detail preview...",
      () => "Preset strength updated."
    );
  });

  motionStrengthInput?.addEventListener("input", () => {
    updateRangeOutput(motionStrengthValue, Number(motionStrengthInput.value));
    scheduleLiveTargetPatch(
      { motion_strength: Number(motionStrengthInput.value) / 100 },
      "Refreshing live detail preview...",
      () => "Motion softness updated."
    );
  });

  temporalStabilityInput?.addEventListener("input", () => {
    updateRangeOutput(temporalStabilityValue, Number(temporalStabilityInput.value));
    scheduleLiveTargetPatch(
      { temporal_stability: Number(temporalStabilityInput.value) / 100 },
      "Refreshing live detail preview...",
      () => "Temporal stability updated."
    );
  });

  edgeFeatherRadiusInput?.addEventListener("input", () => {
    updateRangeOutput(edgeFeatherRadiusValue, Number(edgeFeatherRadiusInput.value), " px");
    scheduleLiveTargetPatch(
      { edge_feather_radius: Number(edgeFeatherRadiusInput.value) },
      "Refreshing feathered edge preview...",
      () => "Edge feather updated."
    );
  });

  viewButtons.forEach((button) => {
    button.addEventListener("click", () => {
      if (button.disabled) {
        return;
      }
      setCanvasMode(button.dataset.canvasMode);
    });
  });

  async function moveWorkflowStep(nextStep) {
    if (!state.workbench || !nextStep || nextStep === state.workbench.workflow_step) {
      return;
    }
    if (nextStep === "review" && !state.workbench.latest_job_id) {
      setStatus(status, "Submit a matting job before entering review.", true);
      return;
    }
    setStatus(status, `Switching to ${nextStep}...`, false);
    try {
      const payload = await parseJson(
        await fetch(root.dataset.workflowStepEndpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ workflow_step: nextStep }),
        })
      );
      renderWorkbench(payload);
      setStatus(status, `${nextStep} step ready.`, false);
    } catch (error) {
      setStatus(status, error.message, true);
    }
  }

  function moveWorkflowBy(offset) {
    if (!state.workbench) {
      return;
    }
    const currentIndex = workflowStepIndex();
    const nextIndex = Math.min(Math.max(currentIndex + offset, 0), WORKFLOW_STEPS.length - 1);
    const nextStep = WORKFLOW_STEPS[nextIndex];
    if (nextStep === state.workbench.workflow_step) {
      return;
    }
    void moveWorkflowStep(nextStep);
  }

  workflowButtons.forEach((button) => {
    button.addEventListener("click", () => {
      if (button.disabled) {
        return;
      }
      void moveWorkflowStep(button.dataset.workflowStep);
    });
  });

  sidebarTabButtons.forEach((button) => {
    button.addEventListener("click", () => {
      if (!state.workbench) {
        return;
      }
      state.workbench.active_sidebar_tab = button.dataset.sidebarTab;
      syncSidebarPanels(state.workbench);
    });
  });

  workspaceNavBack?.addEventListener("click", () => {
    moveWorkflowBy(-1);
  });

  workspaceNavNext?.addEventListener("click", () => {
    moveWorkflowBy(1);
  });

  workspaceReturnToClip?.addEventListener("click", () => {
    void moveWorkflowStep("clip");
  });

  workspaceReturnToRefine?.addEventListener("click", () => {
    void moveWorkflowStep("refine");
  });

  presetButtons.forEach((button) => {
    button.addEventListener("click", async () => {
      const currentTarget = activeTarget();
      if (!currentTarget) {
        return;
      }
      await updateTarget(
        currentTarget.target_id,
        { refine_preset: button.dataset.preset },
        `Applying ${button.textContent} preset...`,
        () => `${button.textContent} preset is now active for ${currentTarget.name}.`
      );
    });
  });

  createTargetButton?.addEventListener("click", async () => {
    if (createTargetButton.disabled) {
      return;
    }
    setStatus(status, "Creating a new target layer...", false);
    try {
      const payload = await parseJson(
        await fetch(root.dataset.targetsEndpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({}),
        })
      );
      renderWorkbench(payload);
      setStatus(status, `Created ${payload.name}.`, false);
    } catch (error) {
      setStatus(status, error.message, true);
    }
  });

  applyTargetNameButton?.addEventListener("click", async () => {
    const currentTarget = activeTarget();
    const nextName = targetNameInput?.value?.trim();
    if (!currentTarget || !nextName || nextName === currentTarget.name) {
      return;
    }
    await updateTarget(
      currentTarget.target_id,
      { name: nextName },
      `Renaming ${currentTarget.name}...`,
      () => `Renamed target to ${nextName}.`
    );
  });

  toggleTargetLockButton?.addEventListener("click", async () => {
    const currentTarget = activeTarget();
    if (!currentTarget) {
      return;
    }
    const nextLocked = !currentTarget.locked;
    await updateTarget(
      currentTarget.target_id,
      { locked: nextLocked },
      `${nextLocked ? "Locking" : "Unlocking"} ${currentTarget.name}...`,
      () => `${currentTarget.name} is now ${nextLocked ? "locked" : "editable"}.`
    );
  });

  undoButton?.addEventListener("click", async () => {
    if (undoButton.disabled) {
      return;
    }
    setStatus(status, "Removing the last click...", false);
    try {
      const payload = await parseJson(
        await fetch(`${root.dataset.workbenchEndpoint}/undo`, {
          method: "POST",
        })
      );
      renderWorkbench(payload);
      setStatus(status, "Removed the last click from the active target.", false);
    } catch (error) {
      setStatus(status, error.message, true);
    }
  });

  resetButton?.addEventListener("click", async () => {
    if (resetButton.disabled) {
      return;
    }
    setStatus(status, "Resetting the active target...", false);
    try {
      const payload = await parseJson(
        await fetch(`${root.dataset.workbenchEndpoint}/reset-target`, {
          method: "POST",
        })
      );
      renderWorkbench(payload);
      setStatus(status, "Cleared the active target back to an empty click state.", false);
    } catch (error) {
      setStatus(status, error.message, true);
    }
  });

  image?.addEventListener("click", async (event) => {
    if (!state.workbench?.can_apply_clicks) {
      setStatus(
        status,
        hasTemplateFrame(state.workbench)
          ? "Preview mode is read-only. Switch back to coarse or refine to edit the target."
          : "Range changed. Re-apply an anchor frame before editing the target.",
        false
      );
      return;
    }

    const bounds = image.getBoundingClientRect();
    const scaleX = image.naturalWidth / bounds.width;
    const scaleY = image.naturalHeight / bounds.height;
    const x = Math.round((event.clientX - bounds.left) * scaleX);
    const y = Math.round((event.clientY - bounds.top) * scaleY);

    try {
      let payload;
      if (state.activeTool.startsWith("brush-")) {
        const brushMode = state.activeTool.replace("brush-", "");
        setStatus(status, `Applying ${brushMode} brush...`, false);
        payload = await parseJson(
          await fetch(root.dataset.brushEndpoint, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              mode: brushMode,
              radius: state.brushRadius,
              points: [[x, y]],
            }),
          })
        );
        renderWorkbench(payload);
        setStatus(status, `${brushMode} brush updated ${activeTarget(payload)?.name || "the active target"}.`, false);
        return;
      }

      setStatus(status, "Updating target preview...", false);
      payload = await parseJson(
        await fetch(root.dataset.clickEndpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ x, y, positive: state.activeTool === "point-positive" }),
        })
      );
      renderWorkbench(payload);
      setStatus(
        status,
        `${state.activeTool === "point-positive" ? "Positive" : "Negative"} point applied to ${activeTarget(payload)?.name || "target"}.`,
        false
      );
    } catch (error) {
      setStatus(status, error.message, true);
    }
  });

  saveButton?.addEventListener("click", async () => {
    if (saveButton.disabled) {
      return;
    }
    setStatus(status, "Saving current target mask...", false);
    try {
      const payload = await parseJson(
        await fetch(root.dataset.saveEndpoint, {
          method: "POST",
        })
      );
      if (payload.mask_name) {
        state.selectedMasks.add(payload.mask_name);
      }
      renderWorkbench(payload);
      setStatus(status, `Saved ${payload.mask_name}.`, false);
    } catch (error) {
      setStatus(status, error.message, true);
    }
  });

  submitButton?.addEventListener("click", async () => {
    const selectedMasks = selectedMaskNames();
    if (submitButton.disabled || selectedMasks.length === 0) {
      setStatus(status, "Select at least one saved mask before queueing the job.", true);
      return;
    }
    setStatus(status, "Submitting queued job...", false);
    try {
      const payload = await parseJson(
        await fetch(root.dataset.submitEndpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            process_start_frame_index: state.workbench?.process_start_frame_index ?? 0,
            process_end_frame_index: state.workbench?.process_end_frame_index ?? 0,
            template_frame_index: state.workbench?.template_frame_index ?? 0,
            selected_masks: selectedMasks,
          }),
        })
      );
      const workbenchPayload = await refreshWorkbench();
      renderWorkbench(workbenchPayload);
      setCanvasMode("source");
      setStatus(status, `Queued job ${payload.job_id}. Review will stay in this workspace.`, false);
    } catch (error) {
      setStatus(status, error.message, true);
    }
  });

  refreshWorkbench().catch((error) => {
    setStatus(status, error.message, true);
  });

  document.addEventListener("keydown", (event) => {
    if (event.defaultPrevented) {
      return;
    }

    const key = event.key;
    const lowerKey = key.toLowerCase();
    const hasPrimaryModifier = event.ctrlKey || event.metaKey;
    const typingContext = isTypingContext(event.target);

    if (hasPrimaryModifier && lowerKey === "s") {
      event.preventDefault();
      saveButton?.click();
      return;
    }

    if (hasPrimaryModifier && key === "Enter") {
      event.preventDefault();
      submitButton?.click();
      return;
    }

    if (event.altKey || hasPrimaryModifier || typingContext) {
      return;
    }

    switch (key) {
      case "1":
      case "2":
      case "3":
      case "4": {
        event.preventDefault();
        const nextStep = {
          "1": "clip",
          "2": "mask",
          "3": "refine",
          "4": "review",
        }[key];
        void moveWorkflowStep(nextStep);
        return;
      }
      case "Backspace":
        event.preventDefault();
        resetButton?.click();
        return;
      case "ArrowLeft":
        if (!typingContext) {
          event.preventDefault();
          moveWorkflowBy(-1);
          return;
        }
        break;
      case "ArrowRight":
        if (!typingContext) {
          event.preventDefault();
          moveWorkflowBy(1);
          return;
        }
        break;
      default:
        break;
    }

    switch (lowerKey) {
      case "i":
        event.preventDefault();
        markRangeInButton?.click();
        return;
      case "o":
        event.preventDefault();
        markRangeOutButton?.click();
        return;
      case "p":
        event.preventDefault();
        setActiveTool("point-positive");
        setStatus(status, "Shortcut: Positive point tool.", false);
        return;
      case "n":
        event.preventDefault();
        setActiveTool("point-negative");
        setStatus(status, "Shortcut: Negative point tool.", false);
        return;
      case "b":
        event.preventDefault();
        setActiveTool("brush-add");
        setStatus(status, "Shortcut: Add brush tool.", false);
        return;
      case "e":
        event.preventDefault();
        setActiveTool("brush-remove");
        setStatus(status, "Shortcut: Remove brush tool.", false);
        return;
      case "g":
        event.preventDefault();
        setActiveTool("brush-feather");
        setStatus(status, "Shortcut: Feather brush tool.", false);
        return;
      case "t":
        event.preventDefault();
        createTargetButton?.click();
        return;
      case "u":
        event.preventDefault();
        undoButton?.click();
        return;
      case "r":
        event.preventDefault();
        resetButton?.click();
        return;
      case "f":
        event.preventDefault();
        setCanvasMode("source");
        setStatus(status, "Shortcut: Source view.", false);
        return;
      case "v":
        event.preventDefault();
        setCanvasMode("overlay");
        setStatus(status, "Shortcut: Overlay view.", false);
        return;
      case "m":
        if (viewButtons.find((button) => button.dataset.canvasMode === "mask")?.disabled) {
          return;
        }
        event.preventDefault();
        setCanvasMode("mask");
        setStatus(status, "Shortcut: Mask view.", false);
        return;
      default:
        break;
    }
  });
}

document.addEventListener("DOMContentLoaded", bindWorkbench);
