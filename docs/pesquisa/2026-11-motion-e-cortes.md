# Pesquisa: motion com IA e seleção automática de cortes (2026-11)

## Motion / edição programática
| Projeto | O que é | Uso no ATTO |
|---|---|---|
| [HyperFrames](https://hyperframes.dev) | HTML + GSAP renderizado quadro a quadro com timeline pausada | **Contrato adotado** (timeline pausada, `seek`, determinismo) |
| [Remotion](https://github.com/remotion-dev/remotion) | Vídeo com React; #1 no GitHub Trending em jan/2026 | Descartado: licença de empresa paga em alguns casos; componente de legenda animada é pago |
| [Revideo](https://github.com/redotvideo/revideo) / [Motion Canvas](https://motioncanvas.io) | Vídeo com TypeScript/canvas | Bom para pipelines, mas exigiria outro runtime |
| [Higgsfield Vibe Motion / Katana](https://higgsfield.ai/blog/higgsfield-katana) | Motion graphics por IA (proprietário, nuvem, créditos) | Referência de estética; Katana refaz edições a partir de um vídeo de referência, não gera b-roll da fala |
| [GSAP](https://gsap.com) | Motor de animação (easing, stagger, timelines) | **Motor da camada** — gratuito inclusive para uso comercial |
| [Lucide](https://lucide.dev) | Ícones SVG de traço (ISC) | Ícones com efeito "desenhar o traço" |

Decisão: em vez de depender de um serviço/CLI externo, o próprio Electron do app renderiza a camada (offscreen,
transparente) e o FFmpeg compõe. Funciona offline, sem créditos, e é determinístico.

## Seleção de cortes (open source)
| Projeto | Método |
|---|---|
| [OpenShorts](https://github.com/mutonby/openshorts) (MIT) | Gemini lê transcrição + cenas e acha 3–15 momentos; FFmpeg corta; MediaPipe reenquadra |
| [SupoClip](https://github.com/FujiwaraChoki/supoclip) (AGPL) | LLM escolhe 3–7 trechos e dá notas de gancho, engajamento, valor e compartilhamento |
| [AI-Youtube-Shorts-Generator](https://github.com/Anil-matcha/AI-Youtube-Shorts-Generator) | Whisper + GPT para destacar trechos, recorte vertical |
| ViralCutter | App desktop para cortes de vídeos longos |
| Rankers descritos em [moclaw.ai](https://moclaw.ai/blog/free-ai-shorts-generator) | Classifica o formato, nota 0–100 por critérios (gancho, pico emocional, opinião forte, frase citável), **remove sobreposições** antes do top N |

Padrão comum: transcrição -> LLM pontua janelas com rubrica -> remove sobreposição -> corta e reenquadra.
O ATTO segue esse padrão, mas local (Qwen3-4B em CPU), com filtros duros antes do LLM (bastidor, abertura) e o
**cold open**: a frase de maior impacto vai para os primeiros segundos, técnica comum em cortes virais.
