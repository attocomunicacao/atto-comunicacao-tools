# 004 · Teste do LLM local para correção (2026-11-06)

Ollama com modelos já instalados, CPU (i7, Iris Xe). Tarefa: corrigir 1.800 caracteres da transcrição do Whisper small com dicionário `SINDEPRESTEM` e listar dúvidas. Script: `apps/engine/scripts/bench_llm.py`.

| Modelo | Resultado |
|---|---|
| qwen2.5:3b | 98 s para 1.800 caracteres (840 tokens). **Não aplicou o dicionário**: manteve "CintiCato"/"Cinti Preste" e listou "dúvidas" idênticas ao original. |
| qwen2.5:1.5b | Não terminou em mais de 8 min; teste interrompido. |

Conclusões:
- Passar a transcrição inteira por um LLM de CPU é inviável (3 h de fala levaria horas) e não corrigiu o caso-alvo.
- Correção de nomes deve ser **determinística**: casamento aproximado (fonético e distância de edição) contra o dicionário do usuário, gerando a lista de dúvidas para aprovação. O LLM entra só nos trechos sinalizados e na análise de temas, em blocos pequenos.
- A decisão do modelo de temas fica pendente de novo teste (segmentação por pausas e embeddings `nomic-embed-text`, já instalado).
