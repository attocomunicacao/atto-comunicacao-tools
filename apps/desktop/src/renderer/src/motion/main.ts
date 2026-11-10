/**
 * ATTO Motion — estilo "minimal premium" (referência: edição de talking head com texto cinematográfico).
 *
 * Contrato (igual ao HyperFrames): UMA timeline GSAP pausada; o renderizador chama `__seek(t)` e captura o quadro.
 * Nada depende do relógio, de timers ou de aleatório: cada quadro é função só do tempo (render determinístico).
 * Fundo transparente; o FFmpeg sobrepõe ao vídeo. Tudo branco; duas famílias: Inter (texto) e Playfair Display
 * itálico (palavra-chave).
 */
import '@fontsource/inter/400.css'
import '@fontsource/inter/500.css'
import '@fontsource/inter/800.css'
import '@fontsource/playfair-display/600-italic.css'
import '@fontsource/playfair-display/700-italic.css'
import gsap from 'gsap'
import * as icones from 'lucide-static'
import './motion.css'
import { cenaImagem3D } from './imagem3d'
import { legenda } from './legendas'
import type { Cena, JobMotion } from './tipos'

declare global {
  interface Window {
    __montar: (job: JobMotion) => Promise<void>
    __seek: (t: number) => Promise<void>
  }
}

const palco = document.getElementById('palco')!
let tl: gsap.core.Timeline | null = null
const desenhos: (() => void)[] = [] // cenas WebGL redesenhadas a cada quadro
const NS = 'http://www.w3.org/2000/svg'

const el = <K extends keyof HTMLElementTagNameMap>(tag: K, cls: string, txt?: string) => {
  const e = document.createElement(tag)
  e.className = cls
  if (txt !== undefined) e.textContent = txt
  return e
}
const svgEl = (tag: string, attrs: Record<string, string | number>) => {
  const e = document.createElementNS(NS, tag)
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, String(v))
  return e
}

/** Prepara traços SVG para o efeito "desenhar a linha". */
function tracos(raiz: Element): Element[] {
  const fs = [...raiz.querySelectorAll('path,line,circle,rect,polyline,polygon,ellipse')]
  fs.forEach((f) => {
    f.setAttribute('pathLength', '1')
    ;(f as SVGElement).style.strokeDasharray = '1'
    ;(f as SVGElement).style.strokeDashoffset = '1'
  })
  return fs
}

function icone(nome: string | undefined): string {
  const mapa = icones as unknown as Record<string, string>
  return mapa[nome ?? ''] ?? mapa['Sparkles']
}

// ---------------------------------------------------------------- cenas (sem cartão, flutuando sobre o vídeo)

/** Vinheta escura suave atrás da cena, para leitura sem caixa. */
function vinheta(t: gsap.core.Timeline, c: Cena, forte = false) {
  const v = el('div', forte ? 'vinheta forte' : 'vinheta')
  palco.appendChild(v)
  gsap.set(v, { opacity: 0 })
  t.to(v, { opacity: 1, duration: 0.5, ease: 'power2.out' }, c.ini)
  t.to(v, { opacity: 0, duration: 0.45, ease: 'power2.in' }, c.fim - 0.45)
}

function sair(t: gsap.core.Timeline, alvo: Element, c: Cena) {
  t.to(alvo, { opacity: 0, y: -30, filter: 'blur(14px)', duration: 0.45, ease: 'power2.in' }, c.fim - 0.45)
}

