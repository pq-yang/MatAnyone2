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

function bindWorkbench() {
  const root = document.getElementById("annotator-app");
  if (!root) {
    return;
  }

  const status = document.getElementById("annotator-status");
  const image = document.getElementById("annotation-image");
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
  const stageButtons = Array.from(root.querySelectorAll(".stage-button"));
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
  const stageBackButton = document.getElementById("stage-back");
  const stageForwardButton = document.getElementById("stage-forward");
  const templateFrameSlider = document.getElementById("template-frame-slider");
  const templateFrameValue = document.getElementById("template-frame-value");
  const applyTemplateFrameButton = document.getElementById("apply-template-frame");
  const keyframeVideo = document.getElementById("keyframe-video");
  const keyframeSelectedLabel = document.getElementById("keyframe-selected-label");
  const keyframeAppliedLabel = document.getElementById("keyframe-applied-label");
  const keyframeTimeLabel = document.getElementById("keyframe-time-label");
  const presetStrengthInput = document.getElementById("preset-strength");
  const presetStrengthValue = document.getElementById("preset-strength-value");
  const motionStrengthInput = document.getElementById("motion-strength");
  const motionStrengthValue = document.getElementById("motion-strength-value");
  const temporalStabilityInput = document.getElementById("temporal-stability");
  const temporalStabilityValue = document.getElementById("temporal-stability-value");
  const previewBeforeImage = document.getElementById("preview-before-image");
  const previewLiveImage = document.getElementById("preview-live-image");

  const state = {
    activeTool: "point-positive",
    canvasMode: "overlay",
    workbench: null,
    selectedMasks: new Set(),
    brushRadius: Number(brushRadiusInput?.value || 28),
    overlayOpacity: Number(overlayOpacityInput?.value || 72),
    templateFrameSelection: Number(templateFrameSlider?.value || 0),
    templateFrameApplied: Number(templateFrameSlider?.value || 0),
    fps: Number(root.dataset.fps || 0),
    durationSeconds: Number(root.dataset.durationSeconds || 0),
    livePatchTimer: null,
    livePatchRevision: 0,
    lastAppliedLivePatchRevision: 0,
    compareBeforeSrc: root.dataset.templateFrameUrl || "",
    compareLiveSrc: root.dataset.templateFrameUrl || "",
  };

  const STAGE_ORDER = ["coarse", "refine", "preview"];

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

  function updateRangeOutput(outputElement, value, suffix = "%") {
    if (!outputElement) {
      return;
    }
    outputElement.value = `${value}${suffix}`;
    outputElement.textContent = `${value}${suffix}`;
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

  function syncCompareStrip(payload = state.workbench) {
    if (!previewBeforeImage || !previewLiveImage || !payload) {
      return;
    }
    const liveSrc = image?.src || withCacheBust(resolveCanvasUrl(payload));
    if (!state.compareBeforeSrc) {
      state.compareBeforeSrc = liveSrc;
    }
    state.compareLiveSrc = liveSrc;
    previewBeforeImage.src = state.compareBeforeSrc;
    previewLiveImage.src = state.compareLiveSrc;
  }

  function syncKeyframeSummary(payload) {
    if (!payload) {
      return;
    }
    state.fps = Number(payload.fps || state.fps || 0);
    state.durationSeconds = Number(payload.duration_seconds || state.durationSeconds || 0);
    state.templateFrameApplied = Number(payload.template_frame_index || 0);
    if (state.templateFrameSelection === undefined || Number.isNaN(state.templateFrameSelection)) {
      state.templateFrameSelection = state.templateFrameApplied;
    }

    if (templateFrameSlider) {
      templateFrameSlider.max = String(Math.max(0, (payload.frame_count || 1) - 1));
      templateFrameSlider.value = String(state.templateFrameSelection);
    }
    updateRangeOutput(templateFrameValue, Number(state.templateFrameSelection || 0), "");

    if (keyframeSelectedLabel) {
      keyframeSelectedLabel.textContent = `Selected frame ${state.templateFrameSelection}`;
    }
    if (keyframeAppliedLabel) {
      keyframeAppliedLabel.textContent = `Applied frame ${state.templateFrameApplied}`;
    }
    if (keyframeTimeLabel) {
      keyframeTimeLabel.textContent = `${formatFrameTimestamp(state.templateFrameSelection, payload)} / ${formatDuration(payload.duration_seconds || 0)}`;
    }

    if (keyframeVideo) {
      if (!keyframeVideo.src) {
        keyframeVideo.src = root.dataset.sourceVideoUrl;
      }
      const desiredTime = frameToSeconds(state.templateFrameSelection, payload);
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
  }

  function applyImagePresentation() {
    if (!image) {
      return;
    }
    if (state.canvasMode === "source") {
      image.style.opacity = "1";
    } else {
      image.style.opacity = String(state.overlayOpacity / 100);
    }
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
    const canSubmit = payload.can_submit && state.selectedMasks.size > 0;
    root.dataset.stage = payload.stage;
    root.dataset.editable = payload.can_apply_clicks ? "true" : "false";

    createTargetButton?.toggleAttribute("disabled", !payload.can_create_target);
    undoButton?.toggleAttribute("disabled", !payload.can_undo_clicks);
    resetButton?.toggleAttribute("disabled", !payload.can_reset_target);
    saveButton?.toggleAttribute("disabled", !payload.can_save_current_target);
    submitButton?.toggleAttribute("disabled", !canSubmit);
    applyTargetNameButton?.toggleAttribute("disabled", !payload.active_target_id);
    stageBackButton?.toggleAttribute("disabled", payload.stage === "coarse");
    stageForwardButton?.toggleAttribute("disabled", payload.stage === "preview");
    if (applyTemplateFrameButton) {
      const sameFrame = Number(templateFrameSlider?.value || 0) === Number(payload.template_frame_index || 0);
      applyTemplateFrameButton.toggleAttribute(
        "disabled",
        !payload.can_change_template_frame || sameFrame
      );
    }
    templateFrameSlider?.toggleAttribute("disabled", !payload.can_change_template_frame);

    const currentTarget = activeTarget(payload);
    toggleTargetLockButton?.toggleAttribute("disabled", !currentTarget);
    if (toggleTargetLockButton && currentTarget) {
      toggleTargetLockButton.textContent = currentTarget.locked ? "Unlock Target" : "Lock Target";
    }

    if (submitButton) {
      submitButton.textContent = payload.stage === "preview"
        ? "Queue Matting Job"
        : "Submit Matting Job";
    }

    syncToolButtons(payload);
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
    if (state.canvasMode === "mask" && !payload.active_mask_url && !payload.current_mask_url) {
      state.canvasMode = payload.current_preview_url ? "overlay" : "source";
    }

    const modeLabel = {
      source: "Source plate",
      overlay: "Overlay preview",
      mask: "Mask inspection",
    }[state.canvasMode];

    if (canvasModeLabel) {
      canvasModeLabel.textContent = `${payload.canvas_mode_label || "Guided silhouette pass"} | ${modeLabel}`;
    }

    if (image) {
      image.src = withCacheBust(resolveCanvasUrl(payload));
      image.alt = {
        source: `Template frame for ${payload.draft_id}`,
        overlay: `Overlay preview for ${payload.draft_id}`,
        mask: `Mask preview for ${payload.draft_id}`,
      }[state.canvasMode];
    }

    viewButtons.forEach((button) => {
      const isMask = button.dataset.canvasMode === "mask";
      button.toggleAttribute(
        "disabled",
        isMask && !payload.active_mask_url && !payload.current_mask_url
      );
      button.toggleAttribute("data-active", button.dataset.canvasMode === state.canvasMode);
    });

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
    state.workbench = payload;
    syncSelectedMasks(payload);
    if (state.templateFrameSelection === state.templateFrameApplied) {
      state.templateFrameSelection = Number(payload.template_frame_index || 0);
    }

    const currentTarget = activeTarget(payload);
    syncTargetControls(payload);

    syncCanvasMode(payload);
    syncCompareStrip(payload);
    syncPresetButtons(payload);

    if (canvasStageNote) {
      canvasStageNote.textContent = payload.stage_note || "";
    }
    if (guidanceTitle) {
      guidanceTitle.textContent = payload.stage_label || "Coarse Selection";
    }
    if (guidanceCopy) {
      guidanceCopy.textContent = payload.stage_note || "";
    }
    if (workflowStageChip) {
      workflowStageChip.textContent = payload.stage_label || payload.stage;
    }
    if (selectionNote) {
      selectionNote.textContent = payload.stage === "preview"
        ? "Preview is locked. Return to coarse or refine before placing more points."
        : "Use points to establish the person first, then switch into presets or brush cleanup.";
    }
    if (brushNote) {
      brushNote.textContent = payload.stage === "preview"
        ? "Brush refinement is disabled in preview mode."
        : "Brush actions edit the active mask directly, which is useful when SAM2 gets the rough silhouette but misses small edge corrections.";
    }

    if (inspectorStage) {
      inspectorStage.textContent = payload.stage_label || payload.stage;
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

    stageButtons.forEach((button) => {
      button.toggleAttribute("data-active", button.dataset.stage === payload.stage);
    });

    renderTargets(payload.targets || [], payload.active_target_id);
    renderSavedMasks(payload.mask_names || []);
    syncActionState(payload);
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

  templateFrameSlider?.addEventListener("input", () => {
    state.templateFrameSelection = Number(templateFrameSlider.value);
    syncKeyframeSummary(state.workbench);
    syncActionState(state.workbench);
  });

  function syncSelectionFromVideo() {
    const payload = state.workbench;
    if (!payload) {
      return;
    }
    const fps = Number(payload.fps || state.fps || 0);
    if (!Number.isFinite(fps) || fps <= 0) {
      return;
    }
    const nextFrame = Math.max(
      0,
      Math.min(
        Number(payload.frame_count || 1) - 1,
        Math.round((keyframeVideo.currentTime || 0) * fps)
      )
    );
    state.templateFrameSelection = nextFrame;
    syncKeyframeSummary(payload);
    syncActionState(payload);
  }

  keyframeVideo?.addEventListener("loadedmetadata", () => {
    syncKeyframeSummary(state.workbench);
  });
  keyframeVideo?.addEventListener("seeked", syncSelectionFromVideo);
  keyframeVideo?.addEventListener("timeupdate", syncSelectionFromVideo);

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

    const baselineSrc = image?.src || state.compareLiveSrc || withCacheBust(resolveCanvasUrl(state.workbench));
    state.livePatchTimer = window.setTimeout(async () => {
      const revision = ++state.livePatchRevision;
      setStatus(status, pendingMessage, false);
      try {
        const payload = await requestTargetPatch(currentTarget.target_id, patch);
        if (revision < state.lastAppliedLivePatchRevision) {
          return;
        }
        state.lastAppliedLivePatchRevision = revision;
        state.compareBeforeSrc = baselineSrc;
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

  applyTemplateFrameButton?.addEventListener("click", async () => {
    if (applyTemplateFrameButton.disabled) {
      return;
    }
    setStatus(status, `Switching template frame to ${state.templateFrameSelection}...`, false);
    try {
      const payload = await parseJson(
        await fetch(root.dataset.templateFrameEndpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ frame_index: state.templateFrameSelection }),
        })
      );
      renderWorkbench(payload);
      setStatus(
        status,
        `Template frame ${payload.template_frame_index} is now active. Existing unsaved annotations were reset.`,
        false
      );
    } catch (error) {
      setStatus(status, error.message, true);
    }
  });

  viewButtons.forEach((button) => {
    button.addEventListener("click", () => {
      if (button.disabled) {
        return;
      }
      setCanvasMode(button.dataset.canvasMode);
    });
  });

  stageButtons.forEach((button) => {
    button.addEventListener("click", async () => {
      setStatus(status, `Switching to ${button.dataset.stage} stage...`, false);
      try {
        const payload = await parseJson(
          await fetch(root.dataset.stageEndpoint, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ stage: button.dataset.stage }),
          })
        );
        renderWorkbench(payload);
        setStatus(status, `${payload.stage_label} ready.`, false);
      } catch (error) {
        setStatus(status, error.message, true);
      }
    });
  });

  function moveStage(offset) {
    if (!state.workbench) {
      return;
    }
    const currentIndex = STAGE_ORDER.indexOf(state.workbench.stage);
    const nextIndex = Math.min(Math.max(currentIndex + offset, 0), STAGE_ORDER.length - 1);
    const nextStage = STAGE_ORDER[nextIndex];
    if (nextStage === state.workbench.stage) {
      return;
    }
    stageButtons.find((button) => button.dataset.stage === nextStage)?.click();
  }

  stageBackButton?.addEventListener("click", () => moveStage(-1));
  stageForwardButton?.addEventListener("click", () => moveStage(1));

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
      setStatus(status, "Preview mode is read-only. Switch back to coarse or refine to edit the target.", false);
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
            template_frame_index: state.workbench?.template_frame_index ?? 0,
            selected_masks: selectedMasks,
          }),
        })
      );
      window.location.assign(`${root.dataset.jobPagePrefix}${payload.job_id}`);
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
      case "3": {
        event.preventDefault();
        const stageButton = stageButtons.find((button) => button.dataset.stage === {
          "1": "coarse",
          "2": "refine",
          "3": "preview",
        }[key]);
        stageButton?.click();
        return;
      }
      case "Backspace":
        event.preventDefault();
        resetButton?.click();
        return;
      case "ArrowLeft":
        if (!typingContext) {
          event.preventDefault();
          moveStage(-1);
          return;
        }
        break;
      case "ArrowRight":
        if (!typingContext) {
          event.preventDefault();
          moveStage(1);
          return;
        }
        break;
      default:
        break;
    }

    switch (lowerKey) {
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
      case "o":
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
