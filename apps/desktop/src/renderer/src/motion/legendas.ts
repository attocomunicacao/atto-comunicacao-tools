/**
 * Motor de presets da legenda (v0.7). Referência: videoplayback.mp4 ("7 animações de texto"), medida quadro a
 * quadro em docs/pesquisa/2026-11-referencias-v07.md.
 *
 * O que a referência faz e a v0.6 não fazia (por isso parecia amadora):
 * 1. COMPOSIÇÃO: as palavras formam um BLOCO compacto em escada — linhas encostadas (entrelinha ~0,9, quase se
 *    tocando), cada linha deslocada um degrau, tamanho CRESCENTE até a palavra-chave. Nada de palavras soltas
 *    espalhadas numa caixa larga.
 * 2. MOVIMENTO CURTO: cada palavra entra em 5-6 quadros (~0,2-0,35 s), deslocando menos de meia altura de letra,
 *    com desfoque de movimento; nada de tremida, quique elástico ou voo de 60 px.
 * 3. O BLOCO NUNCA PARA: deriva devagar (sobe ~10 px e cresce ~2%) enquanto está na tela.
 * 4. SAÍDA LIMPA: o bloco inteiro some em desfoque em 4-5 quadros, encostando na entrada do próximo.
 *
 * Presets (só muda o movimento de entrada; a composição é a mesma):
 *   cinematico · maquina · sobe · desce · esquerda · direita · elastico · deslocamento  +  gancho: impacto · revelacao · glitch
 * Tudo branco. Palavra-chave em Playfair Display itálico (números e "elástico" em Inter 800). Determinístico.
 */
import gsap from 'gsap'
import type { Grupo, JobMotion, PalavraGrupo } from './tipos'

type T = gsap.core.Timeline
type Entrada = (t: T, w: HTMLElement, p: PalavraGrupo, ordem: number, tam: number, chave: boolean) => void

const el = (tag: string, cls: string, txt?: string) => {
  const e = document.createElement(tag)
  e.className = cls
  if (txt !== undefined) e.textContent = txt
  return e
}

const SAIDA = 0.16 // s: o bloco se desfaz em ~5 quadros
const ANTECIPA = 0.04 // a palavra começa a surgir um tiquinho antes de ser dita

interface Composicao {
  caixa: HTMLElement // área livre de rostos (do mapa de espaço)
  bloco: HTMLElement // o bloco em escada (é ele que deriva e sai)
  palavras: { e: HTMLElement; p: PalavraGrupo; chave: boolean; tam: number }[]
}

/** Medidas: a chave ocupa até ~86% da largura livre; as menores seguem a hierarquia da referência (1 : 1,2 : 1,6+). */
function medidas(g: Grupo, larg: number, chave: PalavraGrupo | undefined, maiusc = false) {
  const lk = chave ? chave.t.length : 6
  const fator = maiusc ? 0.66 : chave && /\d/.test(chave.t) ? 0.58 : 0.5
  const K = Math.round(Math.max(88, Math.min(156, (larg * 0.86) / Math.max(lk * fator, 1))))
  const S = Math.round(Math.max(42, Math.min(60, K * 0.44)))
  return { K, S, M: Math.round(S * 1.2) }
}

/**
 * Monta o bloco em escada. `escada`: 1 = degraus para a direita (desce para a direita), -1 = para a esquerda.
 * Linhas: [antes da chave] (pequena) → [chave] (grande) → [depois] (média). Sem chave: 2 linhas equilibradas.
 */
