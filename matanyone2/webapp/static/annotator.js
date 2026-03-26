(function () {
  function setStatus(target, message, isError) {
    if (!target) {
      return;
    }
    target.textContent = message;
    target.dataset.state = isError ? "error" : "info";
  }

  async function parseJson(response) {
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.detail || "Request failed");
    }
    return payload;
  }

  function withCacheBust(url) {
    const separator = url.includes("?") ? "&" : "?";
    return `${url}${separator}t=${Date.now()}`;
  }

  function renderSavedMasks(container, maskNames) {
    if (!container) {
      return;
    }
    container.innerHTML = "";
    maskNames.forEach((maskName) => {
      const label = document.createElement("label");
      const input = document.createElement("input");
      input.type = "checkbox";
      input.name = "mask_name";
      input.value = maskName;
      input.checked = true;
      label.appendChild(input);
      label.append(` ${maskName}`);
      container.appendChild(label);
    });
  }

  function bindUploadForm() {
    const form = document.getElementById("upload-form");
    if (!form) {
      return;
    }

    const status = document.getElementById("upload-status");
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const fileInput = form.querySelector('input[type="file"]');
      const file = fileInput?.files?.[0];
      if (!file) {
        setStatus(status, "Select a video before submitting.", true);
        return;
      }

      const body = new FormData();
      body.append("video", file);
      setStatus(status, "Uploading video and preparing draft...", false);

      try {
        const payload = await parseJson(
          await fetch(form.dataset.uploadEndpoint, {
            method: "POST",
            body,
          })
        );
        window.location.assign(`/drafts/${payload.draft_id}/annotate`);
      } catch (error) {
        setStatus(status, error.message, true);
      }
    });
  }

  function bindAnnotator() {
    const root = document.getElementById("annotator-app");
    if (!root) {
      return;
    }

    const status = document.getElementById("annotator-status");
    const image = document.getElementById("annotation-image");
    const saveButton = document.getElementById("save-mask");
    const submitButton = document.getElementById("submit-job");
    const savedMaskList = document.getElementById("saved-mask-list");
    const positiveButton = document.getElementById("positive-mode");
    const negativeButton = document.getElementById("negative-mode");
    let positiveMode = true;

    function setMode(nextPositiveMode) {
      positiveMode = nextPositiveMode;
      positiveButton?.toggleAttribute("data-active", positiveMode);
      negativeButton?.toggleAttribute("data-active", !positiveMode);
    }

    setMode(true);

    positiveButton?.addEventListener("click", () => setMode(true));
    negativeButton?.addEventListener("click", () => setMode(false));

    image?.addEventListener("click", async (event) => {
      const bounds = image.getBoundingClientRect();
      const scaleX = image.naturalWidth / bounds.width;
      const scaleY = image.naturalHeight / bounds.height;
      const x = Math.round((event.clientX - bounds.left) * scaleX);
      const y = Math.round((event.clientY - bounds.top) * scaleY);

      setStatus(status, "Updating mask preview...", false);
      try {
        const payload = await parseJson(
          await fetch(root.dataset.clickEndpoint, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ x, y, positive: positiveMode }),
          })
        );
        image.src = withCacheBust(payload.current_preview_url);
        setStatus(status, `Added ${positiveMode ? "positive" : "negative"} click at ${x}, ${y}.`, false);
      } catch (error) {
        setStatus(status, error.message, true);
      }
    });

    saveButton?.addEventListener("click", async () => {
      setStatus(status, "Saving current mask...", false);
      try {
        const payload = await parseJson(
          await fetch(root.dataset.saveEndpoint, {
            method: "POST",
          })
        );
        renderSavedMasks(savedMaskList, payload.mask_names || []);
        setStatus(status, `Saved ${payload.mask_name}.`, false);
      } catch (error) {
        setStatus(status, error.message, true);
      }
    });

    submitButton?.addEventListener("click", async () => {
      const selectedMasks = Array.from(
        root.querySelectorAll('input[name="mask_name"]:checked')
      ).map((input) => input.value);
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
  }

  function renderArtifacts(container, artifacts) {
    if (!container) {
      return;
    }
    container.innerHTML = "";
    Object.entries(artifacts || {}).forEach(([name, url]) => {
      const item = document.createElement("li");
      const link = document.createElement("a");
      link.href = url;
      link.textContent = name;
      item.appendChild(link);
      container.appendChild(item);
    });
  }

  function bindJobPage() {
    const root = document.getElementById("job-app");
    if (!root) {
      return;
    }

    const status = document.getElementById("job-status");
    const queuePosition = document.getElementById("job-queue-position");
    const message = document.getElementById("job-message");
    const artifactList = document.getElementById("artifact-list");
    const terminalStates = new Set([
      "completed",
      "completed_with_warning",
      "failed",
      "interrupted",
    ]);

    async function refreshStatus() {
      try {
        const payload = await parseJson(await fetch(root.dataset.statusEndpoint));
        if (status) {
          status.textContent = payload.status;
        }
        if (queuePosition) {
          queuePosition.textContent = payload.queue_position
            ? `Queue position: ${payload.queue_position}`
            : "";
        }
        if (message) {
          message.textContent = payload.warning_text || payload.error_text || "";
        }
        renderArtifacts(artifactList, payload.artifacts);
        return terminalStates.has(payload.status);
      } catch (error) {
        setStatus(message, error.message, true);
        return false;
      }
    }

    refreshStatus().then((isTerminal) => {
      if (isTerminal) {
        return;
      }
      const intervalMs = Number(root.dataset.pollIntervalMs || "2000");
      const timer = window.setInterval(async () => {
        const shouldStop = await refreshStatus();
        if (shouldStop) {
          window.clearInterval(timer);
        }
      }, intervalMs);
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    bindUploadForm();
    bindAnnotator();
    bindJobPage();
  });

  window.MatAnyone2Annotator = {
    version: "0.2.0",
  };
})();
