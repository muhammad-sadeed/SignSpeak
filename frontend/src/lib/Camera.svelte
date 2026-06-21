<script>
  import { onMount, onDestroy } from "svelte";
  import { HAND_CONNECTIONS } from "./handConnections.js";

  let { store, active = $bindable(false) } = $props();

  // Plain (non-reactive) DOM refs so the active $effect doesn't depend on them.
  let videoEl;
  let overlayEl;

  let ready = $state(false);
  let errorMsg = $state("");
  let aspect = $state("4 / 3");

  let stream = null;
  let running = false;
  let sendTimer = null;
  let rafId = null;

  let captureCanvas = null;
  let captureCtx = null;

  const SEND_WIDTH = 640;
  const SEND_INTERVAL_MS = 80; // ~12.5 fps

  function ensureCaptureCanvas() {
    if (!captureCanvas) {
      captureCanvas = document.createElement("canvas");
      captureCtx = captureCanvas.getContext("2d");
    }
  }

  async function start() {
    if (running) return;
    if (!videoEl) return;
    running = true;
    errorMsg = "";
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "user", width: { ideal: 640 }, height: { ideal: 480 } },
        audio: false,
      });
      if (!running) {
        stream.getTracks().forEach((t) => t.stop());
        stream = null;
        return;
      }
      videoEl.srcObject = stream;
      await videoEl.play();
      ready = true;
      sizeOverlay();
      startLoops();
    } catch (e) {
      running = false;
      ready = false;
      errorMsg =
        e?.name === "NotAllowedError"
          ? "Camera permission denied. Allow access and try again."
          : e?.name === "NotFoundError"
            ? "No camera found on this device."
            : e?.message || "Could not access the camera.";
    }
  }

  function stop() {
    running = false;
    ready = false;
    stopLoops();
    if (stream) {
      stream.getTracks().forEach((t) => t.stop());
      stream = null;
    }
    if (videoEl) videoEl.srcObject = null;
    if (overlayEl) {
      const ctx = overlayEl.getContext("2d");
      ctx?.clearRect(0, 0, overlayEl.width, overlayEl.height);
    }
  }

  function sizeOverlay() {
    if (!overlayEl || !videoEl) return;
    const w = videoEl.videoWidth;
    const h = videoEl.videoHeight;
    if (!w || !h) return;
    overlayEl.width = w;
    overlayEl.height = h;
    aspect = `${w} / ${h}`;
  }

  function startLoops() {
    stopLoops();
    sendTimer = setInterval(captureAndSend, SEND_INTERVAL_MS);
    rafId = requestAnimationFrame(drawLoop);
  }

  function stopLoops() {
    if (sendTimer) {
      clearInterval(sendTimer);
      sendTimer = null;
    }
    if (rafId) {
      cancelAnimationFrame(rafId);
      rafId = null;
    }
  }

  function captureAndSend() {
    if (!running || !videoEl || videoEl.readyState < 2) return;
    const vw = videoEl.videoWidth;
    const vh = videoEl.videoHeight;
    if (!vw || !vh) return;
    ensureCaptureCanvas();
    const scale = Math.min(1, SEND_WIDTH / vw);
    const cw = Math.round(vw * scale);
    const ch = Math.round(vh * scale);
    if (captureCanvas.width !== cw) captureCanvas.width = cw;
    if (captureCanvas.height !== ch) captureCanvas.height = ch;
    // Draw the raw (unmirrored) frame; the backend flips it to match training.
    captureCtx.drawImage(videoEl, 0, 0, cw, ch);
    captureCanvas.toBlob((blob) => {
      if (blob && running) store.sendFrame(blob);
    }, "image/jpeg", 0.7);
  }

  function drawLoop() {
    if (!running) return;
    drawSkeleton();
    rafId = requestAnimationFrame(drawLoop);
  }

  function drawSkeleton() {
    if (!overlayEl) return;
    const ctx = overlayEl.getContext("2d");
    const w = overlayEl.width;
    const h = overlayEl.height;
    ctx.clearRect(0, 0, w, h);
    const lms = store.landmarks;
    if (!lms || lms.length === 0) return;

    ctx.lineWidth = Math.max(2, w * 0.006);
    ctx.lineCap = "round";
    ctx.strokeStyle = "rgba(139, 92, 246, 0.95)";
    ctx.shadowColor = "rgba(6, 182, 212, 0.85)";
    ctx.shadowBlur = 14;
    ctx.beginPath();
    for (const [a, b] of HAND_CONNECTIONS) {
      const pa = lms[a];
      const pb = lms[b];
      if (!pa || !pb) continue;
      ctx.moveTo(pa[0] * w, pa[1] * h);
      ctx.lineTo(pb[0] * w, pb[1] * h);
    }
    ctx.stroke();

    ctx.shadowBlur = 10;
    ctx.fillStyle = "#22d3ee";
    for (const p of lms) {
      ctx.beginPath();
      ctx.arc(p[0] * w, p[1] * h, Math.max(3, w * 0.009), 0, Math.PI * 2);
      ctx.fill();
    }
  }

  function onLoadedMetadata() {
    sizeOverlay();
  }

  $effect(() => {
    if (active) start();
    else stop();
  });

  onMount(() => {
    window.addEventListener("resize", sizeOverlay);
  });

  onDestroy(() => {
    window.removeEventListener("resize", sizeOverlay);
    stop();
  });
