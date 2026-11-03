import {defineConfig} from 'vite';
import {fileURLToPath} from 'node:url';

export default defineConfig({
  root: fileURLToPath(new URL('.', import.meta.url)),
  envDir: fileURLToPath(new URL('./.local-env', import.meta.url)),
  envPrefix: 'PUBLIC_WEBSITE_',
  build: {target: 'es2022', sourcemap: false},
  server: {fs: {strict: true, allow: [fileURLToPath(new URL('.', import.meta.url))]}},
});
