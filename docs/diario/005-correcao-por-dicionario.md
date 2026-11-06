# 005 · Correção por dicionário (2026-11-06)

Implementado em `apps/engine/src/garimpo/correcao/`:
- `dicionario.py`: dicionário **por usuário**, salvo em `%APPDATA%\ATTO Tools\dicionario.json`; aprende as correções aprovadas.
- `corretor.py`: compara trechos de 1 a 3 palavras com os termos por **chave fonética** (som parecido) e similaridade; devolve sugestões sem sobreposição. Variantes já aprovadas antes voltam com confiança 1,0 (`conhecida`).
- `tests/test_correcao.py`: 4 testes (erros reais do Whisper, sem falso positivo, termo já correto, aprendizado persistente).

Resultado na amostra real de 10 min (1.639 palavras): as 2 ocorrências de "Cinti Preste" viram dúvida para SINDEPRESTEM, sem nenhum falso positivo.

Limite conhecido: "CintiCato" (= sindicato) não é capturado porque "sindicato" não está no dicionário; o usuário pode adicioná-lo. A tela de aprovação virá no app.
