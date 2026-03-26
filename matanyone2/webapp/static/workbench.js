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
  const inspectorStage = document.getElementById("inspector-stage");
  const inspectorTarget = document.getElementById("inspector-target");
  const inspectorPoints = document.getElementById("inspector-points");
  const inspectorMask = document.getElementById("inspector-mask");

  const state = {
    positiveMode: true,
    workbench: null,
  };

  function setMode(nextPositiveMode) {
    state.positiveMode = nextPositiveMode;
    positiveButton?.toggleAttribute("data-active", nextPositiveMode);
    negativeButton?.toggleAttribute("data-active", !nextPositiveMode);
  }

  function selectedMaskNames() {
    return Array.from(root.querySelectorAll('input[name="mask_name"]:checked'))
      .map((input) => input.value);
  }

  function renderSavedMasks(maskNames) {
    if (!savedMaskList) {
      return;
    }
    const selected = new Set(selectedMaskNames());
    savedMaskList.innerHTML = "";
    maskNames.forEach((maskName) => {
      const label = document.createElement("label");
      const input = document.createElement("input");
      input.type = "checkbox";
      input.name = "mask_name";
      input.value = maskName;
      input.checked = selected.size === 0 || selected.has(maskName);
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
        <span class="target-card__meta">${target.point_count} point${target.point_count === 1 ? "" : "s"} · ${target.saved_mask_name || "unsaved"}</span>
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

  function renderWorkbench(payload) {
    state.workbench = payload;
    root.dataset.stage = payload.stage;

    const currentTarget = payload.targets.find(
      (target) => target.target_id === payload.active_target_id
    );

    if (image) {
      image.src = withCacheBust(
        payload.current_preview_url || payload.template_frame_url || root.dataset.templateFrameUrl
      );
    }
    if (inspectorStage) {
      inspectorStage.textContent = payload.stage;
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
  }

  async function refreshWorkbench() {
    const payload = await parseJson(await fetch(root.dataset.workbenchEndpoint));
    renderWorkbench(payload);
    return payload;
  }

  setMode(true);

  positiveButton?.addEventListener("click", () => setMode(true));
  negativeButton?.addEventListener("click", () => setMode(false));

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
        setStatus(status, `Stage: ${payload.stage}.`, false);
      } catch (error) {
        setStatus(status, error.message, true);
      }
    });
  });

  createTargetButton?.addEventListener("click", async () => {
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
    setStatus(status, "Saving current target mask...", false);
    try {
      const payload = await parseJson(
        await fetch(root.dataset.saveEndpoint, {
          method: "POST",
        })
      );
      renderWorkbench(payload);
      setStatus(status, `Saved ${payload.mask_name}.`, false);
    } catch (error) {
      setStatus(status, error.message, true);
    }
  });

  submitButton?.addEventListener("click", async () => {
    const selectedMasks = selectedMaskNames();
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
