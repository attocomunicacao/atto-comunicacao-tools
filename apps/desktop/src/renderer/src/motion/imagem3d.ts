/**
 * Cena de imagem com efeito 3D (2.5D): a foto e o seu mapa de profundidade (Depth Anything V2) viram texturas
 * WebGL; o shader desloca cada pixel conforme a profundidade enquanto a "câmera" avança e desliza (parallax).
 * Entrada: dolly-in de longe, desfocada; permanência: deriva lenta; saída: avança através da imagem e some.
 * Determinístico: o desenho depende só do estado animado pela timeline (zoom, deslocamento, força).
 */
import gsap from 'gsap'
import type { Cena } from './tipos'

const VERT = `attribute vec2 p; varying vec2 uv; void main(){ uv = p * 0.5 + 0.5; uv.y = 1.0 - uv.y; gl_Position = vec4(p, 0.0, 1.0); }`
const FRAG = `precision highp float;
varying vec2 uv;
uniform sampler2D cor; uniform sampler2D prof;
uniform vec2 escala; uniform float zoom; uniform vec2 desloc; uniform float forca;
void main(){
  vec2 c = (uv - 0.5) / zoom;
  vec2 base = c * escala + 0.5;
  vec2 q = base;
  for (int i = 0; i < 3; i++) { float d = texture2D(prof, q).r; q = base + desloc * (d - 0.35) * forca; }
  vec3 col = texture2D(cor, clamp(q, 0.001, 0.999)).rgb;
  float l = dot(col, vec3(0.299, 0.587, 0.114));
  col = mix(col, vec3(l) * vec3(1.06, 1.0, 0.9), 0.25);
  col = (col - 0.5) * 1.08 + 0.5;
  float v = smoothstep(0.95, 0.25, length((uv - 0.5) * vec2(1.0, 0.8)));
  gl_FragColor = vec4(col * mix(0.35, 1.0, v), 1.0);
}`

function carregar(src: string): Promise<HTMLImageElement> {
  return new Promise((ok, falha) => {
    const i = new Image()
    i.onload = () => ok(i)
    i.onerror = falha
    i.src = src
  })
}

export async function cenaImagem3D(palco: HTMLElement, t: gsap.core.Timeline, c: Cena, desenhos: (() => void)[]) {
  const caixa = document.createElement('div')
  caixa.className = 'cena-imagem'
  const canvas = document.createElement('canvas')
  canvas.width = 1080
  canvas.height = 1920
  const papel = document.createElement('div')
  papel.className = 'papel'
  caixa.append(canvas, papel)
  palco.appendChild(caixa)

  const gl = canvas.getContext('webgl', { preserveDrawingBuffer: true, premultipliedAlpha: false, antialias: true })
  const [img, prof] = await Promise.all([carregar(c.img!), c.prof ? carregar(c.prof) : Promise.resolve(null)])
  const estado = { zoom: 1.5, dx: 0.07, dy: 0.03, forca: 0 }
  let desenhar = () => {}
  if (gl) {
    const sh = (tipo: number, src: string) => {
      const s = gl.createShader(tipo)!
      gl.shaderSource(s, src)
      gl.compileShader(s)
      return s
    }
    const prog = gl.createProgram()!
    gl.attachShader(prog, sh(gl.VERTEX_SHADER, VERT))
    gl.attachShader(prog, sh(gl.FRAGMENT_SHADER, FRAG))
    gl.linkProgram(prog)
    gl.useProgram(prog)
    gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer())
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW)
    const loc = gl.getAttribLocation(prog, 'p')
    gl.enableVertexAttribArray(loc)
    gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0)
    const textura = (unidade: number, fonte: TexImageSource) => {
      gl.activeTexture(gl.TEXTURE0 + unidade)
      gl.bindTexture(gl.TEXTURE_2D, gl.createTexture())
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR)
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR)
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE)
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE)
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, fonte)
    }
    textura(0, img)
    if (prof) textura(1, prof)
    else {
      const vazio = document.createElement('canvas')
      vazio.width = vazio.height = 2
      textura(1, vazio)
    }
    gl.uniform1i(gl.getUniformLocation(prog, 'cor'), 0)
    gl.uniform1i(gl.getUniformLocation(prog, 'prof'), 1)
    const ar = img.naturalWidth / img.naturalHeight
    const alvo = 1080 / 1920
    gl.uniform2f(gl.getUniformLocation(prog, 'escala'), ar > alvo ? alvo / ar : 1, ar > alvo ? 1 : ar / alvo)
    const uZoom = gl.getUniformLocation(prog, 'zoom')
    const uDes = gl.getUniformLocation(prog, 'desloc')
    const uF = gl.getUniformLocation(prog, 'forca')
    desenhar = () => {
      gl.viewport(0, 0, 1080, 1920)
      gl.uniform1f(uZoom, estado.zoom)
      gl.uniform2f(uDes, estado.dx, estado.dy)
      gl.uniform1f(uF, prof ? estado.forca : 0)
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4)
    }
  } else {
    const ctx = canvas.getContext('2d')!
    desenhar = () => {
      const ar = img.naturalWidth / img.naturalHeight
      const w = Math.max(1920 * ar, 1080) * estado.zoom
      const h = w / ar
      ctx.clearRect(0, 0, 1080, 1920)
      ctx.drawImage(img, (1080 - w) / 2 - estado.dx * 400, (1920 - h) / 2, w, h)
    }
  }
  desenhos.push(desenhar)

  const texto = document.createElement('div')
  texto.className = 'imagem-texto'
  const ps = (c.texto ?? '').toLowerCase().split(' ').filter(Boolean)
  ps.forEach((p, i) => {
    const s = document.createElement('span')
    s.className = i === ps.length - 1 ? 'serif' : 'sans'
    s.textContent = p
    texto.append(s, document.createTextNode(' '))
  })
  const credito = document.createElement('div')
  credito.className = 'imagem-credito'
  credito.textContent = c.credito ?? ''
  caixa.append(texto, credito)

  const d = c.fim - c.ini
  gsap.set(caixa, { opacity: 0 })
  // entrada: dolly-in de longe (zoom alto, desfocado) até assentar; o parallax "abre" a cena
  t.fromTo(caixa, { opacity: 0, filter: 'blur(22px)' },
    { opacity: 1, filter: 'blur(0px)', duration: 0.75, ease: 'power3.out', immediateRender: false }, c.ini)
  t.fromTo(estado, { zoom: 1.5, forca: 0, dx: 0.07, dy: 0.03 },
    { zoom: 1.12, forca: 1, dx: 0.02, dy: 0.01, duration: 0.9, ease: 'expo.out', immediateRender: false }, c.ini)
  // permanência: a câmera desliza e o primeiro plano se descola do fundo
  t.to(estado, { zoom: 1.04, dx: -0.035, dy: -0.012, duration: Math.max(d - 1.6, 0.4), ease: 'sine.inOut' }, c.ini + 0.9)
  // saída: avança através da imagem e some
  t.to(estado, { zoom: 1.32, forca: 1.4, duration: 0.7, ease: 'power3.in' }, c.fim - 0.7)
  t.to(caixa, { opacity: 0, filter: 'blur(18px)', duration: 0.55, ease: 'power2.in' }, c.fim - 0.55)
  t.fromTo(texto.children, { opacity: 0, y: 26, filter: 'blur(12px)' },
    { opacity: 1, y: 0, filter: 'blur(0px)', duration: 0.7, ease: 'expo.out', stagger: 0.1, immediateRender: false }, c.ini + 0.5)
  desenhar()
}
