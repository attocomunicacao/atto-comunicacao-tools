/**
 * Renderizador da camada de motion (modo sem janela): `ATTO Tools.exe --render-motion <job.json>`.
 *
 * Abre motion.html fora da tela (offscreen, fundo transparente, 1080x1920, escala 1), monta a timeline GSAP com os
 * dados do corte e, para cada quadro, faz `__seek(t)` e captura a imagem (BGRA). Os quadros vão direto para o FFmpeg,
 * que os sobrepõe ao vídeo-base do corte (já reenquadrado, com zooms e áudio tratado).
 * O motor Python chama este modo e lê o progresso (`PCT n`) pela saída padrão.
 */
import { spawn } from 'node:child_process'
import { readFileSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { app, BrowserWindow, type NativeImage } from 'electron'

interface Job {
  base: string
  saida: string
  fps: number
  duracao: number
  largura: number
  altura: number
  [k: string]: unknown
}

export function modoRender(): string | null {
  const i = process.argv.indexOf('--render-motion')
  return i >= 0 ? process.argv[i + 1] : null
}

export function prepararModoRender(): void {
  app.commandLine.appendSwitch('force-device-scale-factor', '1')
  app.commandLine.appendSwitch('disable-renderer-backgrounding')
  app.disableHardwareAcceleration() // offscreen em software: igual em qualquer máquina
  app.commandLine.appendSwitch('enable-unsafe-swiftshader') // WebGL em software (efeito 3D das imagens)
}

const out = (s: string) => process.stdout.write(s + '\n')

export async function renderizar(caminhoJob: string): Promise<void> {
  const job = JSON.parse(readFileSync(caminhoJob, 'utf-8')) as Job
  const { largura: W, altura: H, fps } = job
  const total = Math.max(1, Math.round(job.duracao * fps))
  const win = new BrowserWindow({
    width: W, height: H, show: false, frame: false, transparent: true, enableLargerThanScreen: true, backgroundColor: '#00000000', useContentSize: true,
    webPreferences: { offscreen: true, sandbox: true, contextIsolation: true, backgroundThrottling: false }
  })
  win.setContentSize(W, H)
  win.webContents.setFrameRate(240)
  const url = process.env['ELECTRON_RENDERER_URL']
  if (url) await win.loadURL(`${url}/motion.html`)
  else await win.loadFile(join(__dirname, '../renderer/motion.html'))
  await win.webContents.executeJavaScript(`window.__montar(${JSON.stringify(job)})`)

  // FFmpeg: vídeo-base + quadros BGRA pela entrada padrão -> corte final
  const ff = spawn('ffmpeg', [
    '-v', 'error', '-y', '-i', job.base,
    '-f', 'rawvideo', '-pix_fmt', 'bgra', '-s', `${W}x${H}`, '-framerate', String(fps), '-i', 'pipe:0',
    '-filter_complex', '[0:v][1:v]overlay=0:0:eof_action=pass:format=auto,format=yuv420p[v]',
    '-map', '[v]', '-map', '0:a?', '-c:v', 'libx264', '-preset', 'faster', '-crf', '16', '-c:a', 'copy',
    '-movflags', '+faststart', job.saida
  ], { stdio: ['pipe', 'ignore', 'pipe'], windowsHide: true })
  let erro = ''
  ff.stderr.on('data', (d: Buffer) => (erro = (erro + d.toString()).slice(-2000)))
  const fim = new Promise<number>((ok) => ff.on('close', (c) => ok(c ?? -1)))

  let falhaPipe: Error | null = null
  ff.stdin.on('error', (e) => (falhaPipe = e))
  const escrever = (buf: Buffer) => new Promise<void>((ok, falha) => {
    if (falhaPipe) return falha(falhaPipe)
    if (ff.stdin.write(buf)) ok()
    else ff.stdin.once('drain', ok)
  })

  let ultimoPct = -1
  for (let f = 0; f < total; f++) {
    await win.webContents.executeJavaScript(`window.__seek(${(f / fps).toFixed(5)})`)
    const img: NativeImage = await win.webContents.capturePage({ x: 0, y: 0, width: W, height: H })
    if (job['depurar'] && f === Math.round(Number(job['depurarEm'] ?? 1) * fps)) writeFileSync(String(job['depurar']), img.toPNG())
    let bmp = img.toBitmap()
    if (bmp.length !== W * H * 4) bmp = img.resize({ width: W, height: H }).toBitmap()
    await escrever(bmp)
    const pct = Math.floor((f / total) * 100)
    if (pct !== ultimoPct) { ultimoPct = pct; out(`PCT ${pct}`) }
  }
  ff.stdin.end()
  const codigo = await fim
  win.destroy()
  if (codigo !== 0) {
    out(`ERRO ffmpeg ${codigo}: ${erro}`)
    process.exitCode = 1
  } else out('PRONTO')
}
