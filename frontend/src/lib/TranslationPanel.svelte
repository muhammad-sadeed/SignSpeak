<script>
  import { fade } from "svelte/transition";

  let { letter, word, sentence, handDetected } = $props();

  let words = $derived(sentence ? sentence.split(" ") : []);
</script>

<section class="panel">
  <div class="hero" class:dim={!letter}>
    {#if letter}
      <span class="hero-letter">{letter}</span>
    {:else}
      <span class="hero-listening">
        <span class="pulse-dot"></span>
        Listening
      </span>
    {/if}
    <span class="hero-label">
      {letter ? "Current letter" : handDetected ? "Hold a sign steady" : "Show a hand sign"}
    </span>
  </div>

  <div class="word-row">
    <span class="word-label">Building</span>
    <span class="word" class:empty={!word}>
      {word || "—"}<span class="caret" class:show={!!word}></span>
    </span>
  </div>

  <div class="sentence-card">
    <div class="sentence-head">
      <span class="bar"></span>
      <span class="sentence-label">Sentence</span>
    </div>
    <div class="sentence-body">
      {#if words.length === 0}
        <span class="sentence-empty">Finalized words will appear here</span>
      {:else}
        {#each words as w, i (i)}
          <span class="chip" in:fade={{ duration: 280 }}>{w}</span>
        {/each}
      {/if}
    </div>
  </div>
</section>

<style>
  .panel {
    display: flex;
    flex-direction: column;
    gap: 18px;
    height: 100%;
  }

  .hero {
    position: relative;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 10px;
    padding: 34px 20px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--surface);
    backdrop-filter: blur(20px);
    box-shadow: var(--shadow);
    overflow: hidden;
    min-height: 200px;
  }

  .hero::before {
    content: "";
    position: absolute;
    inset: 0;
    background: radial-gradient(
      circle at 50% 30%,
      rgba(139, 92, 246, 0.16),
      transparent 60%
    );
    pointer-events: none;
  }

  .hero-letter {
    font-size: clamp(5rem, 14vw, 8.5rem);
    font-weight: 800;
    line-height: 1;
    background: var(--accent-grad);
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
    filter: drop-shadow(0 6px 24px rgba(139, 92, 246, 0.35));
  }

  .hero-listening {
    display: inline-flex;
    align-items: center;
    gap: 12px;
    font-size: clamp(1.4rem, 3vw, 2rem);
    font-weight: 600;
    color: var(--text);
  }

  .pulse-dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: var(--accent-2);
    box-shadow: 0 0 0 0 rgba(6, 182, 212, 0.6);
    animation: pulse-cyan 1.8s infinite;
  }

  @keyframes pulse-cyan {
    0% { box-shadow: 0 0 0 0 rgba(6, 182, 212, 0.6); }
    70% { box-shadow: 0 0 0 12px rgba(6, 182, 212, 0); }
    100% { box-shadow: 0 0 0 0 rgba(6, 182, 212, 0); }
  }

  .hero-label {
    font-size: 0.85rem;
    color: var(--dim);
    letter-spacing: 0.02em;
  }

  .word-row {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 16px 20px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--surface);
    backdrop-filter: blur(20px);
  }

  .word-label {
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: var(--dim);
  }

  .word {
    font-family: var(--mono);
    font-size: 1.6rem;
    font-weight: 600;
    color: var(--text);
    letter-spacing: 0.04em;
    min-height: 1.6em;
    display: inline-flex;
    align-items: center;
  }

  .word.empty {
    color: var(--dim);
  }

  .caret {
    display: inline-block;
    width: 2px;
    height: 1.2em;
    margin-left: 6px;
    background: var(--accent-2);
    opacity: 0;
  }

  .caret.show {
    opacity: 1;
    animation: blink 1.1s steps(1) infinite;
  }

  @keyframes blink {
    50% { opacity: 0; }
  }

  .sentence-card {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 18px 20px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--surface);
    backdrop-filter: blur(20px);
    box-shadow: var(--shadow);
    min-height: 120px;
  }

  .sentence-head {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .bar {
    width: 4px;
    height: 16px;
    border-radius: 2px;
    background: var(--accent-grad);
  }

  .sentence-label {
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: var(--dim);
  }

  .sentence-body {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    align-content: flex-start;
    overflow-y: auto;
    flex: 1;
  }

  .chip {
    padding: 6px 14px;
    font-size: 1.05rem;
    font-weight: 500;
    color: var(--text);
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid var(--border);
    border-radius: 10px;
  }

  .sentence-empty {
    color: var(--dim);
    font-size: 0.9rem;
  }

  @media (prefers-reduced-motion: reduce) {
    .pulse-dot,
    .caret.show {
      animation: none;
    }
  }
</style>
