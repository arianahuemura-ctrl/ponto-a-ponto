import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import istanbul from "vite-plugin-istanbul";
export default defineConfig({
  plugins: [react(), ...(process.env.PAP_COVERAGE === '1' ? [istanbul({
    include: 'src/**/*', exclude: ['node_modules', '**/*.test.js'],
    extension: ['.js', '.jsx'], requireEnv: false, forceBuildInstrument: true,
  })] : [])],
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
    proxy: { "/api": "http://127.0.0.1:8000" },
  },
});
