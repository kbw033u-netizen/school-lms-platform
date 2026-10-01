document.querySelectorAll("[data-video-player]").forEach((player) => {
  const video = player.querySelector("video");
  const zoomIn = player.querySelector("[data-zoom-in]");
  const zoomOut = player.querySelector("[data-zoom-out]");
  const reset = player.querySelector("[data-zoom-reset]");
  const status = player.querySelector("[data-zoom-status]");
  const minZoom = 1;
  const maxZoom = 1.75;
  const zoomStep = 0.25;
  let zoom = minZoom;

  function updateZoom() {
    video.style.transform = `scale(${zoom})`;
    status.value = `${Math.round(zoom * 100)}%`;
    status.textContent = status.value;
    zoomIn.disabled = zoom >= maxZoom;
    zoomOut.disabled = zoom <= minZoom;
    reset.disabled = zoom === minZoom;
  }

  zoomIn.addEventListener("click", () => {
    zoom = Math.min(maxZoom, Number((zoom + zoomStep).toFixed(2)));
    updateZoom();
  });

  zoomOut.addEventListener("click", () => {
    zoom = Math.max(minZoom, Number((zoom - zoomStep).toFixed(2)));
    updateZoom();
  });

  reset.addEventListener("click", () => {
    zoom = minZoom;
    updateZoom();
  });

  updateZoom();
});