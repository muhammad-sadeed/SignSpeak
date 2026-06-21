import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";
import basicSsl from "@vitejs/plugin-basic-ssl";

// https://vite.dev/config/
export default defineConfig({
  plugins: [svelte(), basicSsl()],
  // server: { host: true },
  server: {
    // Force Vite to listen on your local network
    host: "0.0.0.0",
    proxy: {
      // Any frontend request to /ws will be caught by Vite
      "/ws": {
        target: "http://127.0.0.1:8000", // Your plain HTTP FastAPI backend
        ws: true, // Tell Vite to proxy WebSockets!
        secure: false, // Don't verify local SSL certs
        changeOrigin: true,
      },
    },
  },
});
