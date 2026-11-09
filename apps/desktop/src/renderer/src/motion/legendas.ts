/**
 * Motor de presets da legenda. Cada linha (até 5 palavras) chega do motor com `preset` e `caixa` (zona livre de
 * rostos, ver garimpo/espaco.py). Presets lidos quadro a quadro das referências (docs/pesquisa/2026-11-referencias-edicao.md):
 *
 * Linha:   cinematico · maquina (máquina de escrever) · sobe · desce · esquerda · direita · elastico · deslocamento
 * Gancho:  impacto · revelacao · glitch
 *
 * Tudo branco. Palavra-chave em Playfair Display itálico (números em Inter 800). Sempre determinístico.
 */
import gsap from 'gsap'
import type { Grupo, JobMotion, PalavraGrupo } from './tipos'

type T = gsap.core.Timeline
const el = (tag: string, cls: string, txt?: string) => {
  const e = document.createElement(tag)
  e.className = cls
  if (txt !== undefined) e.textContent = txt
  return e
}

function tamanhoChave(t: string, larg: number): number {
  return Math.max(76, Math.min(150, larg / Math.max(t.length * 0.52, 1)))
}

/** Bloco posicionado na caixa livre (centralizado verticalmente nela). */
function bloco(palco: HTMLElement, g: Grupo, extra = ''): HTMLElement {
  const [x, y, w, h] = g.caixa ?? [60, 1270, 960, 450]
  const b = el('div', 'grupo ' + extra)
  Object.assign(b.style, { left: `${x}px`, top: `${y}px`, width: `${w}px`, height: `${h}px` })
  palco.appendChild(b)
  return b
}

function chaveEl(p: PalavraGrupo, larg: number, escala = 1): HTMLElement {
  const num = /\d/.test(p.t)
  const e = el('span', num ? 'chave chave-sans' : 'chave', p.t)
  e.style.fontSize = `${tamanhoChave(p.t, larg) * (num ? 0.9 : 1) * escala}px`
  return e
}

/** Saída comum: a linha inteira se desfaz em desfoque antes da próxima. */
function sair(t: T, b: HTMLElement, g: Grupo, prox: Grupo | undefined, desde: number) {
  const sai = Math.min(g.fim, prox ? prox.ini : g.fim) - 0.26
  t.to(b, { opacity: 0, filter: 'blur(12px)', y: '-=18', duration: 0.28, ease: 'power2.in' }, Math.max(sai, desde + 0.25))
}

function ki(g: Grupo) {
  return g.palavras.findIndex((p) => p.chave)
}

// ---------------------------------------------------------------- presets de linha

/** Cinematográfico (referência minimal): pequenas acima/abaixo surgem na fala; chave revela com desfoque longo. */
function cinematico(palco: HTMLElement, t: T, g: Grupo, prox?: Grupo) {
  const b = bloco(palco, g)
  const k = ki(g)
  const larg = (g.caixa?.[2] ?? 960) - 40
  const antes = el('div', 'linha-peq'), depois = el('div', 'linha-peq')
  const peqs: [HTMLElement, number][] = []
  let chave: HTMLElement | null = null
  g.palavras.forEach((p, i) => {
    if (i === k) { chave = chaveEl(p, larg); return }
    const s = el('span', 'peq', p.t)
    ;(k < 0 || i < k ? antes : depois).append(s, document.createTextNode(' '))
    peqs.push([s, p.ini])
  })
  if (antes.childNodes.length) b.append(antes)
  if (chave) b.append(chave)
  if (depois.childNodes.length) b.append(depois)
  gsap.set(peqs.map(([s]) => s), { opacity: 0 })
  for (const [s, ini] of peqs) {
    t.fromTo(s, { opacity: 0, y: 14, filter: 'blur(8px)' }, { opacity: 1, y: 0, filter: 'blur(0px)', duration: 0.45, ease: 'power3.out', immediateRender: false }, ini - 0.04)
  }
  if (chave) {
    gsap.set(chave, { opacity: 0 })
    t.fromTo(chave, { opacity: 0, y: -60, scale: 1.1, letterSpacing: '0.08em', filter: 'blur(18px)' },
      { opacity: 1, y: 0, scale: 1, letterSpacing: '0em', filter: 'blur(0px)', duration: 0.85, ease: 'expo.out', immediateRender: false }, g.palavras[k].ini - 0.06)
  }
  t.fromTo(b, { y: 0 }, { y: -10, duration: Math.max(g.fim - g.ini, 0.4), ease: 'sine.inOut', immediateRender: false }, g.ini)
  sair(t, b, g, prox, g.ini)
}

