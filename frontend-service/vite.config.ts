import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

export default defineConfig({
  base: "./",
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    host: "0.0.0.0",
    port: 5173,
    strictPort: false,
    hmr: {
      host: "localhost",
      port: 5173,
      protocol: "ws",
    },
    cors: true,
    watch: {
      usePolling: true,
    },
    proxy: {
      // Прокси для API запросов к BFF сервису в Docker
      "/api": {
        // Important for Windows: Node may resolve 'localhost' to IPv6 ::1,
        // while backend listens on IPv4. Use explicit IPv4 loopback.
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        secure: false,
        ws: true, // Поддержка WebSocket для /api/ws/*
      },
    },
  },
});

