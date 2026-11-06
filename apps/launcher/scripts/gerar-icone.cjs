// Gera build/icon.png (512x512) do ATTO Tools. Uso: npx electron apps/launcher/scripts/gerar-icone.cjs --disable-gpu
const { app, BrowserWindow } = require('electron')
const { mkdirSync, writeFileSync } = require('node:fs')
const { join } = require('node:path')

const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512">
  <rect width="512" height="512" rx="112" fill="#0e1014"/>
  <rect x="14" y="14" width="484" height="484" rx="100" fill="none" stroke="#ffffff1f" stroke-width="4"/>
  <rect x="168" y="84" width="176" height="344" rx="30" fill="none" stroke="#2ee6c8" stroke-width="14"/>
  <path d="M222 214 L306 256 L222 298 Z" fill="#2ee6c8"/>
</svg>`

app.whenReady().then(async () => {
  const w = new BrowserWindow({ width: 512, height: 512, show: false, frame: false, useContentSize: true, webPreferences: { offscreen: false } })
  await w.loadURL('data:text/html;charset=utf-8,' + encodeURIComponent(`<body style="margin:0;background:transparent">${svg}</body>`))
  await new Promise((r) => setTimeout(r, 800))
  const img = await w.webContents.capturePage({ x: 0, y: 0, width: 512, height: 512 })
  const destino = join(__dirname, '..', 'build')
  mkdirSync(destino, { recursive: true })
  writeFileSync(join(destino, 'icon.png'), img.toPNG())
  console.log('icone:', img.getSize())
  app.quit()
})
