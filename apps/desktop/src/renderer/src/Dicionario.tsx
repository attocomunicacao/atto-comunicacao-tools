import { useEffect, useState } from 'react'

type Termos = Record<string, string[]>

/** Lê a linha `DICIONARIO {...}` devolvida pelo motor. */
async function chamar(acao: string, termo?: string): Promise<Termos> {
  let resultado: Termos = {}
  const parar = window.atto.aoLinha((l) => {
    if (l.startsWith('DICIONARIO ')) resultado = JSON.parse(l.slice(11))
  })
  await window.atto.motor('dicionario', termo ? [acao, termo] : [acao])
  parar()
  return resultado
}

export function Dicionario() {
  const [termos, setTermos] = useState<Termos>({})
  const [novo, setNovo] = useState('')

  useEffect(() => {
    chamar('listar').then(setTermos)
  }, [])

  const adicionar = async () => {
    if (!novo.trim()) return
    setTermos(await chamar('adicionar', novo.trim()))
    setNovo('')
  }

  const nomes = Object.keys(termos)
  return (
    <>
      <div className="topo">
        <div className="rotulo">Meu dicionário</div>
        <h1>Termos que o Garimpo conhece</h1>
        <p className="sub">
          Nomes de empresas, sindicatos e pessoas. O dicionário é só seu: fica neste computador e cresce quando você
          aprova uma correção.
        </p>
      </div>
      <div className="painel">
        <form
          className="dic-form"
          onSubmit={(e) => {
            e.preventDefault()
            adicionar()
          }}
        >
          <input value={novo} onChange={(e) => setNovo(e.target.value)} placeholder="Escreva o termo correto, ex.: SINDEPRESTEM" aria-label="Novo termo" />
          <button className="btn" type="submit" disabled={!novo.trim()}>
            Adicionar
          </button>
        </form>
        {nomes.length === 0 && <p className="vazio">Nenhum termo ainda.</p>}
        {nomes.map((t) => (
          <div className="linha-termo" key={t}>
            <div>
              <strong>{t}</strong>
              {termos[t].length > 0 && (
                <div className="variantes">
                  {termos[t].map((v) => (
                    <span className="chip" key={v}>
                      {v}
                    </span>
                  ))}
                </div>
              )}
            </div>
            <button className="link" onClick={async () => setTermos(await chamar('remover', t))}>
              Remover
            </button>
          </div>
        ))}
      </div>
    </>
  )
}
