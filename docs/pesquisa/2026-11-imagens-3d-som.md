# Pesquisa: imagens livres, efeito 3D e som (2026-11)

## Bancos de imagem usados (ordem de busca em `garimpo/imagens.py`)
| Fonte | Licença | Observação |
|---|---|---|
| Pexels (API, chave gratuita) | Licença Pexels: uso comercial livre, atribuição não obrigatória | Opcional: o usuário cadastra a chave no app. Limite 200 req/h. |
| Wikimedia Commons (API) | Varia por arquivo | Filtramos SÓ "Public domain", "CC0", "No restrictions" (lido em `extmetadata.LicenseShortName`). |
| Openverse (API) | Filtro `license=cc0,pdm` | Estava com 504 no teste; entra como reserva. |
| Metropolitan Museum Open Access | CC0 | Pinturas; reserva final (`recursos.pintura`). |
| Art Institute of Chicago | CC0 | **Descartado**: API atrás de verificação anti-robô (Cloudflare). |
| Pixabay | Licença própria (não é mais CC0) | Não usado. |

Fontes: [laozhang.ai — Unsplash vs Pexels vs Pixabay vs Wikimedia](https://blog.laozhang.ai/en/posts/free-image-api),
[openreplay — free stock photo resources](https://blog.openreplay.com/free-stock-photo-resources/),
[wpbeginner — 16 sources CC0](https://www.wpbeginner.com/showcase/16-sources-for-free-public-domain-and-cc0-licensed-images/).

## Efeito 3D (2.5D / parallax)
- Profundidade: [Depth Anything V2 Small em ONNX](https://huggingface.co/onnx-community/depth-anything-v2-small)
  (Apache-2.0; os modelos maiores têm licença não comercial). Roda no processador com onnxruntime (~13 s/imagem).
- Render: shader WebGL (`motion/imagem3d.ts`) que desloca o pixel pela profundidade enquanto a câmera faz dolly
  (mesma ideia de [render-image-depth](https://awesome.ecosyste.ms/projects/github.com%2Factiveguild%2Frender-image-depth),
  [react-depth-parallax](https://www.pkgstats.com/pkg:react-depth-parallax) e do artigo
  [cinematic depth in the browser](https://dev.to/martindelophy/building-cinematic-depth-in-the-browser-with-depth-anything-v2-small-and-webgpu-1k07)).
- No render offscreen o WebGL roda em software (`--enable-unsafe-swiftshader`).

## Tipografia de legenda (prática do mercado, fontes informais)
Duas camadas (legenda completa + ênfase animada só nas palavras que carregam a história), 2–4 palavras por linha de
ênfase, quebra nas pausas naturais, reservar o terço inferior para legenda, legibilidade primeiro.
Fontes: [cursa — caption systems](https://cursa.app/en/page/caption-systems-and-kinetic-text-for-clarity),
[CapCut — readable kinetic typography](https://www.capcut.com/features/how-to-make-kinetic-typography-capcut-workflow).

## Som
O usuário tem Epidemic Sound: ele baixa os efeitos na conta dele e anexa no app (whoosh, clique, impacto). Sem arquivo,
`garimpo/sons.py` sintetiza efeitos sutis com o FFmpeg. Mixagem abaixo da voz (−16 a −22 dB) com limitador.