function compor(palco: HTMLElement, g: Grupo, escada: 1 | -1 = 1, opc: { maiusc?: boolean; chaveSans?: boolean } = {}): Composicao {
  const [x, y, w, h] = g.caixa ?? [60, 1270, 960, 450]
  const caixa = el('div', 'leg-caixa')
  Object.assign(caixa.style, { left: `${x}px`, top: `${y}px`, width: `${w}px`, height: `${h}px` })
  const bloco = el('div', 'leg-bloco')
  caixa.append(bloco)
  palco.appendChild(caixa)

  const k = g.palavras.findIndex((p) => p.chave)
  const { K, S, M } = medidas(g, w - 40, k >= 0 ? g.palavras[k] : undefined, opc.maiusc)
  let linhas: { idx: number[]; tam: number }[]
  if (k >= 0) {
    linhas = [
      { idx: g.palavras.map((_, i) => i).filter((i) => i < k), tam: S },
      { idx: [k], tam: K },
      { idx: g.palavras.map((_, i) => i).filter((i) => i > k), tam: M }
    ].filter((l) => l.idx.length)
  } else {
    const n = g.palavras.length
    const meio = Math.ceil(n / 2)
    const T2 = Math.round(Math.min(96, Math.max(64, (w * 0.8) / Math.max(g.palavras.slice(meio).map((p) => p.t).join(' ').length * 0.5, 1))))
    linhas = [{ idx: [...Array(meio).keys()], tam: Math.round(T2 * 0.8) }, { idx: [...Array(n - meio).keys()].map((i) => i + meio), tam: T2 }]
      .filter((l) => l.idx.length)
  }
  const palavras: Composicao['palavras'] = []
  const degrau = Math.round(K * 0.16)
  linhas.forEach((l, li) => {
    const linha = el('div', 'leg-linha')
    linha.style.fontSize = `${l.tam}px`
    // degrau: cada linha anda um pouco para o lado (escada), como na referência
    const passo = (li - (linhas.length - 1) / 2) * degrau * escada
    linha.style.transform = `translateX(${Math.round(passo)}px)`
    if (li > 0) linha.style.marginTop = `${-Math.round(l.tam * 0.1)}px`
    for (const i of l.idx) {
      const p = g.palavras[i]
      const ehChave = i === k
      const num = /\d/.test(p.t)
      const cls = ehChave ? (opc.chaveSans || num || opc.maiusc ? 'leg-p leg-chave-sans' : 'leg-p leg-chave') : 'leg-p'
      const e = el('span', cls, opc.maiusc && ehChave ? p.t.toUpperCase() : p.t)
      linha.append(e)
      palavras.push({ e, p, chave: ehChave, tam: l.tam })
    }
    bloco.append(linha)
  })
  return { caixa, bloco, palavras }
}

/** Deriva contínua + saída em desfoque (comuns a todos os presets). */
function viver(t: T, c: Composicao, g: Grupo, prox: Grupo | undefined, ultimaEntrada: number) {
  const fimVisivel = Math.max(Math.min(g.fim, prox ? prox.ini : g.fim), ultimaEntrada + 0.35)
  const ini = c.palavras[0]?.p.ini ?? g.ini
  t.fromTo(c.bloco, { y: 0, scale: 1 }, { y: -18, scale: 1.03, duration: Math.max(fimVisivel - ini, 0.3), ease: 'sine.out', immediateRender: false }, ini)
  t.to(c.bloco, { opacity: 0, filter: 'blur(10px)', scale: '+=0.012', duration: SAIDA, ease: 'power2.in' }, fimVisivel - SAIDA)
}

/** Aplica uma entrada palavra a palavra, no tempo da fala. */
function porPalavra(palco: HTMLElement, t: T, g: Grupo, prox: Grupo | undefined, entrada: Entrada, escada: 1 | -1 = 1,
  opc: { maiusc?: boolean; chaveSans?: boolean } = {}) {
  const c = compor(palco, g, escada, opc)
  gsap.set(c.palavras.map((x) => x.e), { opacity: 0 })
  let ultima = g.ini
  c.palavras.forEach((x, i) => {
    const quando = x.p.ini - ANTECIPA
    entrada(t, x.e, { ...x.p, ini: quando }, i, x.tam, x.chave)
    ultima = Math.max(ultima, quando)
  })
  viver(t, c, g, prox, ultima)
}

