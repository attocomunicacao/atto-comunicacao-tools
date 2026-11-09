/**
 * ATTO Motion: camada de animação dos cortes (legenda + ilustrações), renderizada quadro a quadro.
 *
 * Mesmo contrato do HyperFrames: uma timeline GSAP PAUSADA; o renderizador chama `__seek(t)` e captura o quadro.
 * Nada depende do relógio (sem Date.now, timers ou aleatório): cada quadro é função só do tempo, então o render é
 * determinístico e sempre igual. Fundo transparente: o resultado é sobreposto ao vídeo pelo FFmpeg.
 */
import gsap from 'gsap'
import * as icones from 'lucide-static'
import './motion.css'
import type { Cena, JobMotion } from './tipos'

declare global {
  interface Window {
    __montar: (job: JobMotion) => Promise<void>
    __seek: (t: number) => Promise<void>
  }
}

const palco = document.getElementById('palco')!
let tl: gsap.core.Timeline | null = null

const el = <K extends keyof HTMLElementTagNameMap>(tag: K, cls: string, txt?: string) => {
  const e = document.createElement(tag)
  e.className = cls
  if (txt !== undefined) e.textContent = txt
  return e
}

function fontes(dir: string | undefined) {
  const url = (f: string) => (dir ? `url("file:///${dir.replace(/\\/g, '/')}/${f}")` : '')
  const css = [
    ['400', 'Lato-Regular.ttf', 'Lato'],
    ['700', 'Lato-Bold.ttf', 'Lato Bold'],
    ['900', 'Lato-Black.ttf', 'Lato Black']
  ]
    .map(([peso, arq, local]) => `@font-face{font-family:"AttoLato";font-weight:${peso};src:local("${local}")${dir ? `,${url(arq)}` : ''};}`)
    .join('\n')
  const s = document.createElement('style')
  s.textContent = css
  document.head.appendChild(s)
}

/** Legenda: uma palavra por vez, motion de entrada (desfoque -> nítido, y -100 -> 0) e saída cruzada. */
function legenda(job: JobMotion, t: gsap.core.Timeline) {
  const camada = el('div', 'legenda')
  palco.appendChild(camada)
  job.palavras.forEach((p, i) => {
    const w = el('div', 'palavra' + (p.enfase ? ' enfase' : ''), p.t)
    camada.appendChild(w)
    const prox = job.palavras[i + 1]
    const fim = prox ? prox.ini + 0.08 : Math.min(p.fim + 0.5, job.duracao)
    gsap.set(w, { opacity: 0 })
    const saida = prox ? 0.18 : 0
    // a entrada se ajusta ao tempo da palavra: nunca termina depois que a saída começa
    const entrada = Math.max(0.16, Math.min(0.55, fim - saida - p.ini))
    // entrada: nasce desfocada, 100 px acima e menor; assenta com easing exponencial
    t.fromTo(w, { y: -100, opacity: 0, scale: p.enfase ? 0.75 : 0.9, filter: 'blur(14px)' },
      { y: 0, opacity: 1, scale: p.enfase ? 1.14 : 1, filter: 'blur(0px)', duration: entrada, ease: 'expo.out', immediateRender: false }, p.ini)
    // respiração: deriva sutil enquanto está na tela (a palavra nunca fica "congelada")
    const parada = fim - saida - (p.ini + entrada)
    if (parada > 0.05) t.to(w, { y: -6, duration: parada, ease: 'sine.inOut' }, p.ini + entrada)
    // saída: desfoca, desce e some enquanto a próxima entra
    if (prox) t.to(w, { y: '+=18', opacity: 0, filter: 'blur(9px)', scale: 0.96, duration: saida, ease: 'power2.in' }, p.ini + entrada + Math.max(parada, 0))
  })
}

function icone(nome: string | undefined): string {
  const mapa = icones as unknown as Record<string, string>
  return mapa[nome ?? ''] ?? mapa['Sparkles']
}

/** Desenha os traços do ícone (efeito "line draw"). */
function prepararTracos(svg: SVGElement) {
  svg.querySelectorAll('path,line,circle,rect,polyline,polygon,ellipse').forEach((f) => {
    f.setAttribute('pathLength', '1')
    ;(f as SVGElement).style.strokeDasharray = '1'
    ;(f as SVGElement).style.strokeDashoffset = '1'
  })
}

function cartao(c: Cena): HTMLElement {
  const card = el('div', `cena cena-${c.tipo}`)
  if (c.tipo === 'numero') {
    card.append(el('div', 'numero', '0'), el('div', 'rotulo', c.texto ?? ''), el('div', 'traco'))
  } else if (c.tipo === 'comparacao') {
    const linha = el('div', 'comparacao')
    const seta = el('div', 'seta')
    seta.innerHTML = icone('ArrowRight')
    linha.append(el('div', 'antes', c.antes ?? ''), seta, el('div', 'depois', c.depois ?? ''))
    card.append(linha, el('div', 'rotulo', c.texto ?? ''))
  } else if (c.tipo === 'icone') {
    const ic = el('div', 'icone')
    ic.innerHTML = icone(c.icone)
    card.append(ic, el('div', 'rotulo', c.texto ?? ''))
  } else {
    const frase = el('div', 'destaque')
    ;(c.texto ?? '').split(' ').forEach((pal) => frase.append(el('span', 'pal', pal), document.createTextNode(' ')))
    card.append(frase, el('div', 'traco'))
  }
  return card
}

