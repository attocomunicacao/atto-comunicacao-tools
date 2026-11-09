/** Dados que o motor (Python) entrega para a camada de motion de um corte. Tempos em segundos desde o início do corte. */
export interface PalavraGrupo { t: string; ini: number; fim: number; chave: boolean }
export interface Grupo {
  ini: number
  fim: number
  palavras: PalavraGrupo[]
  preset?: string // motor de presets (garimpo/motion.escolher_presets)
  zona?: string
  caixa?: [number, number, number, number] // x, y, w, h livre de rostos (garimpo/espaco.py)
}

export interface Cena {
  tipo: 'numero' | 'comparacao' | 'icone' | 'destaque' | 'citacao' | 'pintura' | 'imagem' | 'documento'
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
  destaque?: string // documento: palavras marcadas
  rotulo?: string // documento: chapéu
  zona?: string
  caixa?: [number, number, number, number]
  telaCheia?: boolean // sem espaço livre em volta do rosto: vira um corte em tela cheia
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
