// Dirige o app Electron por CDP e percorre o fluxo completo do Garimpo.
import { spawn } from 'node:child_process'
import { writeFileSync } from 'node:fs'

// Uso: e2e.mjs <apps/desktop> <pasta-de-capturas> [ATTO Tools.exe]
// Com o 3º argumento testa o app EMPACOTADO em um ambiente limpo (sem uv, Python, FFmpeg nem variáveis do desenvolvedor).
const [, , appDir, saida, exe] = process.argv
const PORTA = 9333
const envLimpo = exe
  ? { SystemRoot: process.env.SystemRoot, PATH: `${process.env.SystemRoot}\\System32`, TEMP: process.env.TEMP, LOCALAPPDATA: process.env.LOCALAPPDATA,
      USERPROFILE: process.env.USERPROFILE, APPDATA: process.env.ATTO_APPDATA_TESTE ?? process.env.APPDATA, ATTO_VIDEO_TESTE: process.env.ATTO_VIDEO_TESTE }
  : process.env
const esperar = (ms) => new Promise((r) => setTimeout(r, ms))
const log = (...a) => console.log(new Date().toISOString().slice(11, 19), ...a)

const proc = exe
  ? spawn(exe, ['--disable-gpu', `--remote-debugging-port=${PORTA}`], { stdio: 'ignore', env: envLimpo })
  : spawn('npx', ['electron', '.', '--disable-gpu', `--remote-debugging-port=${PORTA}`], { cwd: appDir, shell: true, stdio: 'ignore', env: envLimpo })

let alvo
for (let i = 0; i < 60 && !alvo; i++) {
  await esperar(1000)
  try {
    const abas = await (await fetch(`http://127.0.0.1:${PORTA}/json`)).json()
    alvo = abas.find((a) => a.type === 'page')
  } catch {}
}
if (!alvo) { log('FALHA: app não abriu'); proc.kill(); process.exit(1) }

const ws = new WebSocket(alvo.webSocketDebuggerUrl)
await new Promise((r) => (ws.onopen = r))
let id = 0
const pend = new Map()
ws.onmessage = (m) => { const d = JSON.parse(m.data); pend.get(d.id)?.(d); pend.delete(d.id) }
const cdp = (method, params = {}) => new Promise((r) => { const n = ++id; pend.set(n, r); ws.send(JSON.stringify({ id: n, method, params })) })
const ev = async (expr) => (await cdp('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true })).result?.result?.value
const foto = async (nome) => { const r = await cdp('Page.captureScreenshot', { format: 'png' }); writeFileSync(`${saida}/${nome}.png`, Buffer.from(r.result.data, 'base64')) }
const texto = () => ev('document.body.innerText')
const clicar = (rotulo) => ev(`(()=>{const b=[...document.querySelectorAll('button')].find(x=>x.innerText.trim().startsWith(${JSON.stringify(rotulo)})&&!x.disabled);if(b){b.click();return true}return false})()`)
async function ate(frag, limiteS, passo = 3000) {
  const t0 = Date.now()
  while (Date.now() - t0 < limiteS * 1000) {
    const t = await texto()
    if (t.includes(frag)) return t
    if (/não foi possível|terminou com erro|Traceback|Error/i.test(t) && !t.includes(frag)) { log('ERRO NA TELA:', t.slice(-600)); await foto('erro'); throw new Error('erro na tela') }
    await esperar(passo)
  }
  await foto('timeout'); throw new Error('timeout esperando: ' + frag)
}

try {
  await cdp('Runtime.enable'); await cdp('Page.enable')
  log('1 clicar Escolher vídeo:', await clicar('Escolher vídeo'))
  await ate('Trocar vídeo', 20); await foto('1-video-escolhido')
  log('2 clicar Começar:', await clicar('Começar'))
  await ate('Transcrevendo', 30); await foto('2-transcrevendo')
  await ate('Dúvidas de escrita', 900, 5000); await foto('3-duvidas'); log('dúvidas apareceram')
  log('3 clicar Continuar:', await clicar('Continuar'))
  await ate('cortes sugeridos', 900, 5000)
  await esperar(2500) // prévias carregando
  await foto('4-cortes')
  log('prévias de áudio:', await ev('document.querySelectorAll("audio").length'), 'cortes na tela')
  await ev('document.querySelector(".item input[type=checkbox]").click()')
  log('4 clicar Gerar:', await clicar('Gerar'))
  await ate('Pronto', 600, 5000); await foto('5-pronto')
  log('arquivos:', await ev('[...document.querySelectorAll(".item h3")].map(x=>x.innerText).join(", ")'))
  log('SUCESSO')
} catch (e) { log('FALHOU:', e.message); process.exitCode = 1 }
ws.close(); proc.kill(); spawn('taskkill', ['/F', '/IM', 'electron.exe', '/T'], { stdio: 'ignore' })