/** Linha + texto: uma linha fina se desenha, é interrompida pela frase e continua do outro lado. */
function cenaLinha(t: gsap.core.Timeline, c: Cena) {
  vinheta(t, c)
  const caixa = el('div', 'cena-linha')
  const svg = svgEl('svg', { viewBox: '0 0 1080 600', width: 1080, height: 600, class: 'linha-svg' })
  const esq = svgEl('path', { d: 'M -20 420 C 160 420, 200 300, 300 300' })
  const dir = svgEl('path', { d: 'M 780 300 C 880 300, 930 180, 1100 180' })
  const ponto = svgEl('circle', { cx: 1100, cy: 180, r: 7, class: 'ponto' })
  svg.append(esq, dir, ponto)
  const texto = el('div', 'linha-texto')
  const palavras = (c.texto ?? '').split(' ')
  palavras.forEach((p, i) => texto.append(el('span', i === palavras.length - 1 ? 'serif' : 'sans', p), document.createTextNode(' ')))
  caixa.append(svg, texto)
  palco.appendChild(caixa)
  gsap.set(caixa, { opacity: 0 })
  t.set(caixa, { opacity: 1 }, c.ini)
  const [a, b] = tracos(svg).filter((f) => f.tagName === 'path')
  gsap.set(ponto, { opacity: 0, scale: 0, transformOrigin: 'center' })
  t.to(a, { strokeDashoffset: 0, duration: 0.7, ease: 'power2.inOut' }, c.ini)
  t.fromTo(texto.children, { opacity: 0, y: 24, filter: 'blur(10px)' },
    { opacity: 1, y: 0, filter: 'blur(0px)', duration: 0.7, ease: 'expo.out', stagger: 0.09, immediateRender: false }, c.ini + 0.45)
  t.to(b, { strokeDashoffset: 0, duration: 0.7, ease: 'power2.inOut' }, c.ini + 0.9)
  t.to(ponto, { opacity: 1, scale: 1, duration: 0.4, ease: 'back.out(3)' }, c.ini + 1.5)
  // câmera acompanha a linha: leve deslocamento lateral de toda a cena
  t.fromTo(caixa, { x: 40 }, { x: -40, duration: c.fim - c.ini, ease: 'sine.inOut', immediateRender: false }, c.ini)
  sair(t, caixa, c)
}

/** Citação: tela escurecida com textura, aspas grandes e a frase escrita palavra por palavra. */
function cenaCitacao(t: gsap.core.Timeline, c: Cena) {
  const fundo = el('div', 'citacao-fundo')
  const caixa = el('div', 'cena-citacao')
  const abre = el('div', 'aspas', '“')
  const fecha = el('div', 'aspas fecha', '”')
  const frase = el('div', 'citacao-texto')
  const palavras = (c.texto ?? '').split(/\s+/).filter(Boolean)
  const longas = new Set([...palavras].sort((x, y) => y.length - x.length).slice(0, 2))
  palavras.forEach((p) => frase.append(el('span', longas.has(p) ? 'serif' : 'sans', p.toLowerCase()), document.createTextNode(' ')))
  caixa.append(abre, frase, fecha)
  palco.append(fundo, caixa)
  gsap.set([fundo, caixa], { opacity: 0 })
  const d = c.fim - c.ini
  t.to(fundo, { opacity: 1, duration: 0.4, ease: 'power2.out' }, c.ini)
  t.set(caixa, { opacity: 1 }, c.ini)
  t.fromTo([abre, fecha], { opacity: 0, scale: 1.6, filter: 'blur(20px)' },
    { opacity: 0.9, scale: 1, filter: 'blur(0px)', duration: 0.8, ease: 'expo.out', stagger: 0.12, immediateRender: false }, c.ini + 0.05)
  const passo = Math.min(0.22, (d * 0.75) / Math.max(palavras.length, 1))
  t.fromTo(frase.children, { opacity: 0, y: 18, filter: 'blur(10px)' },
    { opacity: 1, y: 0, filter: 'blur(0px)', duration: 0.5, ease: 'power3.out', stagger: passo, immediateRender: false }, c.ini + 0.25)
  t.fromTo(caixa, { scale: 1 }, { scale: 1.04, duration: d, ease: 'none', immediateRender: false }, c.ini)
  t.to([fundo, caixa], { opacity: 0, filter: 'blur(16px)', duration: 0.35, ease: 'power2.in' }, c.fim - 0.35)
}

