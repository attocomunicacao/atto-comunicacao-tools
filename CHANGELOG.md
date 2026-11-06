# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/). Versões seguem `x.y.z`.

## [0.4.0] - 2026-11-06

### Alterado
- **Transcrição reconstruída**: Whisper large-v3-turbo (beam 5, VAD, sem repetição em loop) com os termos do seu dicionário como dica. Mais lenta (~0,6x o tempo real), bem mais precisa, principalmente na pontuação. Baixada na primeira vez (1,6 GB); o small embutido fica como plano B sem internet.
- **Seleção de cortes em 3 camadas**: filtros duros (contagem regressiva ou progressiva, "gravando", "derrubando", "pronto", abertura do programa, frase dependente ou fragmento no começo; tudo antes do bastidor inicial é ignorado), pontuação com peso alto para o **gancho dos 5 primeiros segundos**, e um **juiz LLM local** (Qwen3-4B, Apache-2.0, em CPU) que dá notas de gancho, contexto, valor e fechamento e pode adiantar o início para a frase mais forte. Baixado na primeira vez (2,5 GB).
- **Legenda com motion**: entrada desfocada que assenta com easing exponencial (opacidade, y de -100 px a 0, escala 90% a 100%) e saída que desfoca e desce enquanto a próxima palavra entra, como no vídeo de referência. Desenhada a 60 quadros por segundo.

## [0.3.0] - 2026-11-06

### Adicionado
- **Logo no final dos cortes**: no app, "Anexar logo" (PNG/JPG/WebP, guardada no computador). Cada corte ganha 2,2 s finais com o último quadro escurecido e a logo entrando com fade e subida suave.
- **Tela de carregamento detalhada**: progresso geral e por etapa, tempo decorrido, lista de etapas e "Ver detalhes do que está sendo feito" com o registro ao vivo do motor (transcrição, enquadramento, codificação).

### Alterado
- **Enquadramento estável**: o eixo do recorte fica fixo e só muda quando a câmera ou o falante mudam de fato (zona morta larga, mudança precisa durar ~2 s, filtro de maioria contra piscadas da detecção).
- **Dissolução suave** (0,4 s) ao entrar e sair da tela dividida; o áudio não sofre desvio.
- **Legenda**: 64 px, uma palavra por vez, branca, maiúscula, uma só fonte (Lato). Glow em duas camadas, mais suave; entrada com easing quadro a quadro (opacidade, y de -100 px a 0 e leve desfoque que some).
- **Cortes**: ignoram teste de som e "gravando" no começo da gravação; frases que dependem da anterior ("isso", "mas", "então"...) puxam o contexto; fim sempre em frase completa; início e fim ajustados ao silêncio mais próximo, sem cortar palavras. Fade curto no áudio.
- Versão do app mostrada no menu lateral (antes fixa em "v0.0.0 · em desenvolvimento").

## [0.2.1] - 2026-11-06

### Corrigido
- **Corte vertical**: falhava ("Failed to configure output pad") em vídeos com pixel não quadrado (SAR 404:405) quando o enquadramento alternava entre recorte único e tela dividida.

## [0.2.0] - 2026-11-06

### Alterado
- **Launcher**: reconsulta novas versões ao voltar para a janela e a cada 5 minutos (antes só ao abrir).
- **Corte vertical**: o vídeo original agora ocupa 100% da tela 1080×1920 (sem fundo desfocado), com recorte centrado em quem aparece/fala. Com dois rostos em quadro (câmera central), a tela é dividida ao meio (960 px cada; esquerda em cima, direita embaixo). Detecção de rostos local (YuNet, ONNX incluído).
- **Legenda**: branca, sem traçado, 48 px, uma palavra por vez, centralizada, glow fixo e entrada suave (opacidade 0→100% e y de -100 px para 0).

## [0.1.0] - 2026-11-06

Primeira versão de testes.

### Adicionado
- **Garimpo**: transcrição local (faster-whisper `small`), dicionário pessoal com correção por busca fonética, separação em frases, parágrafos e temas (`.md`), sugestão de cortes de 30 s a 1min30 sem cortar frases, prévia em áudio e geração de MP4 vertical 1080×1920 com legenda palavra por palavra (Lato maiúscula).
- **ATTO Tools** (janela do app) com identidade visual da ATTO: vídeo, transcrição, dúvidas, cortes e exportação, além de "Meu dicionário".
- **Launcher**: instala e atualiza lado a lado, confere o SHA-256 e permite voltar à versão anterior.
- Empacotamento (Electron + Python + FFmpeg + modelo + fontes) e `manifest.json` da release.
- Site de apresentação e documentação do desenvolvimento em `docs/diario`.

### Conhecido
- Instalador do Launcher (`ATTO-Tools-Setup-0.1.0.exe`) anexado à release. Pacote de cerca de 886 MB; o app não é assinado digitalmente (SmartScreen avisa); a escolha automática dos melhores trechos ainda pode trazer conversa de abertura.