/** Ilustrações: cartões animados que entram no ritmo da fala (números, comparações, ícones, frases-chave). */
function cenas(job: JobMotion, t: gsap.core.Timeline) {
  for (const c of job.cenas) {
    const card = cartao(c)
    palco.appendChild(card)
    gsap.set(card, { opacity: 0 })
    const d = Math.max(c.fim - c.ini, 1.2)
    t.fromTo(card, { opacity: 0, y: 70, scale: 0.94, filter: 'blur(16px)' },
      { opacity: 1, y: 0, scale: 1, filter: 'blur(0px)', duration: 0.7, ease: 'expo.out' }, c.ini)
    const traco = card.querySelector('.traco')
    if (traco) t.fromTo(traco, { scaleX: 0 }, { scaleX: 1, duration: 0.8, ease: 'power3.inOut' }, c.ini + 0.25)
    if (c.tipo === 'numero') {
      const alvo = card.querySelector('.numero')!
      const contador = { v: 0 }
      const valor = c.valor ?? 0
      const casas = Number.isInteger(valor) ? 0 : 1
      const sufixo = c.sufixo ?? ''
      t.to(contador, {
        v: valor, duration: Math.min(1.4, d * 0.6), ease: 'power3.out',
        onUpdate: () => { alvo.textContent = contador.v.toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas }) + sufixo }
      }, c.ini + 0.1)
      t.fromTo(alvo, { scale: 0.8 }, { scale: 1, duration: 0.9, ease: 'back.out(2)' }, c.ini + 0.1)
    }
    if (c.tipo === 'icone') {
      const svg = card.querySelector('svg')!
      prepararTracos(svg)
      t.to(svg.querySelectorAll('path,line,circle,rect,polyline,polygon,ellipse'),
        { strokeDashoffset: 0, duration: 0.9, ease: 'power2.inOut', stagger: 0.08 }, c.ini + 0.15)
      t.fromTo(svg, { rotate: -8, scale: 0.85 }, { rotate: 0, scale: 1, duration: 1, ease: 'elastic.out(1, 0.6)' }, c.ini + 0.1)
    }
    if (c.tipo === 'comparacao') {
      const [a, s, b] = ['.antes', '.seta svg', '.depois'].map((q) => card.querySelector(q)!)
      prepararTracos(s as SVGElement)
      t.fromTo(a, { x: -40, opacity: 0 }, { x: 0, opacity: 1, duration: 0.5, ease: 'expo.out' }, c.ini + 0.15)
      t.to(s.querySelectorAll('path,line,polyline'), { strokeDashoffset: 0, duration: 0.5, ease: 'power2.inOut' }, c.ini + 0.45)
      t.fromTo(b, { scale: 0.6, opacity: 0 }, { scale: 1, opacity: 1, duration: 0.7, ease: 'back.out(2.2)' }, c.ini + 0.8)
    }
    if (c.tipo === 'destaque') {
      t.fromTo(card.querySelectorAll('.pal'), { y: 40, opacity: 0, filter: 'blur(10px)' },
        { y: 0, opacity: 1, filter: 'blur(0px)', duration: 0.6, ease: 'expo.out', stagger: 0.07 }, c.ini + 0.1)
    }
    // flutuação lenta enquanto está na tela
    t.to(card, { y: -10, duration: Math.max(d - 1.1, 0.3), ease: 'sine.inOut' }, c.ini + 0.7)
    t.to(card, { opacity: 0, y: -40, filter: 'blur(14px)', scale: 0.97, duration: 0.4, ease: 'power2.in' }, c.ini + d - 0.4)
  }
}

/** Transições: flash suave nos cortes internos (ex.: fim do gancho em "cold open"). */
function transicoes(job: JobMotion, t: gsap.core.Timeline) {
  for (const tr of job.transicoes ?? []) {
    const f = el('div', 'flash')
    palco.appendChild(f)
    t.fromTo(f, { opacity: 0 }, { opacity: 0.85, duration: 0.08, ease: 'power1.out' }, tr - 0.08)
    t.to(f, { opacity: 0, duration: 0.3, ease: 'power2.out' }, tr)
  }
}

window.__montar = async (job: JobMotion) => {
  fontes(job.fontes)
  palco.innerHTML = ''
  tl = gsap.timeline({ paused: true })
  cenas(job, tl)
  legenda(job, tl)
  transicoes(job, tl)
  tl.set({}, {}, job.duracao) // a timeline cobre o corte inteiro
  await document.fonts.ready
}

window.__seek = async (t: number) => {
  tl?.seek(t, false)
  await new Promise((ok) => requestAnimationFrame(() => requestAnimationFrame(ok)))
}
