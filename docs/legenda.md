# Legenda dos cortes — sistema e regras

Estilo "minimal premium" (referência: youtu.be/g9xoKm5DEeU). Implementação: `apps/engine/src/garimpo/motion.py`
(plano) e `apps/desktop/src/renderer/src/motion/main.ts` (`legenda`).

## 1. Quebra em linhas (regras, `grupos_legenda`)
- Até 5 palavras por linha; quebra em pontuação (`, . ? ! ; :`) ou pausa > 0,35 s; pausa > 0,8 s sempre quebra.
- Nunca termina a linha em palavra vazia ("no", "e", "da", "que"): ela passa para a linha seguinte.
- Linha de 1 palavra se junta à seguinte.
- O LLM de 4B testado **não** segmenta bem (devolveu linhas de 1–2 palavras com a chave sempre na primeira) — por isso
  a quebra é por regras, e o LLM fica com a tarefa simples de escolher a chave.

## 2. Palavra-chave (a que vai em serifa itálica)
- O LLM local (`chaves_por_llm`) escolhe, linha a linha, a palavra que carrega o sentido.
- A resposta é validada: a palavra precisa existir na linha e não pode ser vazia/auxiliar (`AUXILIARES`).
- Reserva sem LLM (`_peso_chave`): número +3, ênfase +2, palavra de conteúdo (≥ 4 letras) +1 + tamanho/10,
  nome próprio no meio da frase +1,5, auxiliar −2.
- Linha só de muleta ("mas assim", "ainda não"): **sem chave** — tudo pequeno numa linha (`sem_chave`).

## 3. Ordem de leitura e espaço
- O bloco se lê de cima para baixo na ordem da fala: palavras antes da chave **acima**, chave no **centro**,
  palavras depois **abaixo**. Nunca se inverte a ordem.
- Zonas fixas (1080x1920): rosto do falante ~300–1000 px (livre); ilustrações flutuantes 230–900 px (com vinheta);
  legenda 1270–1600 px (terço inferior, acima da área de interface das redes); crédito de imagem 1830 px.
- Em tela cheia (imagem 3D, pintura) a legenda continua por cima; na **citação** (cold open) a legenda some (a frase
  já está escrita no centro).
- Tamanho da chave: 84–150 px, ajustado ao comprimento para caber em ~940 px; pequenas a 46 px.

## 4. Motion
- Pequenas: surgem no tempo da fala (opacidade, y 14→0, blur 8→0, 0,45 s `power3.out`).
- Chave: blur 18→0, y −60→0, escala 1,1→1, letter-spacing 0,08em→0; 0,85 s `expo.out`.
- Bloco respira (y −10 ao longo da linha) e sai inteiro desfocando (0,3 s `power2.in`) antes da próxima.

## 5. Como revisar
Rode a skill `garimpo-legenda` ou o agente `legendista` sobre o `corte-NN.plano.json` gerado em `saida/`.
