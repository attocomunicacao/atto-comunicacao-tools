// Servidor de release falso + controle da janela do launcher por CDP.
import { spawn, spawnSync } from 'node:child_process'
import { createHash } from 'node:crypto'
import { createServer } from 'node:http'
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const [, , appDir, saida] = process.argv
const esperar = (ms) => new Promise((r) => setTimeout(r, ms))
const log = (...a) => console.log(new Date().toISOString().slice(11, 19), ...a)
const tmp = mkdtempSync(join(tmpdir(), 'atto-rel-'))
const tar = join(process.env.SystemRoot, 'System32', 'tar.exe')

function zipDe(versao) {
  const src = join(tmp, 's' + versao); mkdirSync(src, { recursive: true })
  writeFileSync(join(src, 'ATTO Tools.exe'), 'x'.repeat(2_000_000) + versao)
  const z = join(tmp, versao + '.zip'); spawnSync(tar, ['-a', '-cf', z, '-C', src, '.'])
  return readFileSync(z)
}
let versaoServida = '1.0.0'
const zips = { '1.0.0': zipDe('1.0.0'), '1.1.0': zipDe('1.1.0') }
let base
const srv = createServer((q, s) => {
  if (q.url === '/manifest.json') {
    const b = zips[versaoServida]
    return s.writeHead(200, { 'content-type': 'application/json' }).end(JSON.stringify({
      versao: versaoServida, notas: `Novidades da ${versaoServida}: legenda mais rápida.`, executavel: 'ATTO Tools.exe',
      arquivo: { nome: versaoServida + '.zip', url: `${base}/dl/${versaoServida}.zip`, sha256: createHash('sha256').update(b).digest('hex'), tamanho: b.length }
    }))
  }
  const m = q.url.match(/^\/dl\/(.+)\.zip$/)
  if (m && zips[m[1]]) { const b = zips[m[1]]; return setTimeout(() => s.writeHead(200, { 'content-length': b.length }).end(b), 600) }
  s.writeHead(404).end()
})
await new Promise((r) => srv.listen(0, '127.0.0.1', r))
base = `http://127.0.0.1:${srv.address().port}`
const raiz = join(tmp, 'raiz')

async function abrirApp(porta) {
  const env = { ...process.env, ATTO_MANIFEST_URL: base + '/manifest.json', ATTO_PREFIXO: base + '/dl/', ATTO_RAIZ: raiz }
  const proc = spawn('npx', ['electron', '.', '--disable-gpu', `--remote-debugging-port=${porta}`], { cwd: appDir, shell: true, stdio: 'ignore', env })
  let alvo
  for (let i = 0; i < 60 && !alvo; i++) {
    await esperar(1000)
    try { alvo = (await (await fetch(`http://127.0.0.1:${porta}/json`)).json()).find((a) => a.type === 'page') } catch {}
  }
  if (!alvo) throw new Error('janela não abriu')
  const ws = new WebSocket(alvo.webSocketDebuggerUrl); await new Promise((r) => (ws.onopen = r))
  let id = 0; const pend = new Map()
  ws.onmessage = (m) => { const d = JSON.parse(m.data); pend.get(d.id)?.(d); pend.delete(d.id) }
  const cdp = (method, params = {}) => new Promise((r) => { const n = ++id; pend.set(n, r); ws.send(JSON.stringify({ id: n, method, params })) })
  const ev = async (e) => (await cdp('Runtime.evaluate', { expression: e, returnByValue: true, awaitPromise: true })).result?.result?.value
  const texto = () => ev('document.body.innerText')
  const foto = async (n) => writeFileSync(`${saida}/${n}.png`, Buffer.from((await cdp('Page.captureScreenshot', { format: 'png' })).result.data, 'base64'))
  const ate = async (frag, s = 30) => { for (let i = 0; i < s * 2; i++) { const t = await texto(); if (t.toLowerCase().includes(frag.toLowerCase())) return t; await esperar(500) } await foto('timeout'); throw new Error('timeout: ' + frag + ' | ' + (await texto()).replace(/\n/g, ' / ')) }
  const clicar = (r) => ev(`(()=>{const b=[...document.querySelectorAll('button')].find(x=>x.innerText.trim().startsWith(${JSON.stringify(r)})&&!x.disabled);if(b){b.click();return true}return false})()`)
  const fechar = () => { ws.close(); proc.kill(); spawn('taskkill', ['/F', '/IM', 'electron.exe', '/T'], { stdio: 'ignore' }) }
  return { ate, clicar, foto, texto, fechar }
}

try {
  let a = await abrirApp(9444)
  await a.ate('Baixar e instalar'); await a.foto('1-primeira-instalacao'); log('1 primeira instalação mostrada')
  await a.clicar('Baixar e instalar'); await esperar(300); await a.foto('2-baixando')
  await a.ate('Tudo em dia'); await a.foto('3-em-dia'); log('2 instalou 1.0.0 ->', JSON.parse(readFileSync(join(raiz, 'estado.json'), 'utf-8')))
  a.fechar(); await esperar(2500)

  versaoServida = '1.1.0'
  a = await abrirApp(9445)
  await a.ate('Atualização disponível'); await a.foto('4-atualizacao'); log('3 atualização 1.1.0 detectada')
  await a.clicar('Atualizar'); await a.ate('Tudo em dia')
  log('4 atualizou ->', JSON.parse(readFileSync(join(raiz, 'estado.json'), 'utf-8')), 'pastas:', existsSync(join(raiz, 'versions', '1.0.0')), existsSync(join(raiz, 'versions', '1.1.0')))
  await a.ate('Voltar para a versão anterior'); await a.foto('5-com-anterior')
  await a.clicar('Voltar para a versão anterior'); await esperar(1500)
  log('5 voltou ->', JSON.parse(readFileSync(join(raiz, 'estado.json'), 'utf-8')), '| tela:', (await a.texto()).replace(/\n/g, ' / '))
  a.fechar(); await esperar(2000)

  srv.close(); base = 'http://127.0.0.1:1' // servidor fora do ar
  a = await abrirApp(9446)
  await a.ate('Sem conexão'); await a.foto('6-sem-conexao'); log('6 sem conexão, ainda mostra Abrir:', (await a.texto()).includes("Abrir"))
  a.fechar()
  log('SUCESSO')
} catch (e) { log('FALHOU:', e.message); process.exitCode = 1 }
spawn('taskkill', ['/F', '/IM', 'electron.exe', '/T'], { stdio: 'ignore' })
srv.close(); rmSync(tmp, { recursive: true, force: true })