// ---------------------------------------------------------------- entradas (medidas na referência)

const O = { immediateRender: false }

/** Opacidade em tween próprio: a palavra vai de cinza a branco em ~8 quadros, sem "estalar" (referência). */
const acende = (t: T, w: HTMLElement, quando: number, dur = 0.36) =>
  t.fromTo(w, { opacity: 0 }, { opacity: 1, duration: dur, ease: 'power1.out', ...O }, quando)

/** Desliza pra cima: sobe ~0,4 da altura da letra, de 0 a 100% de opacidade, desfoque de movimento curto. */
const sobe: Entrada = (t, w, p, _o, tam) => {
  acende(t, w, p.ini)
  t.fromTo(w, { y: tam * 0.42, filter: 'blur(6px)' }, { y: 0, filter: 'blur(0px)', duration: 0.34, ease: 'expo.out', ...O }, p.ini)
}
/** Desliza pra baixo: vem de cima com rastro vertical (scaleY) que assenta. */
const desce: Entrada = (t, w, p, _o, tam) => {
  acende(t, w, p.ini)
  t.fromTo(w, { y: -tam * 0.42, scaleY: 1.18, filter: 'blur(7px)', transformOrigin: '50% 0%' },
    { y: 0, scaleY: 1, filter: 'blur(0px)', duration: 0.34, ease: 'expo.out', ...O }, p.ini)
}
/** Desliza pra esquerda: entra pela direita com rastro horizontal. */
const esquerda: Entrada = (t, w, p, _o, tam) => {
  acende(t, w, p.ini)
  t.fromTo(w, { x: tam * 0.6, scaleX: 1.12, filter: 'blur(8px)', transformOrigin: '0% 50%' },
    { x: 0, scaleX: 1, filter: 'blur(0px)', duration: 0.34, ease: 'expo.out', ...O }, p.ini)
}
/** Desliza pra direita: espelho. */
const direita: Entrada = (t, w, p, _o, tam) => {
  acende(t, w, p.ini)
  t.fromTo(w, { x: -tam * 0.6, scaleX: 1.12, filter: 'blur(8px)', transformOrigin: '100% 50%' },
    { x: 0, scaleX: 1, filter: 'blur(0px)', duration: 0.34, ease: 'expo.out', ...O }, p.ini)
}
/** Entrada com desfoque/deslocamento: chega muito desfocada, levemente maior e de lado, e assenta. */
const comDesfoque: Entrada = (t, w, p, o, tam) => {
  acende(t, w, p.ini)
  t.fromTo(w, { x: (o % 2 ? -1 : 1) * tam * 0.35, y: tam * 0.18, scale: 1.1, filter: 'blur(16px)' },
    { x: 0, y: 0, scale: 1, filter: 'blur(0px)', duration: 0.44, ease: 'power3.out', ...O }, p.ini)
}
/** Cinemático (minimal premium): pequenas surgem em fade suave; a chave abre o espaçamento e foca. */
const cinematicoE: Entrada = (t, w, p, _o, tam, chave) => {
  if (chave) {
    t.fromTo(w, { opacity: 0, letterSpacing: '0.06em', scale: 1.05, filter: 'blur(14px)' },
      { opacity: 1, letterSpacing: '0em', scale: 1, filter: 'blur(0px)', duration: 0.55, ease: 'power2.out', ...O }, p.ini)
  } else {
    t.fromTo(w, { opacity: 0, y: tam * 0.2, filter: 'blur(5px)' }, { opacity: 1, y: 0, filter: 'blur(0px)', duration: 0.3, ease: 'power2.out', ...O }, p.ini)
  }
}
/** Elástico (referência: um risco de luz que se comprime até a palavra). Sem quique: compressão expo. */
const elasticoE: Entrada = (t, w, p, o, tam, chave) => {
  if (!chave) return sobe(t, w, p, o, tam, chave)
  t.fromTo(w, { opacity: 0.95, scaleX: 2.6, scaleY: 0.07, filter: 'blur(9px) brightness(2.2)' },
    { scaleX: 1, scaleY: 1, filter: 'blur(0px) brightness(1)', duration: 0.34, ease: 'expo.out', ...O }, p.ini - 0.06)
  t.set(w, { opacity: 1 }, p.ini - 0.06)
}

