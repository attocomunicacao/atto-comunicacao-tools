// Launcher (modo desenvolvimento) contra a release REAL do GitHub, instalando em uma pasta temporária.
import { spawn, spawnSync } from 'node:child_process'
import { existsSync, mkdtempSync, readFileSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const [, , appDir, saida] = process.argv
const esperar = (ms) => new Promise((r) => setTimeout(r, ms))
const log = (...a) => console.log(new Date().toISOString().slice(11, 19), ...a)
const raiz = mkdtempSync(join(tmpdir(), 'atto-real-'))
const env = { ...process.env, ATTO_RAIZ: raiz }
delete env.ATTO_MANIFEST_URL; delete env.ATTO_PREFIXO // usa os endereços oficiais

const proc = spawn('npx', ['electron', '.', '--disable-gpu', '--remote-debugging-port=9555'], { cwd: appDir, shell: true, stdio: 'ignore', env })
let alvo
for (let i = 0; i < 60 && !alvo; i++) {
  await esperar(1000)
  try { alvo = (await (await fetch('http://127.0.0.1:9555/json')).json()).find((a) => a.type === 'page') } catch {}
}
const ws = new WebSocket(alvo.webSocketDebuggerUrl); await new Promise((r) => (ws.onopen = r))
let id = 0; const pend = new Map()
ws.onmessage = (m) => { const d = JSON.parse(m.data); pend.get(d.id)?.(d); pend.delete(d.id) }
const cdp = (method, params = {}) => new Promise((r) => { const n = ++id; pend.set(n, r); ws.send(JSON.stringify({ id: n, method, params })) })
const ev = async (e) => (await cdp('Runtime.evaluate', { expression: e, returnByValue: true, awaitPromise: true })).result?.result?.value
const texto = () => ev('document.body.innerText')
const foto = async (n) => writeFileSync(`${saida}/${n}.png`, Buffer.from((await cdp('Page.captureScreenshot', { format: 'png' })).result.data, 'base64'))
const ate = async (frag, s = 30) => { for (let i = 0; i < s * 2; i++) { const t = await texto(); if (t.toLowerCase().includes(frag.toLowerCase())) return t; await esperar(500) } await foto('timeout'); throw new Error('timeout: ' + frag + ' | ' + (await texto()).replace(/\n/g, ' / ')) }
const clicar = async (r) => {
  const pos = await ev(`(()=>{const b=[...document.querySelectorAll('button')].find(x=>x.innerText.trim().startsWith(${JSON.stringify(r)})&&!x.disabled);if(!b)return null;const q=b.getBoundingClientRect();return {x:q.x+q.width/2,y:q.y+q.height/2}})()`)
  if (!pos) return false
  for (const type of ['mousePressed', 'mouseReleased']) await cdp('Input.dispatchMouseEvent', { type, x: pos.x, y: pos.y, button: 'left', clickCount: 1 })
  return true
}

try {
  await cdp('Runtime.enable'); await cdp('Page.enable')
  await ate('Baixar e instalar', 40); await foto('1-release-real'); log('1 launcher viu a release:', (await texto()).replace(/\n/g, ' / '))
  const t0 = Date.now()
  await clicar('Baixar e instalar')
  await ate('Tudo em dia', 600); await foto('2-instalado')
  log(`2 baixou e instalou em ${((Date.now() - t0) / 1000).toFixed(0)} s, estado:`, JSON.parse(readFileSync(join(raiz, 'estado.json'), 'utf-8')))
  log('   executável instalado:', existsSync(join(raiz, 'versions', '0.1.0', 'ATTO Tools.exe')))
  await clicar('Abrir'); await esperar(7000)
  const lista = spawnSync('tasklist', ['/FI', 'IMAGENAME eq ATTO Tools.exe'], { encoding: 'utf-8' }).stdout
  log('3 app instalado aberto:', /ATTO Tools\.exe/.test(lista))
  log('SUCESSO')
} catch (e) { log('FALHOU:', e.message); process.exitCode = 1 }
ws.close(); proc.kill()
spawnSync('taskkill', ['/F', '/IM', 'ATTO Tools.exe', '/T']); spawnSync('taskkill', ['/F', '/IM', 'electron.exe', '/T'])
console.log('raiz de teste:', raiz)
