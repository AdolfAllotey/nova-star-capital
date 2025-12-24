// /opt/nsc/app/vite.config.js
import { defineConfig, loadEnv } from "vite";
import legacy from "@vitejs/plugin-legacy";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const API_BASE = env.VITE_API_BASE || (mode === "production"
    ? "https://api.preprod.novastarcapital.fr"
    : "http://127.0.0.1:8000");

  return {
    base: "/",
    plugins: [
      legacy({
        // Cible Safari 13+ (très prudent ; ajuste à 14 si tu veux)
        targets: ["defaults", "Safari >= 13", "iOS >= 13"],
        additionalLegacyPolyfills: [
          "regenerator-runtime/runtime"
        ]
      }),
    ],
    define: {
      __API_BASE__: JSON.stringify(API_BASE),
    },
    build: {
      target: "es2018",        // transpile un cran plus bas pour Safari
      sourcemap: true,         // utile pour diagnostiquer (temporaire)
      chunkSizeWarningLimit: 800,
      rollupOptions: {
        output: {
          manualChunks: undefined,
        },
      },
    },
    server: {
      host: "127.0.0.1",
      port: 5173
    },
    preview: {
      host: "127.0.0.1",
      port: 5174
    }
  };
});
