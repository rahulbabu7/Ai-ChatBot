import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import jsconfigPaths from 'vite-jsconfig-paths';
import path from 'path';

const resolvePath = (str) => path.resolve(__dirname, str);

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  // Base URL for deployment (only path, no domain)
  const BASE_URL = env.VITE_APP_BASE_NAME || '/';
  const PORT = 3000;

  return {
    base: BASE_URL, // important: must match Router basename
    server: {
      port: PORT,
      host: true,
      // automatically open login page in browser
      open: `${BASE_URL}login`,
    },
    preview: {
      host: true,
      open: `${BASE_URL}login`,
    },
    define: {
      global: 'window',
    },
    resolve: {
      alias: [
        { find: '@', replacement: path.resolve(__dirname, 'src') },
        { find: 'assets', replacement: path.resolve(__dirname, 'src/assets') },
      ],
    },
    css: {
      preprocessorOptions: {
        scss: { charset: false },
        less: { charset: false },
      },
      charset: false,
      postcss: {
        plugins: [
          {
            postcssPlugin: 'internal:charset-removal',
            AtRule: { charset: (atRule) => atRule.remove() },
          },
        ],
      },
    },
    build: {
      chunkSizeWarningLimit: 1600,
      rollupOptions: {
        input: {
          main: resolvePath('index.html'),
        },
      },
    },
    plugins: [react(), jsconfigPaths()],
  };
});