/** Máquina de escrever: letra por letra no ritmo da fala, cursor piscando; chave em serifa. */
function maquina(palco: HTMLElement, t: T, g: Grupo, prox?: Grupo) {
  const b = bloco(palco, g)
  const linha = el('div', 'linha-maquina')
  const k = ki(g)
  const letras: [HTMLElement, number][] = []
  g.palavras.forEach((p, i) => {
    const w = el('span', i === k ? 'serif maq-chave' : 'maq')
    const dur = Math.max(p.fim - p.ini, 0.12)
    ;[...p.t].forEach((ch, j) => {
      const l = el('span', 'letra', ch)
      w.append(l)
      letras.push([l, p.ini + (j / Math.max(p.t.length, 1)) * dur * 0.9])
    })
    linha.append(w, document.createTextNode(' '))
  })
  const cursor = el('span', 'cursor', '|')
  linha.append(cursor)
  b.append(linha)
  gsap.set(letras.map(([l]) => l), { opacity: 0 })
  for (const [l, quando] of letras) t.to(l, { opacity: 1, duration: 0.01 }, quando)
  // cursor pisca (função do tempo, sem repeat infinito)
  const pisca = { v: 0 }
  t.to(pisca, { v: 1, duration: g.fim - g.ini, ease: 'none', onUpdate: () => {
    cursor.style.opacity = Math.floor(pisca.v * (g.fim - g.ini) * 2.2) % 2 === 0 ? '1' : '0'
  } }, g.ini)
  sair(t, b, g, prox, g.ini)
}

/** Desliza (cima/baixo/esquerda/direita): palavras empilhadas entram por máscara, com desfoque de movimento. */
function desliza(direcao: 'sobe' | 'desce' | 'esquerda' | 'direita') {
  return (palco: HTMLElement, t: T, g: Grupo, prox?: Grupo) => {
    const b = bloco(palco, g, 'pilha')
    const k = ki(g)
    const larg = (g.caixa?.[2] ?? 960) - 40
    const linhas: HTMLElement[] = []
    // até 3 linhas: agrupa as palavras pequenas em volta da chave
    let atual = el('div', 'pilha-linha')
    g.palavras.forEach((p, i) => {
      const masc = el('span', 'mascara')
      const s = i === k ? chaveEl(p, larg, 0.85) : el('span', 'peq-grande', p.t)
      masc.append(s)
      if (i === k) {
        if (atual.childNodes.length) linhas.push(atual)
        const lk = el('div', 'pilha-linha')
        lk.append(masc)
        linhas.push(lk)
        atual = el('div', 'pilha-linha')
      } else atual.append(masc, document.createTextNode(' '))
      const de = direcao === 'sobe' ? { yPercent: 110 } : direcao === 'desce' ? { yPercent: -110 } : direcao === 'esquerda' ? { xPercent: 70 } : { xPercent: -70 }
      const borrao = direcao === 'sobe' || direcao === 'desce' ? { scaleY: 1.35 } : { scaleX: 1.45 }
      gsap.set(s, { opacity: 0 })
      t.fromTo(s, { ...de, ...borrao, opacity: 0, filter: 'blur(10px)' },
        { xPercent: 0, yPercent: 0, scaleX: 1, scaleY: 1, opacity: 1, filter: 'blur(0px)', duration: 0.5, ease: 'expo.out', immediateRender: false }, p.ini - 0.05)
    })
    if (atual.childNodes.length) linhas.push(atual)
    b.append(...linhas)
    sair(t, b, g, prox, g.ini)
  }
}

