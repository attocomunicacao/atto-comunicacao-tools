# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/). Versões seguem `x.y.z`.

## [0.6.0] - 2026-11-09

### Adicionado
- **Estilo minimal premium**: legenda em linhas de até 5 palavras, palavra de sentido em Playfair Display itálico (escolhida pelo LLM local), demais em Inter; ilustrações sem cartão (linha + texto, gráfico com grade e bolinha, ícone com órbita, citação em tela cheia).
- **Motor de presets da legenda**: 8 animações (cinematográfica, máquina de escrever, desliza pra cima/baixo/esquerda/direita, elástica, entrada com deslocamento) e 3 de gancho (impacto, revelação, glitch), escolhidas pelo contexto.
- **Motor de transições**: flash cut com silhueta branca (MediaPipe Selfie Segmentation) no gancho e nas trocas de locutor; zoom 230% → 100% com desfoque de movimento, alternando com o flash.
- **Mapa de espaço**: rostos detectados no vídeo montado; legenda e ilustrações vão para faixas livres e nunca cobrem o rosto (sem espaço, a cena vira corte em tela cheia).
- **Imagens livres por frase com efeito 3D** (Pexels com chave do usuário, Wikimedia Commons PD/CC0, Openverse, Met) e profundidade por Depth Anything V2; cena **documento** estilo Vox (papel, manchete, marca-texto).
- **Design de som**: whoosh, clique e impacto sutis; o usuário pode anexar os seus (ex.: Epidemic Sound) em "Sons da edição".
- Skills `garimpo-legenda`, agentes `legendista` e `revisor-de-edicao`, docs `motor-edicao.md`, `legenda.md` e pesquisas em `docs/pesquisa/`.

### Corrigido
- Laço infinito ao resumir citações; respostas vazias do LLM com gramática JSON; imagens fora de contexto ou sensíveis.

## [0.5.0] - 2026-11-09

### Adicionado
- **ATTO Motion**: nova camada de animação dos cortes em HTML + GSAP, renderizada quadro a quadro pelo próprio app (mesmo princípio do HyperFrames e das ferramentas de "vibe motion"). Fundo transparente, composta pelo FFmpeg.
- **Ilustrações animadas do que é falado**: números que contam ("75 mi", "40%"), comparações antes → depois ("44h → 40h"), ícones que se desenham (lei, jornada, governo, dinheiro...) e frases-chave / título-gancho. Vêm de regras e do LLM local (Qwen3-4B), espaçadas para não poluir.
- **Edição dinâmica**: zooms suaves de ênfase (punch-in de 9% com supersampling, sem tremor), flash na transição do gancho e áudio masterizado para redes (−14 LUFS, compressor, filtro de graves).
- **Cold open**: o juiz aponta a frase de maior impacto e o motor escolhe dentro dela a oração mais forte (2–7,5 s, sem conectivo solto no começo); ela abre o vídeo, seguida do corte desde o início. Total sempre ≤ 90 s.
- **Menos cortes, melhores**: cerca de 1 a cada 8 min de gravação (3 a 10), só com nota mínima do juiz.
- Números sugeridos pelo LLM só entram se aparecem na fala; no máximo 3 ícones por corte.
- Skills do projeto (`garimpo-motion`, `garimpo-cortes`, `atto-release`), `CLAUDE.md`, `docs/motion.md` e a pesquisa em `docs/pesquisa/`.

### Alterado
- **Legenda** refeita na camada de motion: entrada com desfoque → nítido, y −100 → 0 e escala, assentando com `expo.out`; respiração sutil parada; saída desfocando e descendo; ênfase em números e palavras fortes. Continua uma palavra por vez, branca, maiúscula, Lato 64 px.
- Empacotador com plano B: se o Windows bloquear o binário nativo do `@electron/packager`, monta o app a partir do Electron já descompactado (sem ícone/metadados no .exe nesta versão).
- O instalador do Launcher continua o da v0.4.0 (o código do Launcher não mudou; o compilador NSIS foi bloqueado pela política de Controle de Aplicativos desta máquina).
- Leitura das respostas do LLM ficou tolerante a formatos variados (antes, notas caíam no padrão 5 e cenas eram descartadas).

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
