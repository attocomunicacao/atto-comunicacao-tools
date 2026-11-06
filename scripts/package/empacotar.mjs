// Empacota o ATTO Tools para Windows x64: app Electron + Python + dependências + FFmpeg + modelo Whisper + fontes.
// Uso: node scripts/package/empacotar.mjs [--versao 0.1.0] [--python <python.exe>] [--sem-zip]
// Saída: dist/ATTO-Tools-<versao>-win-x64.zip e dist/manifest.json (o launcher instala esse zip).
import { spawnSync } from 'node:child_process'
import { cpSync, existsSync, mkdirSync, readdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { homedir } from 'node:os'
import { basename, dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const raiz = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..')
const arg = (nome, padrao) => { const i = process.argv.indexOf(nome); return i >= 0 ? process.argv[i + 1] : padrao }
const versao = arg('--versao', JSON.parse(readFileSync(join(raiz, 'apps/desktop/package.json'), 'utf-8')).version)
const dist = join(raiz, 'dist')
const etapa = (t) => console.log(`\n== ${t}`)

function rodar(cmd, args, opcoes = {}) {
  const r = spawnSync(cmd, args, { stdio: 'inherit', shell: false, ...opcoes })
  if (r.status !== 0) throw new Error(`Falhou: ${cmd} ${args.join(' ')}`)
}
function saida(cmd, args) {
  const r = spawnSync(cmd, args, { encoding: 'utf-8' })
  if (r.status !== 0) throw new Error(`Falhou: ${cmd} ${args.join(' ')}\n${r.stderr}`)
  return r.stdout.trim()
}

if (!/^\d+\.\d+\.\d+$/.test(versao)) throw new Error('Versão inválida: use x.y.z')
const python = arg('--python', saida('uv', ['python', 'find', '3.12']))
const pythonHome = dirname(python)

etapa(`Versão ${versao}`)
rmSync(dist, { recursive: true, force: true })
mkdirSync(dist, { recursive: true })

etapa('1/6 Compilando o app')
rodar('npx', ['electron-vite', 'build'], { cwd: join(raiz, 'apps/desktop'), shell: true })

etapa('2/6 Empacotando o Electron')
const stage = join(dist, 'stage-app')
mkdirSync(stage, { recursive: true })
cpSync(join(raiz, 'apps/desktop/out'), join(stage, 'out'), { recursive: true })
writeFileSync(join(stage, 'package.json'), JSON.stringify({
  name: 'atto-tools', productName: 'ATTO Tools', version: versao, main: 'out/main/index.js',
  description: 'Suíte desktop da Atto Comunicação', author: 'Atto Comunicação'
}, null, 2))
const { packager } = await import(pathUrl(join(raiz, 'node_modules/@electron/packager/dist/index.js')))
const [pasta] = await packager({
  dir: stage, out: dist, name: 'ATTO Tools', executableName: 'ATTO Tools', platform: 'win32', arch: 'x64',
  electronVersion: JSON.parse(readFileSync(join(raiz, 'node_modules/electron/package.json'), 'utf-8')).version,
  asar: true, overwrite: true, appVersion: versao, quiet: true,
  win32metadata: { CompanyName: 'Atto Comunicação', ProductName: 'ATTO Tools', FileDescription: 'ATTO Tools' }
})
const res = join(pasta, 'resources')
function pathUrl(p) { return 'file:///' + p.replaceAll('\\', '/') }

etapa('3/6 Python embarcado')
const motor = join(res, 'engine')
const pyDestino = join(motor, 'python')
const IGNORAR = new Set(['site-packages', 'test', 'tests', 'idlelib', 'tkinter', 'turtledemo', '__pycache__', 'ensurepip', 'lib2to3'])
const filtro = (origem) => !origem.split(/[\\/]/).some((p) => IGNORAR.has(p) && origem !== pythonHome)
mkdirSync(pyDestino, { recursive: true })
for (const f of readdirSync(pythonHome)) {
  if (/^(python(w)?\.exe|python3\d*\.dll|vcruntime.*\.dll|LICENSE\.txt)$/i.test(f)) cpSync(join(pythonHome, f), join(pyDestino, f))
}
for (const d of ['DLLs', 'Lib']) cpSync(join(pythonHome, d), join(pyDestino, d), { recursive: true, filter: (o) => filtro(o.slice(pythonHome.length)) })

etapa('4/6 Dependências do motor (do uv.lock)')
const sp = join(motor, 'site-packages')
mkdirSync(sp, { recursive: true })
const req = join(dist, 'requirements.txt')
writeFileSync(req, saida('uv', ['export', '--project', join(raiz, 'apps/engine'), '--no-dev', '--no-hashes', '--no-emit-project', '--frozen']))
rodar('uv', ['pip', 'install', '--python', python, '--target', sp, '--no-deps', '-r', req])
cpSync(join(raiz, 'apps/engine/src/garimpo'), join(sp, 'garimpo'), { recursive: true, filter: (o) => !o.includes('__pycache__') })

etapa('5/6 FFmpeg, modelo Whisper e fontes')
const ffmpeg = saida('where', ['ffmpeg']).split(/\r?\n/)[0]
mkdirSync(join(res, 'bin'), { recursive: true })
for (const exe of ['ffmpeg.exe', 'ffprobe.exe']) cpSync(join(dirname(ffmpeg), exe), join(res, 'bin', exe))
const hf = join(homedir(), '.cache/huggingface/hub/models--Systran--faster-whisper-small/snapshots')
const snap = join(hf, readdirSync(hf)[0])
mkdirSync(join(res, 'models/small'), { recursive: true })
for (const f of readdirSync(snap)) cpSync(join(snap, f), join(res, 'models/small', f), { dereference: true })
const fontes = join(process.env.LOCALAPPDATA, 'Microsoft/Windows/Fonts')
mkdirSync(join(res, 'fonts'), { recursive: true })
for (const f of ['Lato-Regular.ttf', 'Lato-Bold.ttf', 'Lato-Black.ttf']) cpSync(join(fontes, f), join(res, 'fonts', f))
cpSync(join(raiz, 'THIRD_PARTY_NOTICES.md'), join(pasta, 'THIRD_PARTY_NOTICES.md'))
cpSync(join(raiz, 'LICENSE'), join(pasta, 'LICENSE-ATTO.txt'))

if (process.argv.includes('--sem-zip')) { console.log('\nPasta pronta:', pasta); process.exit(0) }

etapa('6/6 Compactando e gerando o manifest')
const zip = join(dist, `ATTO-Tools-${versao}-win-x64.zip`)
const tar = join(process.env.SystemRoot ?? 'C:\\Windows', 'System32', 'tar.exe')
rodar(tar, ['-a', '-cf', zip, '-C', pasta, '.'])
rodar('node', [join(raiz, 'scripts/release/gerar-manifest.mjs'), zip, versao, `ATTO Tools ${versao}`, join(dist, 'manifest.json')])
console.log(`\nPronto: ${zip}`)
console.log(`Pasta descompactada: ${pasta} (${basename(pasta)})`)
