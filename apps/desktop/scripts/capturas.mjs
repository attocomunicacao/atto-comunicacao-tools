// Gera as capturas de tela do README com dados fictícios (apps/desktop/scripts/demo/mock-atto.js).
// Uso: node apps/desktop/scripts/capturas.mjs <pasta-de-saida>
import { spawn, spawnSync } from 'node:child_process'
import { readFileSync, writeFileSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import react from '@vitejs/plugin-react'
import { createServer } from 'vite'

const aqui = dirname(fileURLToPath(import.meta.url))
const desktop = resolve(aqui, '..')
const saida = resolve(process.argv[2] ?? join(desktop, '..', '..', 'docs/assets/screenshots'))
const esperar = (ms) => new Promise((r) => setTimeout(r, ms))
const mock = readFileSync(join(aqui, 'demo/mock-atto.js'), 'utf-8')

const servidor = await createServer({
  root: join(desktop, 'src/renderer'), logLevel: 'error', server: { port: 5199, strictPort: true },
  plugins: [react(), { name: 'mock-atto', transformIndexHtml: () => [{ tag: 'script', children: mock, injectTo: 'head-prepend' }] }]
})
await servidor.listen()

const electron = join(desktop, '../../node_modules/electron/dist/electron.exe')
const proc = spawn(electron, [join(aqui, 'demo/janela.cjs'), '--disable-gpu', '--remote-debugging-port=9666'], {
  stdio: 'ignore', env: { ...process.env, DEMO_URL: 'http://localhost:5199' }
})
let alvo
for (let i = 0; i < 40 && !alvo; i++) {
  await esperar(1000)
  try { alvo = (await (await fetch('http://127.0.0.1:9666/json')).json()).find((a) => a.type === 'page') } catch {}
}
const ws = new WebSocket(alvo.webSocketDebuggerUrl); await new Promise((r) => (ws.onopen = r))
let id = 0; const pend = new Map()
ws.onmessage = (m) => { const d = JSON.parse(m.data); pend.get(d.id)?.(d); pend.delete(d.id) }
const cdp = (method, params = {}) => new Promise((r) => { const n = ++id; pend.set(n, r); ws.send(JSON.stringify({ id: n, method, params })) })
const ev = async (e) => (await cdp('Runtime.evaluate', { expression: e, returnByValue: true, awaitPromise: true })).result?.result?.value
const foto = async (nome) => { await esperar(900); writeFileSync(join(saida, nome), Buffer.from((await cdp('Page.captureScreenshot', { format: 'png' })).result.data, 'base64')) }
const clicar = (r) => ev(`(()=>{const b=[...document.querySelectorAll('button')].find(x=>x.innerText.trim().startsWith(${JSON.stringify(r)})&&!x.disabled);if(b){b.click();return true}return false})()`)
const ate = async (frag) => { for (let i = 0; i < 40; i++) { if ((await ev('document.body.innerText')).toLowerCase().includes(frag.toLowerCase())) return; await esperar(250) } throw new Error('timeout: ' + frag) }

try {
  await cdp('Runtime.enable'); await cdp('Page.enable')
  await cdp('Emulation.setDeviceMetricsOverride', { width: 1280, height: 820, deviceScaleFactor: 1, mobile: false })
  await ate('Escolher vídeo'); await foto('01-garimpo-inicio.png')
  await clicar('Escolher vídeo'); await ate('Trocar vídeo'); await clicar('Começar')
  await ate('Dúvidas de escrita'); await foto('02-duvidas.png')
  await clicar('Continuar'); await ate('cortes sugeridos'); await esperar(600)
  await ev('document.querySelectorAll(".item input[type=checkbox]").forEach((c,i)=>{ if(i<2) c.click() })')
  await foto('03-cortes.png')
  await clicar('Gerar'); await ate('Pronto'); await foto('04-pronto.png')
  await clicar('Meu dicionário'); await ate('Termos que o Garimpo conhece'); await foto('08-dicionario.png')
  console.log('Capturas geradas em', saida)
} finally {
  ws.close(); proc.kill(); spawnSync('taskkill', ['/F', '/IM', 'electron.exe', '/T'], { stdio: 'ignore' }); await servidor.close()
}
