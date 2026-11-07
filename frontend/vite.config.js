import { defineConfig, loadEnv } from "vite";
import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import istanbul from "vite-plugin-istanbul";
export default defineConfig(({mode}) => {
  const root = fileURLToPath(new URL("..", import.meta.url));
  const environment = process.env.PAP_ENVIRONMENT ?? loadEnv(mode, root, "PAP_ENVIRONMENT").PAP_ENVIRONMENT ?? "production";
  if (!["production", "development"].includes(environment)) throw new Error("PAP_ENVIRONMENT deve ser production ou development");
  return {
  define: {"import.meta.env.PAP_ENVIRONMENT": JSON.stringify(environment)},
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
};
});
