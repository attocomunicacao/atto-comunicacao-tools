import { useEffect, useRef, useState } from 'react'
import { Carregamento, LogoFinal, RecursosEdicao, useAndamento } from './Carregamento'

type Etapa = 'video' | 'transcricao' | 'duvidas' | 'estrutura' | 'cortes' | 'exportar'
const PASSOS: { id: Etapa[]; nome: string }[] = [
  { id: ['video'], nome: '1 Vídeo' },
  { id: ['transcricao'], nome: '2 Transcrição' },
  { id: ['duvidas', 'estrutura'], nome: '3 Dúvidas' },
  { id: ['cortes'], nome: '4 Cortes' },
  { id: ['exportar'], nome: '5 Exportar' }
]

interface Duvida { id: number; original: string; sugestao: string; confianca: number; conhecida: boolean; inicio: number; fim: number; contexto: string }
interface Corte { n: number; tema: string; ini: number; fim: number; duracao: number; texto: string }

const nomeArquivo = (c: string) => c.split(/[\\/]/).pop() ?? c
const tempo = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`

export function Garimpo() {
  const [etapa, setEtapa] = useState<Etapa>('video')
  const [video, setVideo] = useState<string | null>(null)
  const [pasta, setPasta] = useState<string | null>(null)
  const [erro, setErro] = useState('')
  const [duvidas, setDuvidas] = useState<Duvida[]>([])
  const [aprovadas, setAprovadas] = useState<Set<number>>(new Set())
  const [cortes, setCortes] = useState<Corte[]>([])
  const [escolhidos, setEscolhidos] = useState<Set<number>>(new Set())
  const [gerados, setGerados] = useState<string[]>([])
  const [descricao, setDescricao] = useState(() => { try { return localStorage.getItem('garimpo.descricao') ?? '' } catch { return '' } })
  const [refazer, setRefazer] = useState(false)
  const [reaproveitada, setReaproveitada] = useState(false)
  const andamento = useAndamento()

  const rodar = async (cmd: string, args: string[], aoLinha?: (l: string) => void) => {
    setErro('')
    andamento.zerar()
    const parar = aoLinha ? window.atto.aoLinha(aoLinha) : () => {}
    const r = await window.atto.motor(cmd, args)
    parar()
    if (r.codigo !== 0) throw new Error(r.erro || 'O motor terminou com erro.')
  }

  const falhou = (e: unknown, voltarPara: Etapa) => {
    setErro(e instanceof Error ? e.message : String(e))
    setEtapa(voltarPara)
  }

  const escolher = async () => {
    const v = await window.atto.escolherVideo()
    if (v) { setVideo(v); setErro('') }
  }

  const comecar = async () => {
    if (!video) return
    try {
      const p = await window.atto.criarProjeto(video)
      setPasta(p)
      setEtapa('transcricao')
      setReaproveitada(false)
      try { localStorage.setItem('garimpo.descricao', descricao) } catch { /* sem armazenamento */ }
      await rodar('transcrever', [video, '--pasta', p, ...(refazer ? ['--refazer'] : [])], (l) => {
        if (l.startsWith('CACHE transcricao')) setReaproveitada(true)
      })
      const itens = await window.atto.lerJson<Duvida[]>(p, 'duvidas.json')
      setDuvidas(itens)
      setAprovadas(new Set(itens.filter((d) => d.confianca >= 0.9).map((d) => d.id)))
      setEtapa('duvidas')
    } catch (e) { falhou(e, 'video') }
  }

  const estruturar = async () => {
    if (!video || !pasta) return
    try {
      setEtapa('estrutura')
      await rodar('estruturar', [video, '--pasta', pasta, '--aprovadas', [...aprovadas].join(','), '--descricao', descricao.trim()])
      const cs = await window.atto.lerJson<Corte[]>(pasta, 'cortes.json')
      setCortes(cs)
      setEscolhidos(new Set())
      setEtapa('cortes')
    } catch (e) { falhou(e, 'duvidas') }
  }

  const exportar = async () => {
    if (!video || !pasta) return
    try {
      setGerados([])
      setEtapa('exportar')
      await rodar('exportar', [video, '--pasta', pasta, '--aprovados', [...escolhidos].join(',')], (l) => {
        if (l.startsWith('ARQUIVO ')) setGerados((g) => [...g, l.slice(8)])
      })
      andamento.zerar()
    } catch (e) { falhou(e, 'cortes') }
  }

  const alternar = (conj: Set<number>, set: (s: Set<number>) => void, id: number) => {
    const n = new Set(conj)
    n.has(id) ? n.delete(id) : n.add(id)
    set(n)
  }

  const idxPasso = PASSOS.findIndex((p) => p.id.includes(etapa))
  const ocupado = etapa === 'transcricao' || etapa === 'estrutura' || (etapa === 'exportar' && gerados.length < escolhidos.size && !erro)

  return (
    <>
      <div className="topo">
        <div className="rotulo">Garimpo</div>
        <h1>Cortes verticais a partir de palestras e podcasts</h1>
        <p className="sub">Escolha o vídeo. O Garimpo transcreve, separa por temas e sugere cortes de 30 s a 1min30 com legenda palavra por palavra.</p>
      </div>
      <ol className="passos" aria-label="Etapas">
        {PASSOS.map((p, i) => (
          <li key={p.nome} className={i === idxPasso ? 'ativo' : i < idxPasso ? 'feito' : ''}>{p.nome}</li>
        ))}
      </ol>

      <section className="painel">
        {etapa === 'video' && (
          <>
            <p className="sub">Formatos aceitos: MP4, MOV, MTS, MKV e outros. Gravações longas demoram: a transcrição roda no seu processador.</p>
            <div className="acoes">
              <button className="btn sec" onClick={escolher}>{video ? 'Trocar vídeo' : 'Escolher vídeo'}</button>
              <button className="btn" onClick={comecar} disabled={!video}>Começar</button>
            </div>
            {video && <p className="caminho">{video}</p>}
            <label className="campo">
              <span className="campo-titulo">Descrição do vídeo <span className="meta">(opcional, guia a escolha dos cortes)</span></span>
              <textarea rows={3} value={descricao} onChange={(e) => setDescricao(e.target.value)}
                placeholder="Ex.: podcast sobre reforma tributária para donos de pequenas empresas; quero cortes que expliquem o que muda na prática." />
            </label>
            <label className="opcao">
              <input type="checkbox" checked={refazer} onChange={(e) => setRefazer(e.target.checked)} />
              Transcrever de novo <span className="meta">(ignora a transcrição já guardada deste vídeo)</span>
            </label>
            <LogoFinal />
          </>
        )}

        {(etapa === 'transcricao' || etapa === 'estrutura') && (
          <>
            <Carregamento titulo={etapa === 'transcricao' ? 'Transcrevendo' : 'Analisando temas e cortes'} a={andamento} />
          </>
        )}

        {etapa === 'duvidas' && (
          <>
            {reaproveitada && <p className="aviso-ok">Transcrição reaproveitada: este vídeo já tinha sido transcrito.</p>}
            <h2 style={{ margin: '0 0 6px', fontWeight: 500 }}>Dúvidas de escrita</h2>
            <p className="sub" style={{ marginBottom: 18 }}>Aprove as correções corretas. Elas entram no seu dicionário e serão aplicadas sozinhas da próxima vez.</p>
            {duvidas.length === 0 ? (
              <p className="vazio">Nenhuma dúvida encontrada. Cadastre termos em “Meu dicionário” para o Garimpo vigiar nomes difíceis.</p>
            ) : (
              <div className="lista">
                {duvidas.map((d) => (
                  <label key={d.id} className={'item' + (aprovadas.has(d.id) ? ' marcado' : '')}>
                    <input type="checkbox" checked={aprovadas.has(d.id)} onChange={() => alternar(aprovadas, setAprovadas, d.id)} />
                    <div>
                      <h3>{d.original} <span className="setas">→</span> {d.sugestao}</h3>
                      <p className="meta">Confiança {Math.round(d.confianca * 100)}%{d.conhecida ? ' · já aprovada antes' : ''}</p>
                      <p className="contexto">
                        …{d.contexto.slice(0, d.contexto.indexOf(d.original))}<mark>{d.original}</mark>{d.contexto.slice(d.contexto.indexOf(d.original) + d.original.length)}…
                      </p>
                    </div>
                  </label>
                ))}
              </div>
            )}
            <div className="acoes"><button className="btn" onClick={estruturar}>Continuar</button></div>
          </>
        )}

        {etapa === 'cortes' && pasta && (
          <>
            <h2 style={{ margin: '0 0 6px', fontWeight: 500 }}>{cortes.length} cortes sugeridos</h2>
            <p className="sub" style={{ marginBottom: 18 }}>Ouça e marque os que quer gerar.</p>
            {cortes.length === 0 && <p className="vazio">Nenhum trecho de 30 s a 1min30 foi encontrado. Tente um vídeo mais longo.</p>}
            <div className="lista">
              {cortes.map((c) => (
                <div key={c.n} className={'item' + (escolhidos.has(c.n) ? ' marcado' : '')}>
                  <input type="checkbox" checked={escolhidos.has(c.n)} onChange={() => alternar(escolhidos, setEscolhidos, c.n)} aria-label={`Aprovar corte ${c.n}`} />
                  <div>
                    <h3>Corte {String(c.n).padStart(2, '0')} · {Math.round(c.duracao)} s</h3>
                    <p className="meta">{tempo(c.ini)} a {tempo(c.fim)} · tema: {c.tema}</p>
                    <p className="texto">{c.texto}</p>
                    <Previa pasta={pasta} nome={`corte-${String(c.n).padStart(2, '0')}.wav`} />
                  </div>
                </div>
              ))}
            </div>
            <LogoFinal />
            <RecursosEdicao />
            <div className="acoes">
              <button className="btn" onClick={exportar} disabled={escolhidos.size === 0}>Gerar {escolhidos.size || ''} {escolhidos.size === 1 ? 'corte' : 'cortes'}</button>
              <button className="btn sec" onClick={() => setEtapa('duvidas')}>Voltar</button>
            </div>
          </>
        )}

        {etapa === 'exportar' && (
          <>
            {ocupado ? <Carregamento titulo="Gerando vídeos" a={andamento} /> : <h2 style={{ margin: 0, fontWeight: 500 }}>Pronto</h2>}
            <div className="lista" style={{ marginTop: 18 }}>
              {gerados.map((g) => (
                <div className="item" key={g}>
                  <span className="setas">✓</span>
                  <div>
                    <h3>{nomeArquivo(g)}</h3>
                    <button className="link" onClick={() => window.atto.mostrarNaPasta(g)}>Mostrar na pasta</button>
                  </div>
                </div>
              ))}
            </div>
            {!ocupado && (
              <div className="acoes">
                <button className="btn sec" onClick={() => setEtapa('cortes')}>Voltar aos cortes</button>
                <button className="btn sec" onClick={() => { setVideo(null); setPasta(null); setEtapa('video') }}>Novo vídeo</button>
              </div>
            )}
          </>
        )}

        {erro && <p className="erro" role="alert">{erro}</p>}
      </section>
    </>
  )
}

function Previa({ pasta, nome }: { pasta: string; nome: string }) {
  const [url, setUrl] = useState<string | null>(null)
  const ativo = useRef(true)
  useEffect(() => {
    ativo.current = true
    let u: string | null = null
    window.atto.lerBytes(pasta, 'previas', nome).then((b) => {
      if (!ativo.current) return
      u = URL.createObjectURL(new Blob([b as BlobPart], { type: 'audio/wav' }))
      setUrl(u)
    })
    return () => { ativo.current = false; if (u) URL.revokeObjectURL(u) }
  }, [pasta, nome])
  return url ? <audio controls src={url} /> : <p className="meta">Carregando prévia…</p>
}