/** Gráfico/estatística: grade fina com brilho, linha que sobe e uma bolinha percorrendo; número que conta. */
function cenaGrafico(t: gsap.core.Timeline, c: Cena) {
  vinheta(t, c, true)
  const caixa = el('div', 'cena-grafico')
  const W = 820, H = 420
  const svg = svgEl('svg', { viewBox: `0 0 ${W} ${H}`, width: W, height: H, class: 'grafico-svg' })
  for (let x = 0; x <= W; x += 82) svg.append(svgEl('line', { x1: x, y1: 0, x2: x, y2: H, class: 'grade' }))
  for (let y = 0; y <= H; y += 84) svg.append(svgEl('line', { x1: 0, y1: y, x2: W, y2: y, class: 'grade' }))
  const desce = c.tipo === 'comparacao' && Number.parseFloat(c.depois ?? '0') < Number.parseFloat(c.antes ?? '0')
  const d = desce ? `M 30 90 C 260 90, 420 200, 560 260 S 760 330, 790 340` : `M 30 360 C 220 350, 380 300, 520 210 S 720 70, 790 60`
  const curva = svgEl('path', { d, class: 'curva' })
  const bola = svgEl('circle', { r: 13, class: 'bola' })
  svg.append(curva, bola)
  const titulo = el('div', 'grafico-numero', c.tipo === 'comparacao' ? '' : '0')
  if (c.tipo === 'comparacao') {
    titulo.append(el('span', 'antes', c.antes ?? ''), el('span', 'seta', '→'), el('span', 'depois', c.depois ?? ''))
  }
  const rotulo = el('div', 'grafico-rotulo', (c.texto ?? '').toLowerCase())
  caixa.append(titulo, rotulo, svg)
  palco.appendChild(caixa)
  gsap.set(caixa, { opacity: 0 })
  t.fromTo(caixa, { opacity: 0, y: 40, filter: 'blur(14px)' },
    { opacity: 1, y: 0, filter: 'blur(0px)', duration: 0.6, ease: 'expo.out', immediateRender: false }, c.ini)
  const grade = [...svg.querySelectorAll('.grade')]
  t.fromTo(grade, { opacity: 0 }, { opacity: 1, duration: 0.5, stagger: 0.02, ease: 'power1.out', immediateRender: false }, c.ini + 0.1)
  const [linha] = tracos(curva.parentElement!).filter((f) => f === curva)
  const comp = (curva as SVGPathElement).getTotalLength()
  const prog = { p: 0 }
  const moverBola = () => {
    const pt = (curva as SVGPathElement).getPointAtLength(prog.p * comp)
    bola.setAttribute('cx', String(pt.x))
    bola.setAttribute('cy', String(pt.y))
  }
  moverBola()
  t.to(linha, { strokeDashoffset: 0, duration: 1.4, ease: 'power2.inOut' }, c.ini + 0.35)
  t.to(prog, { p: 1, duration: 1.4, ease: 'power2.inOut', onUpdate: moverBola }, c.ini + 0.35)
  if (c.tipo === 'numero') {
    const cont = { v: 0 }
    const valor = c.valor ?? 0
    const casas = Number.isInteger(valor) ? 0 : 1
    t.to(cont, {
      v: valor, duration: 1.4, ease: 'power2.inOut',
      onUpdate: () => { titulo.textContent = cont.v.toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas }) + (c.sufixo ?? '') }
    }, c.ini + 0.35)
  } else {
    const [a, s, b] = [...titulo.children]
    t.fromTo(a, { opacity: 0, x: -30 }, { opacity: 1, x: 0, duration: 0.5, ease: 'expo.out', immediateRender: false }, c.ini + 0.3)
    t.fromTo(s, { opacity: 0, x: -20 }, { opacity: 1, x: 0, duration: 0.4, ease: 'power2.out', immediateRender: false }, c.ini + 0.8)
    t.fromTo(b, { opacity: 0, scale: 0.6, filter: 'blur(10px)' }, { opacity: 1, scale: 1, filter: 'blur(0px)', duration: 0.7, ease: 'back.out(2)', immediateRender: false }, c.ini + 1.3)
  }
  t.fromTo(rotulo, { opacity: 0, y: 12 }, { opacity: 1, y: 0, duration: 0.5, ease: 'power3.out', immediateRender: false }, c.ini + 0.6)
  sair(t, caixa, c)
}

