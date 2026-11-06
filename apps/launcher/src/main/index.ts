import { writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { app, BrowserWindow, ipcMain } from 'electron'
import { abrir, buscarManifest, compararVersoes, instalar, lerEstado, reverter, type Manifest } from './atualizador.ts'

const REPO = 'attocomunicacao/atto-comunicacao-tools'
const EXECUTAVEL = 'ATTO Tools.exe'
// Em produção os endereços são fixos. Só o app em desenvolvimento aceita trocar (para testar com um servidor local).
const dev = !app.isPackaged
const MANIFEST_URL = (dev && process.env['ATTO_MANIFEST_URL']) || `https://github.com/${REPO}/releases/latest/download/manifest.json`
const PREFIXO = (dev && process.env['ATTO_PREFIXO']) || `https://github.com/${REPO}/releases/download/`
const raiz = () => (dev && process.env['ATTO_RAIZ']) || join(process.env['LOCALAPPDATA'] ?? app.getPath('appData'), 'ATTO Tools')

let janela: BrowserWindow | null = null
let ultima: Manifest | null = null
let semConexao = false

async function consultar(): Promise<void> {
  try {
    ultima = await buscarManifest(MANIFEST_URL)
    semConexao = false
  } catch {
    ultima = null
    semConexao = true
  }
}

app.whenReady().then(() => {
  ipcMain.handle('launcher:estado', async () => {
    await consultar()
    const e = lerEstado(raiz())
    return {
      instalada: e.atual,
      anterior: e.anterior,
      ultima: ultima && { versao: ultima.versao, notas: ultima.notas },
      semConexao
    }
  })
  ipcMain.handle('launcher:atualizar', async () => {
    if (!ultima) throw new Error('Não foi possível consultar a versão mais recente.')
    const atual = lerEstado(raiz()).atual
    if (atual && compararVersoes(ultima.versao, atual) <= 0) return
    await instalar({
      raiz: raiz(),
      manifest: ultima,
      prefixoPermitido: PREFIXO,
      aoProgresso: (pct, etapa) => janela?.webContents.send('launcher:progresso', pct, etapa)
    })
  })
  ipcMain.handle('launcher:abrir', () => abrir(raiz(), EXECUTAVEL))
  ipcMain.handle('launcher:reverter', () => void reverter(raiz()))

  janela = new BrowserWindow({
    width: 560,
    height: 560,
    resizable: false,
    backgroundColor: '#0e1014',
    title: 'ATTO Tools',
    autoHideMenuBar: true,
    webPreferences: { preload: join(__dirname, '../preload/index.js'), contextIsolation: true, sandbox: true }
  })
  if (process.env['ELECTRON_RENDERER_URL']) janela.loadURL(process.env['ELECTRON_RENDERER_URL'])
  else janela.loadFile(join(__dirname, '../renderer/index.html'))

  const captura = process.env['ATTO_CAPTURA'] // autoteste visual (desenvolvimento)
  if (dev && captura) {
    janela.webContents.once('did-finish-load', () =>
      setTimeout(async () => {
        writeFileSync(captura, (await janela!.webContents.capturePage()).toPNG())
        app.quit()
      }, 2500)
    )
  }
})
app.on('window-all-closed', () => app.quit())
