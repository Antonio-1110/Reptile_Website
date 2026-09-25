import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss()
  ],
  // `npm test`: Vitest with a browser-like DOM; component CSS isn't needed to test behaviour.
  test: {
    environment: 'jsdom',
    include: ['src/**/*.test.{js,jsx}'], // e2e/ is Playwright's (npm run e2e)
    setupFiles: './src/test/setup.js',
    css: false,
  },
})