/** Ícone + texto: ícone de traço que se desenha, órbita fina com um ponto girando, palavra em serifa. */
function cenaIcone(t: gsap.core.Timeline, c: Cena) {
  vinheta(t, c)
  const caixa = el('div', 'cena-icone')
  const orbita = svgEl('svg', { viewBox: '0 0 400 400', width: 400, height: 400, class: 'orbita' })
  const anel = svgEl('circle', { cx: 200, cy: 200, r: 170 })
  const ponto = svgEl('circle', { cx: 200, cy: 30, r: 7, class: 'ponto' })
  orbita.append(anel, ponto)
  const ic = el('div', 'icone')
  ic.innerHTML = icone(c.icone)
  const rotulo = el('div', 'icone-rotulo')
  const ps = (c.texto ?? '').toLowerCase().split(' ')
  ps.forEach((p, i) => rotulo.append(el('span', i === ps.length - 1 ? 'serif' : 'sans', p), document.createTextNode(' ')))
  caixa.append(orbita, ic, rotulo)
  palco.appendChild(caixa)
  gsap.set(caixa, { opacity: 0 })
  t.set(caixa, { opacity: 1 }, c.ini)
  const [linhaAnel] = tracos(orbita).filter((f) => f === anel)
  gsap.set(ponto, { opacity: 0 })
  t.to(linhaAnel, { strokeDashoffset: 0, duration: 0.9, ease: 'power2.inOut' }, c.ini)
  t.to(ponto, { opacity: 1, duration: 0.2 }, c.ini + 0.8)
  t.fromTo(orbita, { rotate: -40 }, { rotate: 200, duration: c.fim - c.ini, ease: 'none', immediateRender: false }, c.ini)
  const svgIc = ic.querySelector('svg')!
  t.to(tracos(svgIc), { strokeDashoffset: 0, duration: 1.0, ease: 'power2.inOut', stagger: 0.08 }, c.ini + 0.2)
  t.fromTo(svgIc, { scale: 0.8, filter: 'blur(8px)' }, { scale: 1, filter: 'blur(0px)', duration: 1, ease: 'expo.out', immediateRender: false }, c.ini + 0.2)
  t.fromTo(rotulo.children, { opacity: 0, y: 20, filter: 'blur(10px)' },
    { opacity: 1, y: 0, filter: 'blur(0px)', duration: 0.6, ease: 'expo.out', stagger: 0.1, immediateRender: false }, c.ini + 0.55)
  sair(t, caixa, c)
}

/** Pintura em domínio público: tela cheia, textura de papel, bordas escuras e desfocadas, câmera deslizando. */
function cenaPintura(t: gsap.core.Timeline, c: Cena) {
  const caixa = el('div', 'cena-pintura')
  const img = el('div', 'pintura-img')
  img.style.backgroundImage = `url("${c.img}")`
  const papel = el('div', 'papel')
  const borda = el('div', 'pintura-borda')
  const texto = el('div', 'pintura-texto')
  const ps = (c.texto ?? '').toLowerCase().split(' ')
  ps.forEach((p, i) => texto.append(el('span', i === ps.length - 1 ? 'serif' : 'sans', p), document.createTextNode(' ')))
  const credito = el('div', 'pintura-credito', c.credito ?? '')
  caixa.append(img, papel, borda, texto, credito)
  palco.appendChild(caixa)
  gsap.set(caixa, { opacity: 0 })
  const d = c.fim - c.ini
  // entrada: "camera slide" — desliza da direita, desfocada, e assenta
  t.fromTo(caixa, { opacity: 0, x: 260, filter: 'blur(24px)' },
    { opacity: 1, x: 0, filter: 'blur(0px)', duration: 0.7, ease: 'expo.out', immediateRender: false }, c.ini)
  t.fromTo(img, { scale: 1.18, x: 40 }, { scale: 1.06, x: -40, duration: d, ease: 'sine.inOut', immediateRender: false }, c.ini)
  t.fromTo(texto.children, { opacity: 0, y: 26, filter: 'blur(12px)' },
    { opacity: 1, y: 0, filter: 'blur(0px)', duration: 0.7, ease: 'expo.out', stagger: 0.1, immediateRender: false }, c.ini + 0.45)
  t.to(caixa, { opacity: 0, x: -200, filter: 'blur(20px)', duration: 0.5, ease: 'power2.in' }, c.fim - 0.5)
}

