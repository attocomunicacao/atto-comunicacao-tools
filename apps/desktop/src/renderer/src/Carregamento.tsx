import { useEffect, useRef, useState } from 'react'

interface Passo { n: number; texto: string }
interface Andamento {
  passo: number
  total: number
  pctPasso: number | null
  passos: Passo[]
  log: { t: number; texto: string }[]
  inicio: number | null
}
const ZERO: Andamento = { passo: 0, total: 0, pctPasso: null, passos: [], log: [], inicio: null }

/** Lê as linhas do motor: `ETAPA n/total texto`, `PCT 0-100` (dentro da etapa) e `LOG detalhe`. */
export function useAndamento() {
  const [a, setA] = useState<Andamento>(ZERO)
  useEffect(
    () =>
      window.atto.aoLinha((l) => {
        setA((ant) => {
          const agora = Date.now()
          const base = { ...ant, inicio: ant.inicio ?? agora }
          const m = l.match(/^ETAPA (\d+)\/(\d+) (.*)/)
          if (m) {
            const n = Number(m[1])
            return {
              ...base,
              passo: n,
              total: Number(m[2]),
              pctPasso: null,
              passos: [...base.passos.filter((p) => p.n !== n), { n, texto: m[3] }].sort((x, y) => x.n - y.n),
              log: [...base.log, { t: agora, texto: `▶ ${m[3]}` }].slice(-3000)
            }
          }
          const p = l.match(/^PCT (\d+)/)
          if (p) return { ...base, pctPasso: Number(p[1]) }
          const g = l.match(/^LOG (.*)/)
          return { ...base, log: [...base.log, { t: agora, texto: g ? g[1] : l }].slice(-3000) }
        })
      }),
    []
  )
  return { ...a, zerar: () => setA({ ...ZERO, inicio: Date.now() }) }
}
export type EstadoAndamento = ReturnType<typeof useAndamento>

const dur = (ms: number) => {
  const s = Math.max(0, Math.floor(ms / 1000))
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
}

/** Progresso geral, etapas, tempo decorrido e, sob demanda, o registro detalhado do que o motor está fazendo. */
export function Carregamento({ titulo, a }: { titulo: string; a: EstadoAndamento }) {
  const [aberto, setAberto] = useState(false)
  const [agora, setAgora] = useState(Date.now())
  const fim = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const i = setInterval(() => setAgora(Date.now()), 1000)
    return () => clearInterval(i)
  }, [])
  useEffect(() => {
    if (aberto) fim.current?.scrollIntoView({ block: 'end' })
  }, [a.log.length, aberto])
  const pct = a.total > 0 ? Math.min(100, ((a.passo - 1 + (a.pctPasso ?? 0) / 100) / a.total) * 100) : null
  const atual = a.passos.find((p) => p.n === a.passo)
  return (
    <>
      <div className="carga-topo">
        <h2 style={{ margin: 0, fontWeight: 500 }}>{titulo}</h2>
        <span className="carga-tempo" title="Tempo decorrido">{a.inicio ? dur(agora - a.inicio) : '0:00'}</span>
      </div>
      <div className={'barra' + (pct === null ? ' indef' : '')} role="progressbar" aria-valuenow={pct === null ? undefined : Math.round(pct)}>
        <div style={pct === null ? undefined : { width: `${Math.max(pct, 3)}%` }} />
      </div>
      <p className="estado">
        {atual ? `${atual.texto}${a.pctPasso !== null ? ` · ${a.pctPasso}%` : ''}` : 'Iniciando o motor…'}
        {pct !== null && <span className="carga-geral"> · geral {Math.round(pct)}%</span>}
      </p>
      {a.passos.length > 0 && (
        <ol className="carga-passos">
          {a.passos.map((p) => (
            <li key={p.n} className={p.n < a.passo ? 'feito' : p.n === a.passo ? 'ativo' : ''}>
              <span>{p.n < a.passo ? '✓' : p.n === a.passo ? '●' : '○'}</span> {p.texto}
            </li>
          ))}
        </ol>
      )}
      <button className="link" onClick={() => setAberto(!aberto)} aria-expanded={aberto}>
        {aberto ? 'Esconder detalhes' : 'Ver detalhes do que está sendo feito'}
      </button>
      {aberto && (
        <div className="carga-log" role="log" aria-live="off">
          {a.log.length === 0 && <div>Ainda sem registros…</div>}
          {a.log.map((l, i) => (
            <div key={i}>
              <span className="t">{a.inicio ? dur(l.t - a.inicio) : ''}</span> {l.texto}
            </div>
          ))}
          <div ref={fim} />
        </div>
      )}
      <p className="estado" style={{ marginTop: 12 }}>Pode demorar vários minutos, dependendo do tamanho do vídeo.</p>
    </>
  )
}

/** Logo que aparece no fim de todos os cortes (guardada no computador; vale para todos os projetos). */
export function LogoFinal() {
  const [url, setUrl] = useState<string | null>(null)
  const carregar = async () => {
    const b = await window.atto.logoBytes()
    setUrl((antiga) => {
      if (antiga) URL.revokeObjectURL(antiga)
      return b ? URL.createObjectURL(new Blob([b as BlobPart])) : null
    })
  }
  useEffect(() => {
    carregar().catch(() => {})
  }, [])
  return (
    <div className="logo-final">
      <div className="logo-previa">{url ? <img src={url} alt="Logo escolhida" /> : <span>sem logo</span>}</div>
      <div>
        <h3>Logo no final dos cortes</h3>
        <p className="meta">
          {url ? 'Entra em todos os cortes, com fade suave, por 2 s no final.' : 'Opcional. PNG com fundo transparente fica melhor.'}
        </p>
        <div className="acoes" style={{ marginTop: 8 }}>
          <button className="btn sec" onClick={async () => { await window.atto.escolherLogo(); await carregar() }}>
            {url ? 'Trocar logo' : 'Anexar logo'}
          </button>
          {url && (
            <button className="link" onClick={async () => { await window.atto.removerLogo(); await carregar() }}>Remover</button>
          )}
        </div>
      </div>
    </div>
  )
}