function cinematico(palco: HTMLElement, t: T, g: Grupo, prox?: Grupo) { porPalavra(palco, t, g, prox, cinematicoE, 1) }
function sobeP(palco: HTMLElement, t: T, g: Grupo, prox?: Grupo) { porPalavra(palco, t, g, prox, sobe, 1) }
function desceP(palco: HTMLElement, t: T, g: Grupo, prox?: Grupo) { porPalavra(palco, t, g, prox, desce, -1) }
function esquerdaP(palco: HTMLElement, t: T, g: Grupo, prox?: Grupo) { porPalavra(palco, t, g, prox, esquerda, -1) }
function direitaP(palco: HTMLElement, t: T, g: Grupo, prox?: Grupo) { porPalavra(palco, t, g, prox, direita, 1) }
function deslocamento(palco: HTMLElement, t: T, g: Grupo, prox?: Grupo) { porPalavra(palco, t, g, prox, comDesfoque, 1) }
function elastico(palco: HTMLElement, t: T, g: Grupo, prox?: Grupo) { porPalavra(palco, t, g, prox, elasticoE, 1, { maiusc: true }) }

/** Máquina de escrever: letra por letra no ritmo da fala, com cursor que pisca e acompanha a última letra. */
function maquina(palco: HTMLElement, t: T, g: Grupo, prox?: Grupo) {
  const c = compor(palco, g, 1)
  const letras: [HTMLElement, number][] = []
  for (const x of c.palavras) {
    const txt = x.e.textContent ?? ''
    x.e.textContent = ''
    // referência: digitação rápida e regular (≤ 55% da palavra falada, nunca mais de 1 letra por quadro)
    const dur = Math.max(Math.min((x.p.fim - x.p.ini) * 0.55, txt.length * 0.045), txt.length / 30)
    ;[...txt].forEach((ch, j) => {
      const l = el('span', 'letra', ch)
      x.e.append(l)
      letras.push([l, x.p.ini - ANTECIPA + (j / Math.max(txt.length, 1)) * dur])
    })
  }
  const cursor = el('span', 'cursor', '|')
  cursor.style.fontSize = `${c.palavras[c.palavras.length - 1]?.tam ?? 60}px`
  c.palavras[c.palavras.length - 1]?.e.parentElement?.append(cursor)
  gsap.set(letras.map(([l]) => l), { opacity: 0 })
  for (const [l, quando] of letras) t.fromTo(l, { opacity: 0 }, { opacity: 1, duration: 0.03, ...O }, quando)
  // cursor aceso enquanto digita; depois pisca devagar (1 Hz), como na referência
  const fimDigitacao = letras.length ? letras[letras.length - 1][1] : g.ini
  const pisca = { v: 0 }
  const d = Math.max(g.fim - fimDigitacao, 0.3)
  t.to(pisca, { v: 1, duration: d, ease: 'none', onUpdate: () => {
    cursor.style.opacity = String(0.675 + 0.325 * Math.cos(pisca.v * d * Math.PI * 2)) // pulso suave, sem degrau
  } }, fimDigitacao)
  viver(t, c, g, prox, letras.length ? letras[letras.length - 1][1] : g.ini)
}

// ---------------------------------------------------------------- presets de gancho (primeiros segundos)

