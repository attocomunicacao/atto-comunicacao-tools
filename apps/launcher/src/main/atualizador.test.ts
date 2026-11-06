import assert from 'node:assert/strict'
import { spawnSync } from 'node:child_process'
import { createHash } from 'node:crypto'
import { existsSync, mkdirSync, mkdtempSync, readFileSync, writeFileSync } from 'node:fs'
import { createServer } from 'node:http'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { after, before, test } from 'node:test'
import { compararVersoes, instalar, lerEstado, reverter, tarDoWindows, type Manifest } from './atualizador.ts'

let servidor: ReturnType<typeof createServer>
let base = ''
const zips = new Map<string, Buffer>()
const tmp = mkdtempSync(join(tmpdir(), 'atto-launcher-'))

function criarZip(versao: string): Buffer {
  const src = join(tmp, 'src-' + versao)
  mkdirSync(src, { recursive: true })
  writeFileSync(join(src, 'ATTO Tools.exe'), 'exe ' + versao)
  const zip = join(tmp, `${versao}.zip`)
  const r = spawnSync(tarDoWindows(), ['-a', '-cf', zip, '-C', src, '.'])
  assert.equal(r.status, 0, String(r.stderr))
  return readFileSync(zip)
}

const manifestDe = (versao: string, corromper = false): Manifest => {
  const buf = zips.get(versao)!
  return {
    versao,
    executavel: 'ATTO Tools.exe',
    arquivo: { nome: `${versao}.zip`, url: `${base}/${versao}.zip`, sha256: corromper ? 'a'.repeat(64) : createHash('sha256').update(buf).digest('hex'), tamanho: buf.length }
  }
}
const opts = (raiz: string, manifest: Manifest) => ({ raiz, manifest, prefixoPermitido: base, aoProgresso: () => {} })

before(async () => {
  for (const v of ['1.0.0', '1.1.0', '1.2.0']) zips.set(v, criarZip(v))
  servidor = createServer((q, s) => {
    const b = zips.get((q.url ?? '').slice(1).replace('.zip', ''))
    if (!b) return s.writeHead(404).end()
    s.writeHead(200, { 'content-length': b.length }).end(b)
  })
  await new Promise<void>((ok) => servidor.listen(0, '127.0.0.1', ok))
  base = `http://127.0.0.1:${(servidor.address() as { port: number }).port}`
})
after(() => servidor.close())

test('compara versões', () => {
  assert.equal(compararVersoes('1.2.0', '1.10.0'), -1)
  assert.equal(compararVersoes('2.0.0', '1.9.9'), 1)
  assert.equal(compararVersoes('1.0.0', '1.0.0'), 0)
})

test('instala, atualiza lado a lado e volta à versão anterior', async () => {
  const raiz = join(tmp, 'a')
  await instalar(opts(raiz, manifestDe('1.0.0')))
  assert.deepEqual(lerEstado(raiz), { atual: '1.0.0', anterior: null })
  await instalar(opts(raiz, manifestDe('1.1.0')))
  assert.deepEqual(lerEstado(raiz), { atual: '1.1.0', anterior: '1.0.0' })
  assert.ok(existsSync(join(raiz, 'versions', '1.0.0', 'ATTO Tools.exe')))
  assert.deepEqual(reverter(raiz), { atual: '1.0.0', anterior: '1.1.0' })
  await instalar(opts(raiz, manifestDe('1.2.0')))
  assert.ok(!existsSync(join(raiz, 'versions', '1.1.0')), 'versões antigas são removidas')
})

test('SHA-256 errado não instala nada e mantém a versão atual', async () => {
  const raiz = join(tmp, 'b')
  await instalar(opts(raiz, manifestDe('1.0.0')))
  await assert.rejects(instalar(opts(raiz, manifestDe('1.1.0', true))), /SHA-256/)
  assert.deepEqual(lerEstado(raiz), { atual: '1.0.0', anterior: null })
  assert.ok(!existsSync(join(raiz, 'versions', '1.1.0')))
})

test('recusa pacote fora do endereço permitido', async () => {
  const raiz = join(tmp, 'c')
  const m = manifestDe('1.0.0')
  m.arquivo.url = 'https://exemplo.com/malicioso.zip'
  await assert.rejects(instalar(opts(raiz, m)), /não permitido/)
})