/** Tamanho de projeto de cada cena (px); ela é reduzida para caber na caixa livre de rostos. */
const PROJETO: Record<string, [number, number]> = {
  destaque: [1080, 600], numero: [820, 700], comparacao: [820, 700], icone: [1080, 640], documento: [860, 640]
}

/** Coloca o elemento da cena dentro da caixa livre (sem cobrir rosto), mantendo a proporção. */
function encaixar(raiz: HTMLElement, c: Cena) {
  const [dw, dh] = PROJETO[c.tipo] ?? [1080, 600]
  const [x, y, w, h] = c.caixa ?? [60, 150, 960, 520]
  const s = Math.min(w / dw, h / dh, c.telaCheia ? 1.25 : 1)
  const env = el('div', 'encaixe')
  Object.assign(env.style, {
    left: `${x + (w - dw * s) / 2}px`, top: `${y + (h - dh * s) / 2}px`, width: `${dw}px`, height: `${dh}px`,
    transform: `scale(${s})`
  })
  raiz.replaceWith(env)
  env.appendChild(raiz)
  Object.assign(raiz.style, { left: '0px', top: '0px', right: 'auto' })
}

/** Documento (estilo Vox): recorte de matéria em papel que flutua, câmera aproxima e marca-texto na manchete. */
function cenaDocumento(t: gsap.core.Timeline, c: Cena) {
  vinheta(t, c, true)
  const caixa = el('div', 'cena-documento')
  const papel = el('div', 'doc-papel')
  const chapeu = el('div', 'doc-chapeu', (c.rotulo ?? '').toUpperCase())
  const manchete = el('div', 'doc-manchete')
  const alvo = (c.destaque ?? '').toLowerCase().split(/\s+/).filter(Boolean)
  const marcas: HTMLElement[] = []
  ;(c.texto ?? '').split(/\s+/).forEach((p) => {
    const limpo = p.toLowerCase().replace(/[.,;:!?…]/g, '')
    if (alvo.includes(limpo)) {
      const m = el('span', 'doc-marca')
      const fundo = el('span', 'doc-marca-fundo')
      m.append(fundo, document.createTextNode(p))
      manchete.append(m, document.createTextNode(' '))
      marcas.push(fundo)
    } else manchete.append(document.createTextNode(p + ' '))
  })
  const corpo = el('div', 'doc-corpo')
  for (let i = 0; i < 6; i++) {
    const l = el('div', 'doc-linha')
    l.style.width = `${[96, 100, 88, 100, 92, 64][i]}%`
    corpo.append(l)
  }
  papel.append(chapeu, el('div', 'doc-fio'), manchete, corpo, el('div', 'papel'))
  caixa.append(papel)
  palco.appendChild(caixa)
  const d = c.fim - c.ini
  gsap.set(caixa, { opacity: 0 })
  // entra flutuando (leve rotação e perspectiva), a câmera aproxima devagar, o marca-texto passa na manchete
  t.fromTo(caixa, { opacity: 0, y: 90, rotate: -7, rotateX: 18, scale: 0.9, filter: 'blur(14px)' },
    { opacity: 1, y: 0, rotate: -2.5, rotateX: 0, scale: 0.96, filter: 'blur(0px)', duration: 0.9, ease: 'expo.out', immediateRender: false }, c.ini)
  t.to(caixa, { rotate: -1, scale: 1.05, y: -14, duration: Math.max(d - 1.3, 0.5), ease: 'sine.inOut' }, c.ini + 0.9)
  gsap.set(marcas, { scaleX: 0, transformOrigin: 'left center' })
  t.to(marcas, { scaleX: 1, duration: 0.55, ease: 'power2.inOut', stagger: 0.12 }, c.ini + 0.8)
  t.fromTo(corpo.children, { opacity: 0 }, { opacity: 1, duration: 0.3, stagger: 0.05, immediateRender: false }, c.ini + 0.35)
  t.to(caixa, { opacity: 0, y: -40, rotate: 1.5, filter: 'blur(14px)', duration: 0.45, ease: 'power2.in' }, c.fim - 0.45)
}

