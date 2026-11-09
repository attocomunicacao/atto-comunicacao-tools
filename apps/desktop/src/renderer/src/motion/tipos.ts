/** Dados que o motor (Python) entrega para a camada de motion de um corte. Tempos em segundos desde o início do corte. */
export interface PalavraGrupo { t: string; ini: number; fim: number; chave: boolean }
export interface Grupo { ini: number; fim: number; palavras: PalavraGrupo[] }

export interface Cena {
  tipo: 'numero' | 'comparacao' | 'icone' | 'destaque' | 'citacao' | 'pintura' | 'imagem'
  ini: number
  fim: number
  texto?: string
  valor?: number
  sufixo?: string
  antes?: string
  depois?: string
  icone?: string // nome Lucide em PascalCase (ex.: "Clock", "Scale")
  img?: string // data URI da pintura/imagem
  prof?: string // data URI do mapa de profundidade (efeito 3D)
  credito?: string
  cobreLegenda?: boolean
}

export interface JobMotion {
  largura: number
  altura: number
  fps: number
  duracao: number
  grupos: Grupo[]
  cenas: Cena[]
  transicoes?: number[]
}
