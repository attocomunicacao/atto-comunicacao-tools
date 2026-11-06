/**
 * Lógica do launcher: consulta a release, baixa, confere o SHA-256, instala lado a lado e permite voltar.
 * Só usa módulos do Node, para ser testada sem o Electron.
 *
 * Estrutura em disco (raiz = %LOCALAPPDATA%\ATTO Tools):
 *   versions\<versao>\...   cada versão em sua pasta
 *   estado.json             { atual, anterior }
 */
import { spawn, spawnSync } from 'node:child_process'
import { createHash } from 'node:crypto'
import { createReadStream, createWriteStream, existsSync, mkdirSync, readdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { Readable } from 'node:stream'
import { pipeline } from 'node:stream/promises'

export interface Manifest {
  versao: string
  publicadoEm?: string
  notas?: string
  executavel: string
  arquivo: { nome: string; url: string; sha256: string; tamanho: number }
}

export interface Estado {
  atual: string | null
  anterior: string | null
}

export const VERSAO_VALIDA = /^\d+\.\d+\.\d+$/

export function compararVersoes(a: string, b: string): number {
  const pa = a.split('.').map(Number)
  const pb = b.split('.').map(Number)
  for (let i = 0; i < 3; i++) if (pa[i] !== pb[i]) return pa[i] < pb[i] ? -1 : 1
  return 0
}

export function lerEstado(raiz: string): Estado {
  try {
    const e = JSON.parse(readFileSync(join(raiz, 'estado.json'), 'utf-8'))
    return { atual: e.atual ?? null, anterior: e.anterior ?? null }
  } catch {
    return { atual: null, anterior: null }
  }
}

function salvarEstado(raiz: string, e: Estado): void {
  mkdirSync(raiz, { recursive: true })
  writeFileSync(join(raiz, 'estado.json'), JSON.stringify(e, null, 2), 'utf-8')
}

export async function buscarManifest(url: string): Promise<Manifest> {
  const r = await fetch(url, { redirect: 'follow', signal: AbortSignal.timeout(15000) })
  if (!r.ok) throw new Error(`Não foi possível consultar a atualização (HTTP ${r.status}).`)
  const m = (await r.json()) as Manifest
  if (!VERSAO_VALIDA.test(m.versao) || !m.arquivo?.url || !m.arquivo?.sha256 || !m.executavel)
    throw new Error('O manifest da release está incompleto.')
  if (m.executavel.includes('..') || m.executavel.startsWith('/') || /^[a-zA-Z]:/.test(m.executavel))
    throw new Error('Caminho do executável inválido no manifest.')
  return m
}

export async function sha256(arquivo: string): Promise<string> {
  const h = createHash('sha256')
  await pipeline(createReadStream(arquivo), h)
  return h.digest('hex')
}

async function baixar(url: string, destino: string, aoProgresso: (pct: number) => void): Promise<void> {
  const r = await fetch(url, { redirect: 'follow' })
  if (!r.ok || !r.body) throw new Error(`Falha ao baixar (HTTP ${r.status}).`)
  const total = Number(r.headers.get('content-length') ?? 0)
  let lido = 0
  const origem = Readable.fromWeb(r.body as never)
  origem.on('data', (c: Buffer) => {
    lido += c.length
    if (total) aoProgresso(Math.min(99, (lido / total) * 100))
  })
  await pipeline(origem, createWriteStream(destino))
}

/** tar.exe do Windows (bsdtar, entende .zip). Evita um `tar` GNU que esteja antes no PATH (ex.: Git Bash). */
export function tarDoWindows(): string {
  const sys = join(process.env['SystemRoot'] ?? 'C:\\Windows', 'System32', 'tar.exe')
  return existsSync(sys) ? sys : 'tar'
}

function extrair(zip: string, destino: string): void {
  mkdirSync(destino, { recursive: true })
  const r = spawnSync(tarDoWindows(), ['-xf', zip, '-C', destino], { windowsHide: true })
  if (r.status !== 0) throw new Error('Não foi possível extrair o pacote: ' + String(r.stderr).slice(0, 300))
}

export interface OpcoesInstalar {
  raiz: string
  manifest: Manifest
  prefixoPermitido: string // a URL do pacote precisa começar com isto
  aoProgresso: (pct: number, etapa: string) => void
}

/** Baixa, confere e instala a versão ao lado das outras. Só troca a "atual" depois de tudo certo. */
export async function instalar({ raiz, manifest, prefixoPermitido, aoProgresso }: OpcoesInstalar): Promise<Estado> {
  if (!manifest.arquivo.url.startsWith(prefixoPermitido)) throw new Error('O pacote aponta para um endereço não permitido.')
  const pasta = join(raiz, 'versions', manifest.versao)
  const temp = join(raiz, 'temp')
  mkdirSync(temp, { recursive: true })
  const zip = join(temp, `${manifest.versao}.zip`)
  try {
    aoProgresso(0, 'Baixando')
    await baixar(manifest.arquivo.url, zip, (p) => aoProgresso(p * 0.8, 'Baixando'))
    aoProgresso(80, 'Conferindo integridade')
    if ((await sha256(zip)) !== manifest.arquivo.sha256.toLowerCase())
      throw new Error('O arquivo baixado está corrompido (SHA-256 não confere). Nada foi instalado.')
    aoProgresso(88, 'Instalando')
    rmSync(pasta, { recursive: true, force: true })
    extrair(zip, pasta)
    if (!existsSync(join(pasta, manifest.executavel))) throw new Error('O pacote não contém o executável esperado.')
  } catch (e) {
    rmSync(pasta, { recursive: true, force: true })
    throw e
  } finally {
    rmSync(zip, { force: true })
  }
  const antes = lerEstado(raiz)
  const novo: Estado = { atual: manifest.versao, anterior: antes.atual && antes.atual !== manifest.versao ? antes.atual : antes.anterior }
  salvarEstado(raiz, novo)
  limpar(raiz, novo)
  aoProgresso(100, 'Pronto')
  return novo
}

/** Remove versões que não são a atual nem a anterior. */
export function limpar(raiz: string, e: Estado): void {
  const dir = join(raiz, 'versions')
  if (!existsSync(dir)) return
  for (const v of readdirSync(dir)) if (v !== e.atual && v !== e.anterior) rmSync(join(dir, v), { recursive: true, force: true })
}

export function reverter(raiz: string): Estado {
  const e = lerEstado(raiz)
  if (!e.anterior || !existsSync(join(raiz, 'versions', e.anterior))) throw new Error('Não há versão anterior instalada.')
  const novo = { atual: e.anterior, anterior: e.atual }
  salvarEstado(raiz, novo)
  return novo
}

export function abrir(raiz: string, executavel: string): void {
  const e = lerEstado(raiz)
  if (!e.atual) throw new Error('O ATTO Tools ainda não está instalado.')
  const exe = join(raiz, 'versions', e.atual, executavel)
  if (!existsSync(exe)) throw new Error('Executável não encontrado. Reinstale o ATTO Tools.')
  spawn(exe, [], { detached: true, stdio: 'ignore', cwd: join(raiz, 'versions', e.atual) }).unref()
}