/** Texto elástico: nasce como um risco de luz horizontal e se comprime até a palavra (ease elástico). */
function elastico(palco: HTMLElement, t: T, g: Grupo, prox?: Grupo) {
  const b = bloco(palco, g)
  const k = Math.max(ki(g), 0)
  const larg = (g.caixa?.[2] ?? 960) - 40
  const antes = el('div', 'linha-peq')
  g.palavras.forEach((p, i) => { if (i !== k) antes.append(el('span', 'peq', p.t), document.createTextNode(' ')) })
  const grande = el('div', 'elastica', g.palavras[k].t.toUpperCase())
  grande.style.fontSize = `${Math.min(150, larg / Math.max(g.palavras[k].t.length * 0.62, 1))}px`
  b.append(antes, grande)
  gsap.set([antes, grande], { opacity: 0 })
  t.fromTo(antes, { opacity: 0, y: 10 }, { opacity: 1, y: 0, duration: 0.4, ease: 'power3.out', immediateRender: false }, g.ini)
  t.fromTo(grande, { opacity: 1, scaleX: 3.2, scaleY: 0.06, filter: 'blur(6px) brightness(3)' },
    { scaleX: 1, scaleY: 1, filter: 'blur(0px) brightness(1)', duration: 0.9, ease: 'elastic.out(1, 0.5)', immediateRender: false }, g.palavras[k].ini - 0.1)
  sair(t, b, g, prox, g.ini)
}

/** Entrada com deslocamento: linhas em escada (esquerda, centro, direita), cada uma vem desfocada na diagonal. */
function deslocamento(palco: HTMLElement, t: T, g: Grupo, prox?: Grupo) {
  const b = bloco(palco, g, 'escada')
  const k = ki(g)
  const larg = (g.caixa?.[2] ?? 960) - 40
  const partes: HTMLElement[] = []
  let atual = el('div', 'degrau')
  g.palavras.forEach((p, i) => {
    if (i === k) {
      if (atual.childNodes.length) partes.push(atual)
      const d = el('div', 'degrau')
      d.append(chaveEl(p, larg, 0.9))
      partes.push(d)
      atual = el('div', 'degrau')
    } else atual.append(el('span', 'peq-grande', p.t), document.createTextNode(' '))
  })
  if (atual.childNodes.length) partes.push(atual)
  partes.forEach((d, i) => {
    d.style.alignSelf = ['flex-start', 'center', 'flex-end'][i % 3]
    b.append(d)
    gsap.set(d, { opacity: 0 })
    const quando = g.ini + (i / partes.length) * Math.min(g.fim - g.ini, 1.2)
    t.fromTo(d, { opacity: 0, x: i % 2 ? 60 : -60, y: 30, filter: 'blur(14px)' },
      { opacity: 1, x: 0, y: 0, filter: 'blur(0px)', duration: 0.6, ease: 'power3.out', immediateRender: false }, quando)
  })
  sair(t, b, g, prox, g.ini)
}

// ---------------------------------------------------------------- presets de gancho

/** Impacto: a chave bate na tela (escala 2,4 → 1) com tremida curta e pulso de brilho. */
function impacto(palco: HTMLElement, t: T, g: Grupo, prox?: Grupo) {
  const b = bloco(palco, g)
  const k = Math.max(ki(g), 0)
  const larg = (g.caixa?.[2] ?? 960) - 40
  const antes = el('div', 'linha-peq'), depois = el('div', 'linha-peq')
  g.palavras.forEach((p, i) => { if (i !== k) (i < k ? antes : depois).append(el('span', 'peq', p.t), document.createTextNode(' ')) })
  const chave = chaveEl(g.palavras[k], larg, 1.15)
  b.append(antes, chave, depois)
  gsap.set([antes, depois, chave], { opacity: 0 })
  const tk = g.palavras[k].ini - 0.05
  t.fromTo(chave, { opacity: 0, scale: 2.4, filter: 'blur(16px)' }, { opacity: 1, scale: 1, filter: 'blur(0px)', duration: 0.38, ease: 'expo.out', immediateRender: false }, tk)
  const tremida = { v: 0 }
  t.to(tremida, { v: 1, duration: 0.35, ease: 'none', onUpdate: () => {
    const a = (1 - tremida.v) * 9
    gsap.set(b, { x: Math.sin(tremida.v * 60) * a, y: Math.cos(tremida.v * 47) * a * 0.6 })
  } }, tk + 0.3)
  t.fromTo(chave, { textShadow: '0 0 90px rgba(255,255,255,1)' }, { textShadow: '0 0 34px rgba(255,255,255,0.35)', duration: 0.8, ease: 'power2.out', immediateRender: false }, tk + 0.1)
  t.fromTo([antes, depois], { opacity: 0, y: 12 }, { opacity: 1, y: 0, duration: 0.4, ease: 'power3.out', stagger: 0.1, immediateRender: false }, tk + 0.25)
  sair(t, b, g, prox, tk + 0.4)
}

