import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Two outputs under dist/: js/brand-list.js (IIFE, React bundled; Django mounts it) and css/main.css.
export default defineConfig(({ mode }) => ({
  plugins: [react()],
  // The IIFE bundle has no bundler-provided NODE_ENV; tests keep React's development build.
  define:
    mode === "test"
      ? {}
      : { "process.env.NODE_ENV": JSON.stringify("production") },
  build: {
    outDir: "dist",
    emptyOutDir: false,
    lib: {
      entry: "src/main.jsx",
      formats: ["iife"],
      name: "BrandListApp",
      fileName: () => "js/brand-list.js",
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test-setup.js"],
    globals: true,
  },
}));
