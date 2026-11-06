import { spawn } from 'node:child_process'
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { basename, join, resolve, sep } from 'node:path'
import { app, BrowserWindow, dialog, ipcMain, shell } from 'electron'

const COMANDOS = new Set(['transcrever', 'estruturar', 'exportar', 'dicionario'])
let janela: BrowserWindow | null = null

const pastaProjetos = () => join(app.getPath('userData'), 'projetos')
const pastaMotor = () => resolve(app.getAppPath(), '..', 'engine') // desenvolvimento; o instalador embarcará o motor

/** Só aceita caminhos dentro da pasta de projetos. */
function dentroDosProjetos(caminho: string): string {
  const p = resolve(caminho)
  if (!p.startsWith(pastaProjetos() + sep)) throw new Error('Caminho fora da pasta de projetos')
  return p
}

function criarJanela(): void {
  janela = new BrowserWindow({
    width: 1280,
    height: 820,
    minWidth: 1000,
    minHeight: 680,
    backgroundColor: '#0e1014',
    title: 'ATTO Tools',
    autoHideMenuBar: true,
    webPreferences: { preload: join(__dirname, '../preload/index.js'), contextIsolation: true, sandbox: true }
  })
  if (process.env['ELECTRON_RENDERER_URL']) janela.loadURL(process.env['ELECTRON_RENDERER_URL'])
  else janela.loadFile(join(__dirname, '../renderer/index.html'))

  // Autoteste: ATTO_CAPTURA=<arquivo.png> salva uma imagem da janela e fecha o app.
  const captura = process.env['ATTO_CAPTURA']
  if (captura) {
    janela.webContents.once('did-finish-load', () =>
      setTimeout(async () => {
        const img = await janela!.webContents.capturePage()
        writeFileSync(captura, img.toPNG())
        app.quit()
      }, 1500)
    )
  }
}

function executarMotor(args: string[], aoLinha: (linha: string) => void): Promise<{ codigo: number; erro: string }> {
  return new Promise((ok) => {
    const proc = spawn('uv', ['run', '--project', pastaMotor(), 'garimpo', ...args], {
      env: { ...process.env, PYTHONIOENCODING: 'utf-8' },
      windowsHide: true
    })
    let resto = ''
    let erro = ''
    proc.stdout.on('data', (d: Buffer) => {
      resto += d.toString('utf-8')
      const linhas = resto.split(/\r?\n/)
      resto = linhas.pop() ?? ''
      linhas.forEach((l) => l.trim() && aoLinha(l))
    })
    proc.stderr.on('data', (d: Buffer) => (erro = (erro + d.toString('utf-8')).slice(-1500)))
    proc.on('error', (e) => ok({ codigo: -1, erro: `Não foi possível iniciar o motor (uv): ${e.message}` }))
    proc.on('close', (c) => ok({ codigo: c ?? -1, erro }))
  })
}

app.whenReady().then(() => {
  mkdirSync(pastaProjetos(), { recursive: true })

  ipcMain.handle('video:escolher', async () => {
    if (process.env['ATTO_VIDEO_TESTE']) return process.env['ATTO_VIDEO_TESTE'] // autoteste, sem diálogo
    const r = await dialog.showOpenDialog({
      title: 'Escolha o vídeo',
      properties: ['openFile'],
      filters: [{ name: 'Vídeo', extensions: ['mp4', 'mov', 'mts', 'm2ts', 'mkv', 'avi', 'mxf', 'wmv'] }]
    })
    return r.canceled ? null : r.filePaths[0]
  })

  ipcMain.handle('projeto:criar', (_e, video: string) => {
    const nome = basename(video).replace(/\.[^.]+$/, '').replace(/[^\w-]+/g, '_').slice(0, 40)
    const pasta = join(pastaProjetos(), `${nome}-${Date.now()}`)
    mkdirSync(pasta, { recursive: true })
    return pasta
  })

  ipcMain.handle('motor:executar', async (_e, cmd: string, args: string[]) => {
    if (!COMANDOS.has(cmd) || !args.every((a) => typeof a === 'string')) throw new Error('Comando inválido')
    const pastaIdx = args.indexOf('--pasta')
    if (pastaIdx >= 0) dentroDosProjetos(args[pastaIdx + 1])
    return executarMotor([cmd, ...args], (linha) => janela?.webContents.send('motor:linha', linha))
  })

  ipcMain.handle('arquivo:json', (_e, pasta: string, nome: string) =>
    JSON.parse(readFileSync(join(dentroDosProjetos(pasta), basename(nome)), 'utf-8'))
  )
  ipcMain.handle('arquivo:bytes', (_e, pasta: string, sub: string, nome: string) =>
    readFileSync(join(dentroDosProjetos(pasta), basename(sub), basename(nome)))
  )
  ipcMain.handle('pasta:mostrar', (_e, caminho: string) => {
    shell.showItemInFolder(dentroDosProjetos(caminho))
  })

  criarJanela()
  app.on('activate', () => BrowserWindow.getAllWindows().length === 0 && criarJanela())
})

app.on('window-all-closed', () => process.platform !== 'darwin' && app.quit())
