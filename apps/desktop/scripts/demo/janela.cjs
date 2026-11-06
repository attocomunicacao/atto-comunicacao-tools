// Janela mínima do Electron que abre o renderer em modo demo (usada por capturas.mjs).
const { app, BrowserWindow } = require('electron')
app.whenReady().then(() => {
  const w = new BrowserWindow({ width: 1280, height: 820, backgroundColor: '#0e1014', autoHideMenuBar: true })
  w.loadURL(process.env.DEMO_URL)
})
app.on('window-all-closed', () => app.quit())