/** Impacto: a chave chega grande e desfocada e assenta seca (sem tremida), com um pulso de brilho. */
function impacto(palco: HTMLElement, t: T, g: Grupo, prox?: Grupo) {
  porPalavra(palco, t, g, prox, (tl, w, p, o, tam, chave) => {
    if (!chave) return sobe(tl, w, p, o, tam, chave)
    tl.fromTo(w, { opacity: 0, scale: 1.5, filter: 'blur(14px)' }, { opacity: 1, scale: 1, filter: 'blur(0px)', duration: 0.3, ease: 'expo.out', ...O }, p.ini)
    tl.fromTo(w, { textShadow: '0 0 70px rgba(255,255,255,0.95)' }, { textShadow: '0 2px 18px rgba(0,0,0,0.45)', duration: 0.7, ease: 'power2.out', ...O }, p.ini + 0.08)
  }, 1)
}

/** Revelação: cada palavra é revelada da esquerda para a direita por máscara, com um fio de luz na frente. */
function revelacao(palco: HTMLElement, t: T, g: Grupo, prox?: Grupo) {
  porPalavra(palco, t, g, prox, (tl, w, p) => {
    const dur = Math.min(0.45, Math.max(p.fim - p.ini, 0.3))
    acende(tl, w, p.ini)
    tl.fromTo(w, { clipPath: 'inset(-20% 100% -20% 0%)', filter: 'blur(3px)' },
      { clipPath: 'inset(-20% -5% -20% 0%)', filter: 'blur(0px)', duration: dur, ease: 'power2.inOut', ...O }, p.ini)
  }, 1)
}

/** Glitch (monocromático, referência "LINK NA BIO"): cópias fantasmas deslocadas que convergem em ~0,3 s. */
function glitch(palco: HTMLElement, t: T, g: Grupo, prox?: Grupo) {
  porPalavra(palco, t, g, prox, (tl, w, p) => {
    acende(tl, w, p.ini)
    const q = { v: 0 }
    tl.to(q, { v: 1, duration: 0.3, ease: 'none', onUpdate: () => {
      const a = (1 - q.v) * 18
      w.style.textShadow = `${Math.round(Math.sin(q.v * 31) * a)}px 0 0 rgba(255,255,255,${0.55 * (1 - q.v)}), ${-Math.round(Math.cos(q.v * 27) * a)}px 0 0 rgba(255,255,255,${0.4 * (1 - q.v)}), 0 2px 18px rgba(0,0,0,0.45)`
      w.style.clipPath = q.v < 0.55 ? `inset(${Math.round(Math.abs(Math.sin(q.v * 19)) * 35)}% 0 0 0)` : 'none'
    } }, p.ini)
  }, -1, { maiusc: false })
}

const PRESETS: Record<string, (palco: HTMLElement, t: T, g: Grupo, prox?: Grupo) => void> = {
  cinematico, maquina, sobe: sobeP, desce: desceP, esquerda: esquerdaP, direita: direitaP, elastico, deslocamento,
  impacto, revelacao, glitch
}

export function legenda(palco: HTMLElement, job: JobMotion, t: T) {
  // citação e conceito ocupam a tela com texto próprio: a legenda some durante eles (lab ciclo 16)
  const cobertos = job.cenas.filter((c) => c.cobreLegenda || c.tipo === 'citacao' || c.tipo === 'conceito')
  job.grupos.forEach((g, gi) => {
    if (cobertos.some((c) => g.ini >= c.ini - 0.05 && g.ini < c.fim)) return
    // lab ciclo 15: a linha que começou antes de uma cena de tela cheia sai antes dela entrar (não fica por baixo)
    const corta = cobertos.find((c) => g.ini < c.ini && g.fim > c.ini - 0.05)
    if (corta) g = { ...g, fim: Math.max(corta.ini - 0.05, g.ini + 0.3) }
    const preset = PRESETS[g.preset ?? 'cinematico'] ?? cinematico
    preset(palco, t, g, job.grupos[gi + 1])
  })
}
