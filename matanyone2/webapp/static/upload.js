import {
  formatBytes,
  formatDuration,
  parseJson,
  probeVideoFile,
  setStatus,
} from "/static/shared.js";

function bindUploadPage() {
  const form = document.getElementById("upload-form");
  if (!form) {
    return;
  }

  const fileInput = document.getElementById("video-file");
  const dropzone = document.getElementById("dropzone-panel");
  const submitButton = document.getElementById("upload-submit");
  const resetButton = document.getElementById("upload-reset");
  const status = document.getElementById("upload-status");
  const mediaCard = document.getElementById("media-info-card");
  const preview = document.getElementById("media-preview");
  const mediaName = document.getElementById("media-name");
  const mediaType = document.getElementById("media-type");
  const mediaSize = document.getElementById("media-size");
  const mediaResolution = document.getElementById("media-resolution");
  const mediaDuration = document.getElementById("media-duration");

  function resetMediaCard() {
    if (mediaCard) {
      mediaCard.dataset.empty = "true";
    }
    if (preview) {
      preview.dataset.ready = "false";
      preview.textContent = "No clip selected";
    }
    if (mediaName) {
      mediaName.textContent = "No file selected";
    }
    if (mediaType) {
      mediaType.textContent = "-";
    }
    if (mediaSize) {
      mediaSize.textContent = "-";
    }
    if (mediaResolution) {
      mediaResolution.textContent = "-";
    }
    if (mediaDuration) {
      mediaDuration.textContent = "-";
    }
    if (submitButton) {
      submitButton.disabled = true;
    }
  }

  async function updateMediaCard(file) {
    if (!file) {
      resetMediaCard();
      setStatus(status, "Select a source clip to prepare the draft.", false);
      return;
    }

    if (mediaCard) {
      mediaCard.dataset.empty = "false";
    }
    if (preview) {
      preview.dataset.ready = "true";
      preview.textContent = (file.name.split(".").pop() || "video").toUpperCase();
    }
    if (mediaName) {
      mediaName.textContent = file.name;
    }
    if (mediaType) {
      mediaType.textContent = file.type || "video";
    }
    if (mediaSize) {
      mediaSize.textContent = formatBytes(file.size);
    }
    if (mediaResolution) {
      mediaResolution.textContent = "Reading metadata...";
    }
    if (mediaDuration) {
      mediaDuration.textContent = "Reading metadata...";
    }

    try {
      const metadata = await probeVideoFile(file);
      if (mediaResolution) {
      mediaResolution.textContent = `${metadata.width} x ${metadata.height}`;
      }
      if (mediaDuration) {
        mediaDuration.textContent = formatDuration(metadata.duration);
      }
      if (submitButton) {
        submitButton.disabled = false;
      }
      setStatus(status, "Draft ready to create. Continue into annotation when ready.", false);
    } catch (error) {
      if (mediaResolution) {
        mediaResolution.textContent = "-";
      }
      if (mediaDuration) {
        mediaDuration.textContent = "-";
      }
      if (submitButton) {
        submitButton.disabled = false;
      }
      setStatus(status, error.message, true);
    }
  }

  function assignDroppedFiles(files) {
    if (!fileInput || !files?.length) {
      return;
    }
    const transfer = new DataTransfer();
    transfer.items.add(files[0]);
    fileInput.files = transfer.files;
    updateMediaCard(files[0]);
  }

  dropzone?.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      fileInput?.click();
    }
  });

  ["dragenter", "dragover"].forEach((eventName) => {
    dropzone?.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropzone.dataset.dragging = "true";
    });
  });

  ["dragleave", "drop"].forEach((eventName) => {
    dropzone?.addEventListener(eventName, () => {
      if (dropzone) {
        dropzone.dataset.dragging = "false";
      }
    });
  });

  dropzone?.addEventListener("drop", (event) => {
    event.preventDefault();
    assignDroppedFiles(event.dataTransfer?.files);
  });

  fileInput?.addEventListener("change", () => {
    updateMediaCard(fileInput.files?.[0] || null);
  });

  resetButton?.addEventListener("click", () => {
    if (fileInput) {
      fileInput.value = "";
    }
    resetMediaCard();
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const file = fileInput?.files?.[0];
    if (!file) {
      setStatus(status, "Select a video before entering the workbench.", true);
      return;
    }

    const body = new FormData();
    body.append("video", file);
    if (submitButton) {
      submitButton.disabled = true;
    }
    setStatus(status, "Uploading clip and preparing draft...", false);

    try {
      const payload = await parseJson(
        await fetch(form.dataset.uploadEndpoint, {
          method: "POST",
          body,
        })
      );
      window.location.assign(`/drafts/${payload.draft_id}/annotate`);
    } catch (error) {
      if (submitButton) {
        submitButton.disabled = false;
      }
      setStatus(status, error.message, true);
    }
  });

  resetMediaCard();
}

document.addEventListener("DOMContentLoaded", bindUploadPage);
