import { resolve } from 'node:path'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'electron-vite'

export default defineConfig({
  main: {},
  preload: {},
  renderer: {
    plugins: [react()],
    // duas páginas: a interface do app e a camada de motion (renderizada quadro a quadro)
    build: { rollupOptions: { input: { index: resolve(__dirname, 'src/renderer/index.html'), motion: resolve(__dirname, 'src/renderer/motion.html') } } }
  }
})
