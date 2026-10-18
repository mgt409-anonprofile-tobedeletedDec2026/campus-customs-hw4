import { Agent } from "node:http";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The backend (FastAPI) runs on port 8000; the dev server forwards API and image requests to it.
// keepAlive is off so `uvicorn --reload` can restart promptly instead of waiting on idle connections.
// xfwd passes each shopper's real address to the backend (X-Forwarded-For) for per-shopper spam limits.
const backend = { target: "http://127.0.0.1:8000", agent: new Agent({ keepAlive: false }), xfwd: true };

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": backend,
      "/images": backend,
    },
  },
});
