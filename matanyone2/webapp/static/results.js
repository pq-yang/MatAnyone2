import {
  parseJson,
  setStatus,
  withCacheBust,
} from "/static/shared.js";

const TERMINAL_STATES = new Set([
  "completed",
  "completed_with_warning",
  "failed",
  "interrupted",
]);

function bindResultsPage() {
  const root = document.getElementById("job-app");
  if (!root) {
    return;
  }

  const statusNode = document.getElementById("job-status");
  const queueNode = document.getElementById("job-queue-position");
  const messageNode = document.getElementById("job-message");
  const artifactList = document.getElementById("artifact-list");
  const previewVideo = document.getElementById("preview-video");
  const previewPlaceholder = document.getElementById("preview-placeholder");
  const previewCaption = document.getElementById("preview-caption");
  const tabs = Array.from(root.querySelectorAll(".preview-tab"));

  const state = {
    mode: "source",
    payload: null,
  };

  function previewUrlFor(payload) {
    switch (state.mode) {
      case "foreground":
        return payload.artifacts?.["foreground.mp4"] || null;
      case "alpha":
        return payload.artifacts?.["alpha.mp4"] || null;
      case "overlay":
        return payload.artifacts?.["foreground.mp4"] || payload.source_video_url || null;
      case "source":
      default:
        return payload.source_video_url || root.dataset.sourceVideoEndpoint || null;
    }
  }

  function previewCaptionFor(payload) {
    if (state.mode === "overlay") {
      return payload.artifacts?.["foreground.mp4"]
        ? "Overlay preview currently mirrors the foreground render while the dedicated browser compositor is still pending."
        : "Overlay preview will unlock once foreground output is available.";
    }
    if (state.mode === "alpha") {
      return payload.artifacts?.["alpha.mp4"]
        ? "Alpha preview is showing the grayscale matte stream."
        : "Alpha preview becomes available after export starts.";
    }
    if (state.mode === "foreground") {
      return payload.artifacts?.["foreground.mp4"]
        ? "Foreground preview is showing the current rendered foreground pass."
        : "Foreground preview becomes available after inference output is written.";
    }
    return "Source preview is always available for quick comparison against the matte outputs.";
  }

  function renderArtifacts(artifacts) {
    if (!artifactList) {
      return;
    }
    artifactList.innerHTML = "";
    Object.entries(artifacts || {}).forEach(([name, url]) => {
      const item = document.createElement("li");
      item.className = "artifact-item";
      const link = document.createElement("a");
      link.href = url;
      link.textContent = name;
      item.appendChild(link);
      artifactList.appendChild(item);
    });
  }

  function renderPreview(payload) {
    if (!previewCaption || !previewVideo || !previewPlaceholder) {
      return;
    }
    previewCaption.textContent = previewCaptionFor(payload);
    const url = previewUrlFor(payload);
    if (!url) {
      previewVideo.removeAttribute("src");
      previewVideo.load();
      previewVideo.hidden = true;
      previewPlaceholder.hidden = false;
      previewPlaceholder.textContent = "Waiting for the selected preview stream.";
      return;
    }
    previewPlaceholder.hidden = true;
    previewVideo.hidden = false;
    previewVideo.src = withCacheBust(url);
  }

  function renderPayload(payload) {
    state.payload = payload;
    if (statusNode) {
      statusNode.textContent = payload.status;
    }
    if (queueNode) {
      queueNode.textContent = payload.queue_position
        ? `Queue position: ${payload.queue_position}`
        : "";
    }
    if (messageNode) {
      messageNode.textContent = payload.warning_text || payload.error_text || "";
      messageNode.dataset.state = payload.error_text ? "error" : "info";
    }
    tabs.forEach((tab) => {
      tab.toggleAttribute("data-active", tab.dataset.mode === state.mode);
    });
    renderArtifacts(payload.artifacts);
    renderPreview(payload);
  }

  async function refreshStatus() {
    const payload = await parseJson(await fetch(root.dataset.statusEndpoint));
    renderPayload(payload);
    return TERMINAL_STATES.has(payload.status);
  }

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      state.mode = tab.dataset.mode;
      if (state.payload) {
        renderPayload(state.payload);
      }
    });
  });

  refreshStatus()
    .then((isTerminal) => {
      if (isTerminal) {
        return;
      }
      const intervalMs = Number(root.dataset.pollIntervalMs || "2000");
      const timer = window.setInterval(async () => {
        try {
          const shouldStop = await refreshStatus();
          if (shouldStop) {
            window.clearInterval(timer);
          }
        } catch (error) {
          window.clearInterval(timer);
          setStatus(messageNode, error.message, true);
        }
      }, intervalMs);
    })
    .catch((error) => {
      setStatus(messageNode, error.message, true);
    });
}

document.addEventListener("DOMContentLoaded", bindResultsPage);
