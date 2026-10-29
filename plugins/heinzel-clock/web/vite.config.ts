/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import tailwindcss from "@tailwindcss/vite";
export default defineConfig({
 plugins: [tailwindcss()],
 build: { lib: { entry: "src/index.ts", formats: ["es"], fileName: () => "index.js", cssFileName: "style" },
   outDir: "../src/heinzel_clock/views", emptyOutDir: true, assetsInlineLimit: 0,
   rollupOptions: { external: ["react", "react/jsx-runtime", "react-dom", "react-router"],
     output: { paths: { react: "/plugin-sdk/v1/react.js", "react/jsx-runtime": "/plugin-sdk/v1/jsx-runtime.js", "react-dom": "/plugin-sdk/v1/react-dom.js", "react-router": "/plugin-sdk/v1/react-router.js" } } },
   license: { fileName: "licenses.md" }
 },
 test: { setupFiles: ["./src/test-setup.ts"], environment: "jsdom", include: ["src/**/*.test.{ts,tsx}"] }
});
