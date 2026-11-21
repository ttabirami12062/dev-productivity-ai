/// <reference types="vitest/config" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  // Same port as before, so local testing steps don't change.
  server: { port: 3001 },
  // Vercel already serves the "build" folder that Create React App produced.
  build: { outDir: 'build' },
  test: { environment: 'jsdom', setupFiles: './src/setupTests.ts', globals: true },
});
