import react from "@vitejs/plugin-react"
import path from "path"
import { defineConfig } from "vite"

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // Pinned dev port (strict): 5173 is taken by another app on this machine,
  // and the API allow-lists this exact origin — auto-increment would break CORS.
  server: {
    port: 5175,
    strictPort: true,
  },
  resolve: {
    alias: {
      "@": path.resolve(import.meta.dirname, "./src"),
    },
  },
})
