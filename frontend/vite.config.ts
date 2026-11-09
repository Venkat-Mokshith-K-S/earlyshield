import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// This project is ESM (package.json has "type": "module"), so __dirname is
// not available — derive the equivalent from import.meta.url instead.
const currentDir = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      // Mirrors "@/*" -> "src/*" in tsconfig.json. tsconfig's `paths` only
      // satisfies the TypeScript type-checker; Rollup (the actual bundler
      // behind `vite build`) needs this separate alias to resolve the same
      // imports at build time. (Learned this the hard way last time.)
      "@": path.resolve(currentDir, "./src"),
    },
  },
  server: {
    host: true,
    port: 5173,
    proxy: { "/api": { target: "http://127.0.0.1:8000", changeOrigin: true } },
  },
});