/** Fundo de "corte" em tela cheia (escuro com textura de papel) para cenas que não cabem em volta do rosto. */
function fundoCheio(t: gsap.core.Timeline, c: Cena) {
  const f = el('div', 'fundo-cheio')
  palco.appendChild(f)
  gsap.set(f, { opacity: 0 })
  t.fromTo(f, { opacity: 0, scale: 1.08, filter: 'blur(20px)' }, { opacity: 1, scale: 1, filter: 'blur(0px)', duration: 0.5, ease: 'power3.out', immediateRender: false }, c.ini - 0.1)
  t.to(f, { opacity: 0, filter: 'blur(16px)', duration: 0.45, ease: 'power2.in' }, c.fim - 0.4)
}

/**
 * Conceito (v0.7, narração ilustrada — videoplayback (3).mp4): a frase vira uma ilustração em tela cheia feita só de
 * motion (sem foto): fundo texturizado escuro, um ícone grande desenhado traço a traço dentro de um anel que gira,
 * a frase falada em cima (pequena) e a palavra-chave embaixo em serifa. Entra e sai em desfoque; a câmera aproxima.
 */
function cenaConceito(t: gsap.core.Timeline, c: Cena) {
  const fundo = el('div', 'citacao-fundo conceito-fundo')
  const caixa = el('div', 'cena-conceito')
  const sobre = el('div', 'conceito-sobre')
  const palavras = (c.texto ?? '').split(/\s+/).filter(Boolean)
  palavras.forEach((p) => sobre.append(el('span', 'sans', p.toLowerCase()), document.createTextNode(' ')))
  const arte = el('div', 'conceito-arte')
  const anel = svgEl('svg', { viewBox: '0 0 600 600', width: 600, height: 600, class: 'conceito-anel' })
  const circ = svgEl('circle', { cx: 300, cy: 300, r: 270 })
  const circ2 = svgEl('circle', { cx: 300, cy: 300, r: 228, class: 'fino' })
  const ponto = svgEl('circle', { cx: 300, cy: 30, r: 9, class: 'ponto' })
  anel.append(circ, circ2, ponto)
  const ic = el('div', 'conceito-icone')
  ic.innerHTML = icone(c.icone)
  arte.append(anel, ic)
  const chave = el('div', 'conceito-chave', (c.destaque || palavras[palavras.length - 1] || '').toLowerCase())
  caixa.append(sobre, arte, chave)
  palco.append(fundo, caixa)
  gsap.set([fundo, caixa, ponto], { opacity: 0 })
  const d = c.fim - c.ini
  t.fromTo(fundo, { opacity: 0 }, { opacity: 1, duration: 0.35, ease: 'power2.out', immediateRender: false }, c.ini)
  t.fromTo(caixa, { opacity: 0, scale: 1.08, filter: 'blur(18px)' },
    { opacity: 1, scale: 1, filter: 'blur(0px)', duration: 0.55, ease: 'expo.out', immediateRender: false }, c.ini)
  t.to(tracos(anel), { strokeDashoffset: 0, duration: 1.0, ease: 'power2.inOut', stagger: 0.12 }, c.ini + 0.1)
  t.to(ponto, { opacity: 1, duration: 0.2 }, c.ini + 0.9)
  t.fromTo(anel, { rotate: -30 }, { rotate: 120, duration: d, ease: 'none', immediateRender: false }, c.ini)
  const svgIc = ic.querySelector('svg')
  if (svgIc) {
    t.to(tracos(svgIc), { strokeDashoffset: 0, duration: 1.1, ease: 'power2.inOut', stagger: 0.08 }, c.ini + 0.25)
    t.fromTo(svgIc, { scale: 0.85 }, { scale: 1, duration: 1.2, ease: 'expo.out', immediateRender: false }, c.ini + 0.25)
  }
  const passo = Math.min(0.16, (d * 0.4) / Math.max(palavras.length, 1))
  t.fromTo(sobre.children, { opacity: 0, y: 16, filter: 'blur(8px)' },
    { opacity: 1, y: 0, filter: 'blur(0px)', duration: 0.35, ease: 'power3.out', stagger: passo, immediateRender: false }, c.ini + 0.15)
  t.fromTo(chave, { opacity: 0, letterSpacing: '0.08em', filter: 'blur(14px)' },
    { opacity: 1, letterSpacing: '0em', filter: 'blur(0px)', duration: 0.6, ease: 'power2.out', immediateRender: false }, c.ini + 0.55)
  t.fromTo(caixa, { y: 0 }, { y: -18, duration: d, ease: 'none', immediateRender: false }, c.ini)
  t.to([fundo, caixa], { opacity: 0, filter: 'blur(16px)', duration: 0.3, ease: 'power2.in' }, c.fim - 0.3)
}

