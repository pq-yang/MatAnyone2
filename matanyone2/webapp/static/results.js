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
  const overlayCanvas = document.getElementById("preview-overlay-canvas");
  const overlayForegroundVideo = document.getElementById("overlay-foreground-video");
  const overlayAlphaVideo = document.getElementById("overlay-alpha-video");
  const tabs = Array.from(root.querySelectorAll(".preview-tab"));

  const state = {
    mode: "source",
    payload: null,
    overlayFrameHandle: null,
    overlayForegroundUrl: null,
    overlayAlphaUrl: null,
    currentVideoUrl: null,
    overlayVideosBound: false,
    foregroundCanvas: document.createElement("canvas"),
    alphaCanvas: document.createElement("canvas"),
  };

  const foregroundContext = state.foregroundCanvas.getContext("2d", { willReadFrequently: true });
  const alphaContext = state.alphaCanvas.getContext("2d", { willReadFrequently: true });
  const overlayContext = overlayCanvas?.getContext("2d", { willReadFrequently: true }) || null;

  function previewUrlFor(payload) {
    switch (state.mode) {
      case "foreground":
        return payload.artifacts?.["foreground.mp4"] || null;
      case "alpha":
        return payload.artifacts?.["alpha.mp4"] || null;
      case "source":
      default:
        return payload.source_video_url || root.dataset.sourceVideoEndpoint || null;
    }
  }

  function previewCaptionFor(payload) {
    if (state.mode === "overlay") {
      return payload.artifacts?.["foreground.mp4"] && payload.artifacts?.["alpha.mp4"]
        ? "Overlay preview is compositing foreground and alpha over the source plate in the browser."
        : "Overlay preview becomes available after both foreground and alpha exports are ready.";
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
    if (overlayForegroundVideo) {
      overlayForegroundVideo.pause();
    }
    if (overlayAlphaVideo) {
      overlayAlphaVideo.pause();
    }
  }

  function ensureMediaSource(video, url) {
    if (!video || !url) {
      return false;
    }
    if (video.dataset.assetUrl === url) {
      return false;
    }
    video.dataset.assetUrl = url;
    video.src = withCacheBust(url);
    video.load();
    return true;
  }

  function ensurePreviewVideo(url) {
    if (!previewVideo || !url) {
      return;
    }
    if (state.currentVideoUrl === url) {
      return;
    }
    state.currentVideoUrl = url;
    previewVideo.src = withCacheBust(url);
    previewVideo.load();
  }

  function syncOverlayPlayback() {
    if (!previewVideo || !overlayForegroundVideo || !overlayAlphaVideo || state.mode !== "overlay") {
      return;
    }
    const targetTime = previewVideo.currentTime || 0;
    const tolerance = 0.08;

    [overlayForegroundVideo, overlayAlphaVideo].forEach((video) => {
      try {
        if (Math.abs((video.currentTime || 0) - targetTime) > tolerance) {
          video.currentTime = targetTime;
        }
      } catch (error) {
        // Ignore sync jitter while metadata is still loading.
      }
      video.playbackRate = previewVideo.playbackRate || 1;
      if (previewVideo.paused) {
        video.pause();
      } else {
        video.play().catch(() => {});
      }
    });
  }

  function drawOverlayFrame() {
    if (
      state.mode !== "overlay" ||
      !overlayCanvas ||
      !overlayContext ||
      !previewVideo ||
      !overlayForegroundVideo ||
      !overlayAlphaVideo
    ) {
      cancelOverlayLoop();
      return;
    }

    if (
      overlayForegroundVideo.readyState < 2 ||
      overlayAlphaVideo.readyState < 2 ||
      previewVideo.readyState < 2
    ) {
      state.overlayFrameHandle = window.requestAnimationFrame(drawOverlayFrame);
      return;
    }

    const width = overlayForegroundVideo.videoWidth || previewVideo.videoWidth;
    const height = overlayForegroundVideo.videoHeight || previewVideo.videoHeight;
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

  function bindOverlayVideoSync() {
    if (!previewVideo || state.overlayVideosBound) {
      return;
    }

    const syncAndMaybeDraw = () => {
      syncOverlayPlayback();
      if (state.mode === "overlay" && state.overlayFrameHandle === null) {
        state.overlayFrameHandle = window.requestAnimationFrame(drawOverlayFrame);
      }
    };

    ["play", "pause", "seeking", "seeked", "timeupdate", "ratechange", "loadeddata"].forEach((eventName) => {
      previewVideo.addEventListener(eventName, syncAndMaybeDraw);
    });

    state.overlayVideosBound = true;
  }

  function renderOverlayPreview(payload) {
    const sourceUrl = payload.source_video_url || root.dataset.sourceVideoEndpoint || null;
    const foregroundUrl = payload.artifacts?.["foreground.mp4"] || null;
    const alphaUrl = payload.artifacts?.["alpha.mp4"] || null;

    if (!sourceUrl || !foregroundUrl || !alphaUrl || !previewVideo || !overlayCanvas) {
      clearOverlayCanvas();
      previewVideo?.removeAttribute("src");
      previewVideo?.load();
      if (previewVideo) {
        previewVideo.hidden = true;
      }
      if (previewPlaceholder) {
        previewPlaceholder.hidden = false;
        previewPlaceholder.textContent = "Waiting for foreground and alpha streams for overlay preview.";
      }
      return;
    }

    bindOverlayVideoSync();
    ensurePreviewVideo(sourceUrl);
    ensureMediaSource(overlayForegroundVideo, foregroundUrl);
    ensureMediaSource(overlayAlphaVideo, alphaUrl);
    if (previewPlaceholder) {
      previewPlaceholder.hidden = true;
    }
    previewVideo.hidden = false;
    overlayCanvas.hidden = false;
    syncOverlayPlayback();
    if (state.overlayFrameHandle === null) {
      state.overlayFrameHandle = window.requestAnimationFrame(drawOverlayFrame);
    }
  }

  function renderStandardPreview(url) {
    clearOverlayCanvas();
    if (!previewVideo || !previewPlaceholder) {
      return;
    }
    if (!url) {
      state.currentVideoUrl = null;
      previewVideo.removeAttribute("src");
      previewVideo.load();
      previewVideo.hidden = true;
      previewPlaceholder.hidden = false;
      previewPlaceholder.textContent = "Waiting for the selected preview stream.";
      return;
    }
    previewPlaceholder.hidden = true;
    previewVideo.hidden = false;
    ensurePreviewVideo(url);
  }

  function renderPreview(payload) {
    if (!previewCaption) {
      return;
    }

    previewCaption.textContent = previewCaptionFor(payload);
    if (state.mode === "overlay") {
      renderOverlayPreview(payload);
      return;
    }
    renderStandardPreview(previewUrlFor(payload));
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
