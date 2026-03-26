import {
  parseJson,
  setStatus,
  withCacheBust,
} from "/static/shared.js";

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
  const savedMaskList = document.getElementById("saved-mask-list");
  const targetList = document.getElementById("target-list");
  const positiveButton = document.getElementById("positive-mode");
  const negativeButton = document.getElementById("negative-mode");
  const stageButtons = Array.from(root.querySelectorAll(".stage-button"));
  const viewButtons = Array.from(root.querySelectorAll(".canvas-view-tab"));
  const inspectorStage = document.getElementById("inspector-stage");
  const inspectorTarget = document.getElementById("inspector-target");
  const inspectorPoints = document.getElementById("inspector-points");
  const inspectorMask = document.getElementById("inspector-mask");
  const canvasModeLabel = document.getElementById("canvas-mode-label");
  const canvasStageNote = document.getElementById("canvas-stage-note");
  const railNote = document.getElementById("rail-note");
  const guidanceTitle = document.getElementById("stage-guidance-title");
  const guidanceCopy = document.getElementById("stage-guidance-copy");

  const state = {
    positiveMode: true,
    canvasMode: "overlay",
    workbench: null,
    selectedMasks: new Set(),
  };

  function setMode(nextPositiveMode) {
    state.positiveMode = nextPositiveMode;
    positiveButton?.toggleAttribute("data-active", nextPositiveMode);
    negativeButton?.toggleAttribute("data-active", !nextPositiveMode);
  }

  function selectedMaskNames() {
    return Array.from(state.selectedMasks).sort();
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

  function renderTargets(targets, activeTargetId) {
    if (!targetList) {
      return;
    }
    targetList.innerHTML = "";
    targets.forEach((target) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "target-card";
      button.dataset.selected = target.target_id === activeTargetId ? "true" : "false";
      button.innerHTML = `
        <span class="target-card__name">${target.name}</span>
        <span class="target-card__meta">${target.point_count} point${target.point_count === 1 ? "" : "s"} - ${target.saved_mask_name || "unsaved"}</span>
      `;
      button.addEventListener("click", async () => {
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
      targetList.appendChild(button);
    });
  }

  function syncActionState(payload) {
    if (!payload) {
      return;
    }
    const canSubmit = payload.can_submit && state.selectedMasks.size > 0;
    root.dataset.stage = payload.stage;
    root.dataset.editable = payload.can_apply_clicks ? "true" : "false";

    if (image) {
      image.dataset.editable = payload.can_apply_clicks ? "true" : "false";
      image.style.cursor = payload.can_apply_clicks
        ? state.positiveMode ? "crosshair" : "cell"
        : "default";
    }

    positiveButton?.toggleAttribute("disabled", !payload.can_apply_clicks);
    negativeButton?.toggleAttribute("disabled", !payload.can_apply_clicks);
    createTargetButton?.toggleAttribute("disabled", !payload.can_create_target);
    saveButton?.toggleAttribute("disabled", !payload.can_save_current_target);
    submitButton?.toggleAttribute("disabled", !canSubmit);

    if (submitButton) {
      submitButton.textContent = payload.stage === "preview"
        ? "Queue Matting Job"
        : "Submit Matting Job";
    }
  }

  function resolveCanvasUrl(payload) {
    if (state.canvasMode === "mask") {
      return payload.active_mask_url || payload.template_frame_url || root.dataset.templateFrameUrl;
    }
    if (state.canvasMode === "source") {
      return payload.template_frame_url || root.dataset.templateFrameUrl;
    }
    return payload.current_preview_url || payload.template_frame_url || root.dataset.templateFrameUrl;
  }

  function syncCanvasMode(payload) {
    if (state.canvasMode === "mask" && !payload.active_mask_url) {
      state.canvasMode = payload.current_preview_url ? "overlay" : "source";
    }

    const modeLabel = {
      source: "Source plate",
      overlay: "Overlay preview",
      mask: "Mask inspection",
    }[state.canvasMode];

    if (canvasModeLabel) {
      canvasModeLabel.textContent = `${payload.canvas_mode_label || "Guided silhouette pass"} - ${modeLabel}`;
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
      button.toggleAttribute("disabled", isMask && !payload.active_mask_url);
      button.toggleAttribute("data-active", button.dataset.canvasMode === state.canvasMode);
    });
  }

  function renderWorkbench(payload) {
    state.workbench = payload;
    syncSelectedMasks(payload);

    const currentTarget = payload.targets.find(
      (target) => target.target_id === payload.active_target_id
    );

    syncCanvasMode(payload);
    if (canvasStageNote) {
      canvasStageNote.textContent = payload.stage_note || "";
    }
    if (railNote) {
      railNote.textContent = payload.stage === "preview"
        ? "Preview locks point editing so you can review saved masks and export selection without accidental clicks."
        : "Coarse clicks stay isolated per target layer. Save each layer before moving to the next person.";
    }
    if (guidanceTitle) {
      guidanceTitle.textContent = payload.stage_label || "Coarse Selection";
    }
    if (guidanceCopy) {
      guidanceCopy.textContent = payload.stage_note || "";
    }
    if (inspectorStage) {
      inspectorStage.textContent = payload.stage_label || payload.stage;
    }
    if (inspectorTarget) {
      inspectorTarget.textContent = currentTarget?.name || "-";
    }
    if (inspectorPoints) {
      inspectorPoints.textContent = String(currentTarget?.point_count || 0);
    }
    if (inspectorMask) {
      inspectorMask.textContent = currentTarget?.saved_mask_name || "Not saved yet";
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

  setMode(true);

  positiveButton?.addEventListener("click", () => setMode(true));
  negativeButton?.addEventListener("click", () => setMode(false));

  viewButtons.forEach((button) => {
    button.addEventListener("click", () => {
      if (button.disabled) {
        return;
      }
      state.canvasMode = button.dataset.canvasMode;
      if (state.workbench) {
        syncCanvasMode(state.workbench);
      }
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

  image?.addEventListener("click", async (event) => {
    if (!state.workbench?.can_apply_clicks) {
      setStatus(status, "Preview mode is read-only. Switch back to coarse or refine to place more points.", false);
      return;
    }

    const bounds = image.getBoundingClientRect();
    const scaleX = image.naturalWidth / bounds.width;
    const scaleY = image.naturalHeight / bounds.height;
    const x = Math.round((event.clientX - bounds.left) * scaleX);
    const y = Math.round((event.clientY - bounds.top) * scaleY);

    setStatus(status, "Updating target preview...", false);
    try {
      const payload = await parseJson(
        await fetch(root.dataset.clickEndpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ x, y, positive: state.positiveMode }),
        })
      );
      renderWorkbench(payload);
      setStatus(
        status,
        `${state.positiveMode ? "Positive" : "Negative"} point applied to ${payload.targets.find((target) => target.target_id === payload.active_target_id)?.name || "target"}.`,
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
            template_frame_index: 0,
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
}

document.addEventListener("DOMContentLoaded", bindWorkbench);
