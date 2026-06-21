<script>
  import { onMount } from "svelte";
  import { createSignStore } from "./lib/signSocket.svelte.js";
  import { createTTS } from "./lib/tts.svelte.js";
  import Camera from "./lib/Camera.svelte";
  import TranslationPanel from "./lib/TranslationPanel.svelte";

  const store = createSignStore();
  const tts = createTTS();
  let cameraActive = $state(false);

  const statusInfo = $derived(
    {
      idle: { label: "Disconnected", cls: "off" },
      connecting: { label: "Connecting…", cls: "warn" },
      connected: { label: "Connected", cls: "on" },
      error: { label: "Connection error", cls: "err" },
    }[store.status] ?? { label: "Disconnected", cls: "off" },
  );

  // Auto-speak each word as it finalizes into the sentence.
  let lastSentence = "";
  $effect(() => {
    const s = store.sentence;
    if (s === lastSentence) return;
    if (tts.enabled && s && s.startsWith(lastSentence)) {
      const added = s.slice(lastSentence.length).trim();
      if (added) tts.speak(added);
    }
    lastSentence = s;
  });

  onMount(() => {
    store.connect();
    return () => {
      tts.cancel();
      store.disconnect();
    };
  });

  function toggleCamera() {
    cameraActive = !cameraActive;
  }

  function speakSentence() {
    if (store.sentence) tts.speak(store.sentence);
  }
</script>

<div class="app">
  <header class="topbar">
    <div class="brand">
      <span class="logo-dot"></span>
      <div>
        <h1>SignSpeak</h1>
        <p class="tag">Real-time ASL fingerspelling → text</p>
      </div>
    </div>
    <div class="status {statusInfo.cls}">
      <span class="status-dot"></span>
      {statusInfo.label}
    </div>
  </header>

  <div class="toolbar">
    <div class="group">
      <button class="btn primary" onclick={toggleCamera}>
        {cameraActive ? "Stop camera" : "Start camera"}
      </button>
      <button
        class="btn ghost"
        onclick={() => store.reset()}
        disabled={!store.sentence && !store.word}
      >
        Reset
      </button>
    </div>
    {#if tts.supported}
      <div class="group">
        <select
          class="voice-select"
          value={tts.selectedVoiceURI}
          onchange={(e) => tts.setVoice(e.currentTarget.value)}
          aria-label="Voice"
        >
          {#each tts.voices as v, i (i)}
            <option value={v.voiceURI}>{v.name} ({v.lang})</option>
          {/each}
        </select>
        <button
          class="btn toggle"
          aria-pressed={tts.enabled}
          onclick={() => tts.toggle()}
          title="Toggle auto-speak"
        >
          Auto-speak {tts.enabled ? "on" : "off"}
        </button>
        <button
          class="btn ghost"
          class:speaking={tts.speaking}
          onclick={speakSentence}
          disabled={!store.sentence}
        >
          {tts.speaking ? "Speaking…" : "Speak"}
        </button>
      </div>
    {/if}
  </div>

  <main class="grid">
    <Camera {store} active={cameraActive} />
    <TranslationPanel
      letter={store.letter}
      word={store.word}
      sentence={store.sentence}
      handDetected={store.handDetected}
    />
  </main>

  <footer class="foot">
    Sign a letter · hold steady to type · lower your hand to finalize a word
  </footer>
</div>

<style>
  .app {
    max-width: 1180px;
    margin: 0 auto;
    padding: 28px 22px 48px;
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    flex-wrap: wrap;
  }

  .brand {
    display: flex;
    align-items: center;
    gap: 14px;
  }

  .logo-dot {
    width: 38px;
    height: 38px;
    border-radius: 12px;
    background: var(--accent-grad);
    box-shadow: 0 8px 24px rgba(139, 92, 246, 0.4);
    flex-shrink: 0;
  }

  h1 {
    font-size: 1.5rem;
    font-weight: 800;
    letter-spacing: -0.02em;
    margin: 0;
    line-height: 1.1;
  }

  .tag {
    margin: 2px 0 0;
    font-size: 0.85rem;
    color: var(--dim);
  }

  .status {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 7px 14px;
    font-size: 0.82rem;
    font-weight: 600;
    border-radius: 999px;
    border: 1px solid var(--border);
    background: var(--surface);
    backdrop-filter: blur(10px);
  }

  .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--dim);
  }

  .status.on {
    color: #d1fae5;
  }
  .status.on .status-dot {
    background: #10b981;
  }
  .status.warn {
    color: #fde68a;
  }
  .status.warn .status-dot {
    background: #f59e0b;
  }
  .status.err {
    color: #fca5a5;
  }
  .status.err .status-dot {
    background: #ef4444;
  }
  .status.off {
    color: var(--dim);
  }

  .toolbar {
    display: flex;
    gap: 12px;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
  }

  .group {
    display: flex;
    gap: 12px;
    align-items: center;
    flex-wrap: wrap;
  }

  .voice-select {
    font: inherit;
    font-size: 0.88rem;
    color: var(--text);
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 10px 12px;
    cursor: pointer;
    max-width: 220px;
  }

  .voice-select option {
    background: #15151f;
    color: var(--text);
  }

  .toggle[aria-pressed="true"] {
    color: #d1fae5;
    border-color: rgba(16, 185, 129, 0.4);
    background: rgba(16, 185, 129, 0.12);
  }

  .btn.speaking {
    color: #cffafe;
    border-color: rgba(6, 182, 212, 0.4);
    background: rgba(6, 182, 212, 0.12);
  }

  .btn {
    font: inherit;
    font-weight: 600;
    padding: 11px 22px;
    border-radius: 12px;
    border: 1px solid var(--border);
    cursor: pointer;
    transition:
      transform 0.12s ease,
      box-shadow 0.12s ease,
      opacity 0.12s ease;
  }

  .btn:active {
    transform: translateY(1px);
  }
  .btn:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }

  .btn.primary {
    color: white;
    background: var(--accent-grad);
    border-color: transparent;
    box-shadow: 0 8px 22px rgba(139, 92, 246, 0.35);
  }

  .btn.primary:hover:not(:disabled) {
    box-shadow: 0 10px 28px rgba(139, 92, 246, 0.5);
  }

  .btn.ghost {
    color: var(--text);
    background: var(--surface);
    backdrop-filter: blur(10px);
  }

  .btn.ghost:hover:not(:disabled) {
    background: rgba(255, 255, 255, 0.08);
  }

  .grid {
    display: grid;
    grid-template-columns: 1.4fr 1fr;
    gap: 20px;
    align-items: start;
  }

  .foot {
    text-align: center;
    font-size: 0.82rem;
    color: var(--dim);
    padding-top: 4px;
  }

  @media (max-width: 900px) {
    .grid {
      grid-template-columns: 1fr;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .btn {
      transition: none;
    }
  }
</style>
