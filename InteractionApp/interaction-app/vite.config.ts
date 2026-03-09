import { sveltekit } from "@sveltejs/kit/vite";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [sveltekit()],
  server: {
    proxy: {
      "/spatial": { target: "ws://localhost:8080", ws: true },
      "/status": { target: "ws://localhost:8080", ws: true },
      "/api": { target: "http://localhost:8080" },
    },
  },
});
