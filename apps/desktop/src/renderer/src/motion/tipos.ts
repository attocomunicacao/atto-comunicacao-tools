/** Dados que o motor (Python) entrega para a camada de motion de um corte. Tempos em segundos desde o início do corte. */
export interface PalavraMotion { t: string; ini: number; fim: number; enfase?: boolean }

export interface Cena {
  tipo: 'numero' | 'comparacao' | 'icone' | 'destaque'
  ini: number
  fim: number
  texto?: string
  valor?: number
  sufixo?: string
  antes?: string
  depois?: string
  icone?: string // nome Lucide em PascalCase (ex.: "Clock", "Scale")
}

export interface JobMotion {
  largura: number
  altura: number
  fps: number
  duracao: number
  palavras: PalavraMotion[]
  cenas: Cena[]
  transicoes?: number[]
  fontes?: string
}