/** Revelação: uma linha fina varre a largura e revela o texto por máscara (wipe), chave em serifa. */
function revelacao(palco: HTMLElement, t: T, g: Grupo, prox?: Grupo) {
  const b = bloco(palco, g)
  const k = ki(g)
  const larg = (g.caixa?.[2] ?? 960) - 40
  const conteudo = el('div', 'revela')
  const antes = el('div', 'linha-peq'), depois = el('div', 'linha-peq')
  let chave: HTMLElement | null = null
  g.palavras.forEach((p, i) => {
    if (i === k) chave = chaveEl(p, larg)
    else (k < 0 || i < k ? antes : depois).append(el('span', 'peq', p.t), document.createTextNode(' '))
  })
  conteudo.append(antes)
  if (chave) conteudo.append(chave)
  conteudo.append(depois)
  const risco = el('div', 'risco-revela')
  b.append(conteudo, risco)
  const dur = Math.min(0.9, Math.max(g.fim - g.ini - 0.3, 0.4))
  gsap.set(conteudo, { clipPath: 'inset(0% 100% 0% 0%)' })
  gsap.set(risco, { opacity: 0 })
  t.to(conteudo, { clipPath: 'inset(0% 0% 0% 0%)', duration: dur, ease: 'power3.inOut' }, g.ini)
  t.fromTo(risco, { opacity: 1, left: '0%' }, { left: '100%', duration: dur, ease: 'power3.inOut', immediateRender: false }, g.ini)
  t.to(risco, { opacity: 0, duration: 0.2 }, g.ini + dur)
  sair(t, b, g, prox, g.ini + dur)
}

/** Glitch (monocromático): palavras grandes empilhadas com cópias fantasmas deslocadas que tremem e assentam. */
function glitch(palco: HTMLElement, t: T, g: Grupo, prox?: Grupo) {
  const b = bloco(palco, g, 'pilha')
  const larg = (g.caixa?.[2] ?? 960) - 40
  const palavras = g.palavras.filter((p) => p.t.length > 1).slice(0, 3)
  palavras.forEach((p) => {
    const linha = el('div', 'glitch-linha')
    const tam = Math.min(140, larg / Math.max(p.t.length * 0.62, 1))
    const fantasmas = [el('span', 'glitch-fantasma', p.t.toUpperCase()), el('span', 'glitch-fantasma', p.t.toUpperCase())]
    const principal = el('span', 'glitch-principal', p.t.toUpperCase())
    for (const f of [...fantasmas, principal]) f.style.fontSize = `${tam}px`
    linha.append(...fantasmas, principal)
    b.append(linha)
    gsap.set(linha, { opacity: 0 })
    t.set(linha, { opacity: 1 }, p.ini - 0.05)
    const q = { v: 0 }
    t.to(q, { v: 1, duration: 0.45, ease: 'none', onUpdate: () => {
      const a = (1 - q.v) * 26
      gsap.set(fantasmas[0], { x: Math.round(Math.sin(q.v * 40) * a), opacity: 0.5 * (1 - q.v) + 0.15 })
      gsap.set(fantasmas[1], { x: -Math.round(Math.cos(q.v * 33) * a), opacity: 0.4 * (1 - q.v) + 0.1 })
      gsap.set(principal, { clipPath: q.v < 0.6 ? `inset(${Math.round(Math.abs(Math.sin(q.v * 23)) * 40)}% 0 0 0)` : 'inset(0% 0 0 0)' })
    } }, p.ini - 0.05)
  })
  sair(t, b, g, prox, g.ini)
}

const PRESETS: Record<string, (palco: HTMLElement, t: T, g: Grupo, prox?: Grupo) => void> = {
  cinematico, maquina, sobe: desliza('sobe'), desce: desliza('desce'), esquerda: desliza('esquerda'),
  direita: desliza('direita'), elastico, deslocamento, impacto, revelacao, glitch
}

export function legenda(palco: HTMLElement, job: JobMotion, t: T) {
  const cobertos = job.cenas.filter((c) => c.cobreLegenda)
  job.grupos.forEach((g, gi) => {
    if (cobertos.some((c) => g.ini >= c.ini - 0.05 && g.ini < c.fim)) return
    const preset = PRESETS[g.preset ?? 'cinematico'] ?? cinematico
    preset(palco, t, g, job.grupos[gi + 1])
  })
}
