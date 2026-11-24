import { defineConfig } from 'vite';

export default defineConfig(({ command }) => ({
  // Production assets are served by FastAPI under /static/dist/; in dev the
  // Jinja helper emits canonical http://localhost:5173/src/main.ts URLs.
  base: command === 'build' ? '/static/dist/' : '/',
  build: {
    manifest: true,
    // Only the dist subfolder — emptyOutDir on app/static itself would wipe
    // the avatars and images FastAPI serves.
    outDir: '../backend/app/static/dist',
    emptyOutDir: true,
    rollupOptions: {
      // The lesson page and the teacher's area (/admin) are separate entries;
      // vite_asset() in the backend looks each one up in the manifest.
      input: ['src/main.ts', 'src/admin/main.ts'],
    },
  },
  server: {
    port: 5173,
    strictPort: true,
    // The page itself is served by FastAPI on :8000, so module scripts and
    // CSS-referenced assets are cross-origin requests against this server.
    origin: 'http://localhost:5173',
    cors: {
      origin: ['http://localhost:8000', 'http://127.0.0.1:8000'],
    },
  },
}));
