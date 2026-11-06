import { useEffect, useState } from 'react'
import { Dicionario } from './Dicionario'
import { Garimpo } from './Garimpo'

type Tela = 'garimpo' | 'dicionario'

export function App() {
  const [tela, setTela] = useState<Tela>('garimpo')
  const [versao, setVersao] = useState('')
  useEffect(() => { window.atto.versao().then(setVersao).catch(() => {}) }, [])
  return (
    <div className="app">
      <aside className="side">
        <div className="marca">
          ATTO <span>TOOLS</span>
        </div>
        <nav className="nav" aria-label="Ferramentas">
          <button className={tela === 'garimpo' ? 'ativo' : ''} onClick={() => setTela('garimpo')}>
            Garimpo
          </button>
          <button className={tela === 'dicionario' ? 'ativo' : ''} onClick={() => setTela('dicionario')}>
            Meu dicionário
          </button>
        </nav>
        <div className="versao">{versao ? `v${versao}` : ""}</div>
      </aside>
      <main className="main">
        {/* Garimpo fica montado para não perder o andamento ao trocar de tela */}
        <div hidden={tela !== 'garimpo'}>
          <Garimpo />
        </div>
        {tela === 'dicionario' && <Dicionario />}
      </main>
    </div>
  )
}
