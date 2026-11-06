// Simula a ponte `window.atto` com DADOS FICTÍCIOS, só para gerar as capturas de tela do README e do site.
// Nada aqui vem de clientes ou de gravações reais.
;(() => {
  const ouvintes = []
  const emitir = (l) => ouvintes.forEach((f) => f(l))
  const wav = () => {
    const n = 22050, b = new ArrayBuffer(44 + n * 2), v = new DataView(b)
    const s = (o, t) => [...t].forEach((c, i) => v.setUint8(o + i, c.charCodeAt(0)))
    s(0, 'RIFF'); v.setUint32(4, 36 + n * 2, true); s(8, 'WAVEfmt '); v.setUint32(16, 16, true); v.setUint16(20, 1, true)
    v.setUint16(22, 1, true); v.setUint32(24, 22050, true); v.setUint32(28, 44100, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true)
    s(36, 'data'); v.setUint32(40, n * 2, true)
    return new Uint8Array(b)
  }
  const duvidas = [
    { id: 0, original: 'Cinde Serve', sugestao: 'SINDSERV', confianca: 0.93, conhecida: false, inicio: 0, fim: 0,
      contexto: 'Bom dia a todos, é um prazer receber vocês no auditório do Cinde Serve, que hoje abre o ciclo de palestras de 2026.' },
    { id: 1, original: 'Alicança Tec', sugestao: 'ALIANÇATEC', confianca: 0.88, conhecida: false, inicio: 0, fim: 0,
      contexto: 'Quem apoia este encontro é a Alicança Tec, parceira do sindicato desde a primeira edição.' }
  ]
  const lorem = [
    'O maior erro de quem lidera é achar que comunicar é falar. Comunicar é garantir que o outro entendeu. Na prática, isso significa repetir a mesma mensagem de três formas diferentes e perguntar, no final, o que ficou claro. Quando a equipe sabe o porquê da decisão, ela executa melhor e discute menos.',
    'Feedback não é crítica. É informação que a pessoa ainda pode usar. Por exemplo: em vez de dizer que a entrega ficou ruim, diga o que você esperava e o que viu. Ou seja, descreva o fato, o impacto e o próximo passo. Isso muda a conversa inteira.',
    'Reunião boa tem pauta, tem hora para acabar e termina com responsável e prazo. Se ninguém sai com uma tarefa, a reunião foi só uma conversa cara. A regra é simples: sem decisão, sem convite.'
  ]
  const cortes = [
    { n: 1, tema: 'comunicação / equipe / mensagem', ini: 312, fim: 371, duracao: 59, texto: lorem[0] },
    { n: 2, tema: 'feedback / pessoa / fato', ini: 1104, fim: 1158, duracao: 54, texto: lorem[1] },
    { n: 3, tema: 'reunião / pauta / decisão', ini: 2230, fim: 2284, duracao: 54, texto: lorem[2] }
  ]
  const termos = { SINDSERV: ['Cinde Serve'], 'ALIANÇATEC': [], 'Raquel Monteiro': ['Rachel Monteiro'] }
  window.atto = {
    escolherVideo: async () => 'C:\\Vídeos\\Palestra Liderança 2026.mp4',
    criarProjeto: async () => 'C:\\demo',
    aoLinha: (fn) => { ouvintes.push(fn); return () => ouvintes.splice(ouvintes.indexOf(fn), 1) },
    motor: async (cmd, args) => {
      if (cmd === 'dicionario') emitir('DICIONARIO ' + JSON.stringify(termos))
      if (cmd === 'exportar') args[args.indexOf('--aprovados') + 1].split(',').forEach((n) => emitir(`ARQUIVO C:\\demo\\saida\\corte-0${n}.mp4`))
      return { codigo: 0, erro: '' }
    },
    lerJson: async (_p, nome) => (nome === 'duvidas.json' ? duvidas : cortes),
    lerBytes: async () => wav(),
    versao: async () => '0.3.0',
    logoAtual: async () => null,
    logoBytes: async () => null,
    escolherLogo: async () => null,
    removerLogo: async () => {},
    mostrarNaPasta: async () => {}
  }
})()
