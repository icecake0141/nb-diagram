import { defineConfig } from 'vite';
import { resolve } from 'node:path';

export default defineConfig({
  build: {
    outDir: resolve(__dirname, '../static/dist'),
    emptyOutDir: false,
    rollupOptions: {
      input: {
        app: resolve(__dirname, 'src/app-main.ts'),
      },
      output: {
        entryFileNames: 'app-main.js',
        chunkFileNames: 'chunks/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash][extname]',
      },
    },
  },
});