async function cenas(job: JobMotion, t: gsap.core.Timeline) {
  for (const c of job.cenas) {
    if (c.telaCheia) fundoCheio(t, c)
    const antes = new Set(palco.children)
    if (c.tipo === 'imagem' && c.img) await cenaImagem3D(palco, t, c, desenhos)
    else if (c.tipo === 'citacao') cenaCitacao(t, c)
    else if (c.tipo === 'conceito') cenaConceito(t, c)
    else if (c.tipo === 'pintura' && c.img) cenaPintura(t, c)
    else if (c.tipo === 'numero' || c.tipo === 'comparacao') cenaGrafico(t, c)
    else if (c.tipo === 'icone') cenaIcone(t, c)
    else if (c.tipo === 'documento') cenaDocumento(t, c)
    else cenaLinha(t, c)
    // cenas que não são tela cheia vão para a caixa livre de rostos (mapa de espaço)
    if (c.caixa && !['imagem', 'pintura', 'citacao', 'conceito'].includes(c.tipo)) {
      for (const novo of [...palco.children].filter((x) => !antes.has(x)) as HTMLElement[]) {
        if (novo.classList.contains('fundo-cheio')) continue
        if (novo.classList.contains('vinheta')) {
          if (c.telaCheia) { novo.remove(); continue }
          const [x, y, w, h] = c.caixa
          novo.style.background = `radial-gradient(ellipse ${w * 0.75}px ${h * 0.9}px at ${x + w / 2}px ${y + h / 2}px, rgba(0,0,0,0.6), rgba(0,0,0,0) 100%)`
        } else encaixar(novo, c)
      }
    }
  }
}

// ---------------------------------------------------------------- transições

/** Fim do cold open: faixa de luz atravessa a tela na diagonal, com flash e desfoque. */
function transicoes(job: JobMotion, t: gsap.core.Timeline) {
  for (const tr of job.transicoes ?? []) {
    const faixa = el('div', 'luz')
    const flash = el('div', 'flash')
    palco.append(faixa, flash)
    gsap.set([faixa, flash], { opacity: 0 })
    t.fromTo(faixa, { opacity: 1, xPercent: -120 }, { xPercent: 120, duration: 0.55, ease: 'power2.inOut', immediateRender: false }, tr - 0.3)
    t.set(faixa, { opacity: 0 }, tr + 0.26)
    t.fromTo(flash, { opacity: 0 }, { opacity: 0.7, duration: 0.1, ease: 'power1.out', immediateRender: false }, tr - 0.1)
    t.to(flash, { opacity: 0, duration: 0.4, ease: 'power2.out' }, tr)
  }
}

window.__montar = async (job: JobMotion) => {
  palco.innerHTML = ''
  desenhos.length = 0
  tl = gsap.timeline({ paused: true })
  await cenas(job, tl)
  legenda(palco, job, tl)
  tl.set({}, {}, job.duracao)
  await document.fonts.ready
}

window.__seek = async (t: number) => {
  tl?.seek(t, false)
  for (const d of desenhos) d()
  await new Promise((ok) => requestAnimationFrame(() => requestAnimationFrame(ok)))
}
