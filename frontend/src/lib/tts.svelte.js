// Text-to-speech controller built on the browser Web Speech API.
// No dependencies, no API keys, works offline. The translated text already
// lives in the frontend, so speech is generated entirely client-side.

export function createTTS() {
  const supported =
    typeof window !== "undefined" &&
    "speechSynthesis" in window &&
    "SpeechSynthesisUtterance" in window;

  const synth = supported ? window.speechSynthesis : null;

  let enabled = $state(true); // auto-speak finalized words by default
  let speaking = $state(false);
  let voices = $state([]);
  let selectedVoiceURI = $state("");

  function loadVoices() {
    if (!supported) return;
    const list = synth.getVoices();
    if (!list.length) return;
    voices = list;
    if (!selectedVoiceURI) {
      // Prefer an English voice, fall back to the first available.
      const en = list.find((v) => v.lang.toLowerCase().startsWith("en"));
      selectedVoiceURI = (en ?? list[0]).voiceURI;
    }
  }

  if (supported) {
    loadVoices();
    // voiceschanged is the one event fired by SpeechSynthesis itself.
    synth.onvoiceschanged = loadVoices;
  }

  function speak(text) {
    if (!supported || !text) return;
    const utterance = new SpeechSynthesisUtterance(text);
    const voice = voices.find((v) => v.voiceURI === selectedVoiceURI);
    if (voice) utterance.voice = voice;
    utterance.rate = 1;
    utterance.pitch = 1;
    // start/end/error fire on the utterance, not on speechSynthesis.
    utterance.onstart = () => (speaking = true);
    utterance.onend = () => (speaking = false);
    utterance.onerror = () => (speaking = false);
    // Cancel anything queued so the latest utterance wins (avoids backlog
    // when words finalize faster than they can be spoken).
    synth.cancel();
    synth.speak(utterance);
  }

  function cancel() {
    if (supported) synth.cancel();
    speaking = false;
  }

  function toggle() {
    enabled = !enabled;
    if (!enabled) cancel();
  }

  function setVoice(uri) {
    selectedVoiceURI = uri;
  }

  return {
    get supported() {
      return supported;
    },
    get enabled() {
      return enabled;
    },
    get speaking() {
      return speaking;
    },
    get voices() {
      return voices;
    },
    get selectedVoiceURI() {
      return selectedVoiceURI;
    },
    speak,
    cancel,
    toggle,
    setVoice,
  };
}
