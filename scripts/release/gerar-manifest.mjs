// Gera o manifest.json da release a partir do pacote .zip (calcula o SHA-256).
// Uso: node scripts/release/gerar-manifest.mjs <pacote.zip> <versao> [notas] [saida=manifest.json]
// O manifest é publicado como arquivo da Release; o launcher confere o SHA-256 antes de instalar.
import { createHash } from 'node:crypto'
import { readFileSync, statSync, writeFileSync } from 'node:fs'
import { basename } from 'node:path'

const REPO = process.env.GITHUB_REPOSITORY ?? 'attocomunicacao/atto-comunicacao-tools'
const [zip, versao, notas = '', saida = 'manifest.json'] = process.argv.slice(2)

if (!zip || !/^\d+\.\d+\.\d+$/.test(versao ?? '')) {
  console.error('Uso: gerar-manifest.mjs <pacote.zip> <versao x.y.z> [notas] [saida]')
  process.exit(1)
}

const nome = basename(zip)
const manifest = {
  versao,
  publicadoEm: new Date().toISOString(),
  notas,
  executavel: 'ATTO Tools.exe',
  arquivo: {
    nome,
    url: `https://github.com/${REPO}/releases/download/v${versao}/${encodeURIComponent(nome)}`,
    sha256: createHash('sha256').update(readFileSync(zip)).digest('hex'),
    tamanho: statSync(zip).size
  }
}
writeFileSync(saida, JSON.stringify(manifest, null, 2) + '\n', 'utf-8')
console.log(`manifest.json gerado para a versão ${versao} (${manifest.arquivo.sha256.slice(0, 12)}…)`)