</script>

<div class="camera">
  <div class="video-wrap" style="aspect-ratio: {aspect}">
    <video
      bind:this={videoEl}
      playsinline
      muted
      onloadedmetadata={onLoadedMetadata}
    ></video>
    <canvas bind:this={overlayEl} class="overlay"></canvas>

    {#if ready}
      <div class="badge" class:live={store.handDetected}>
        <span class="dot"></span>
        {store.handDetected ? "Hand detected" : "Listening"}
      </div>
    {/if}

    {#if !ready && !errorMsg}
      <div class="placeholder">
        <svg viewBox="0 0 24 24" width="56" height="56" aria-hidden="true">
          <path
            fill="currentColor"
            d="M4 7h3l1.5-2h7L17 7h3a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2m8 11a5 5 0 1 0-5-5 5 5 0 0 0 5 5m0-2a3 3 0 1 1 3-3 3 3 0 0 1-3 3"
          />
        </svg>
        <p class="ph-title">Camera is off</p>
        <p class="ph-sub">Press Start to begin translating</p>
      </div>
    {/if}

    {#if errorMsg}
      <div class="placeholder error">
        <p>{errorMsg}</p>
      </div>
    {/if}
  </div>
</div>

<style>
  .camera {
    width: 100%;
  }

  .video-wrap {
    position: relative;
    width: 100%;
    max-height: 70vh;
    background: #05050a;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    overflow: hidden;
    box-shadow: var(--shadow);
  }

  video {
    width: 100%;
    height: 100%;
    object-fit: cover;
    transform: scaleX(-1); /* selfie mirror */
    display: block;
  }

  .overlay {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
  }

  .badge {
    position: absolute;
    top: 14px;
    left: 14px;
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 6px 12px;
    font-size: 0.8rem;
    font-weight: 600;
    color: var(--dim);
    background: rgba(0, 0, 0, 0.45);
    backdrop-filter: blur(8px);
    border: 1px solid var(--border);
    border-radius: 999px;
  }

  .badge.live {
    color: #d1fae5;
    border-color: rgba(16, 185, 129, 0.4);
  }

  .dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--dim);
  }

  .badge.live .dot {
    background: #10b981;
    box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.6);
    animation: pulse 1.6s infinite;
  }

  @keyframes pulse {
    0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.6); }
    70% { box-shadow: 0 0 0 8px rgba(16, 185, 129, 0); }
    100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
  }

  .placeholder {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 6px;
    color: var(--dim);
    text-align: center;
    padding: 24px;
  }

  .placeholder svg {
    color: rgba(255, 255, 255, 0.18);
    margin-bottom: 6px;
  }

  .ph-title {
    font-size: 1.05rem;
    font-weight: 600;
    color: var(--text);
  }

  .ph-sub {
    font-size: 0.88rem;
  }

  .placeholder.error {
    color: #fca5a5;
  }

  @media (prefers-reduced-motion: reduce) {
    .badge.live .dot { animation: none; }
  }
</style>
