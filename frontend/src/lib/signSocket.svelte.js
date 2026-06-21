// Reactive WebSocket store backed by Svelte 5 runes.
// Connects to the FastAPI backend, streams JPEG frames, and exposes the
// latest translation state as reactive getters.

const WS_URL =
  import.meta.env.VITE_WS_URL ?? "ws://localhost:8000/ws";

const RECONNECT_BASE_MS = 800;
const RECONNECT_MAX_MS = 8000;

/**
 * @returns {object} store with reactive getters + control methods.
 */
export function createSignStore() {
  let ws = null;
  let reconnectTimer = null;
  let reconnectAttempt = 0;
  let manualClose = false;

  let status = $state("idle"); // idle | connecting | connected | error
  let letter = $state(null);
  let word = $state("");
  let sentence = $state("");
  let handDetected = $state(false);
  let landmarks = $state(null);

  function clearReconnect() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
  }

  function scheduleReconnect() {
    if (manualClose) return;
    clearReconnect();
    const delay = Math.min(
      RECONNECT_BASE_MS * 2 ** reconnectAttempt,
      RECONNECT_MAX_MS,
    );
    reconnectAttempt += 1;
    reconnectTimer = setTimeout(connect, delay);
  }

  function connect() {
    clearReconnect();
    manualClose = false;
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
      return;
    }
    status = "connecting";
    try {
      ws = new WebSocket(WS_URL);
    } catch {
      status = "error";
      scheduleReconnect();
      return;
    }
    ws.binaryType = "arraybuffer";

    ws.onopen = () => {
      reconnectAttempt = 0;
      status = "connected";
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        letter = data.letter ?? null;
        word = data.word ?? "";
        sentence = data.sentence ?? "";
        handDetected = !!data.hand_detected;
        landmarks = data.landmarks ?? null;
      } catch {
        // ignore malformed messages
      }
    };

    ws.onclose = () => {
      status = "idle";
      ws = null;
      scheduleReconnect();
    };

    ws.onerror = () => {
      status = "error";
    };
  }

  function sendFrame(blob) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(blob);
    }
  }

  function reset() {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "reset" }));
    }
  }

  function disconnect() {
    manualClose = true;
    clearReconnect();
    if (ws) {
      ws.close();
      ws = null;
    }
    status = "idle";
  }

  return {
    get status() {
      return status;
    },
    get letter() {
      return letter;
    },
    get word() {
      return word;
    },
    get sentence() {
      return sentence;
    },
    get handDetected() {
      return handDetected;
    },
    get landmarks() {
      return landmarks;
    },
    connect,
    sendFrame,
    reset,
    disconnect,
  };
}
