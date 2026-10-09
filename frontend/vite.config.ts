/// <reference types="vitest/config" />
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    // No Docker com Windows/macOS, os eventos de arquivo não chegam ao container:
    // o polling faz o Vite perceber as alterações (ligado pelo docker-compose).
    watch: { usePolling: process.env.VITE_USE_POLLING === "true" },
    // Em desenvolvimento, o Vite repassa /api para o Django. Para o navegador, frontend e
    // API ficam na MESMA origem: não é preciso CORS e o cookie SameSite=Strict funciona.
    // No Docker, o backend é acessado pelo nome do serviço (ver docker-compose.yml).
    proxy: {
      "/api": process.env.API_PROXY_TARGET ?? "http://localhost:8000",
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    globals: true,
    css: false,
  },
});
