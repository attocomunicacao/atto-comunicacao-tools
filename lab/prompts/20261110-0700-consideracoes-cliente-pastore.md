# Prompt — considerações do cliente no teste real (Eduardo Pastore, cortes 05/06/08)

Você é editor de motion do Garimpo. Aplique as três considerações do cliente sem quebrar o resto:

1. **Flash cut curto.** Hoje são 24 quadros (0,4 s antes + 0,4 s depois) alternando A/B com silhueta, o que dá a
   sensação de "vai e volta". Novo: só 2 a 4 quadros de silhueta branca bem no ponto de troca, sem voltar ao plano
   anterior depois de entrar no próximo. Sequência alvo: A, A, A(silhueta) | B(silhueta), B(silhueta), B.
   Arquivo: `apps/engine/src/garimpo/transicoes.py` (FLASH_ANTES/DEPOIS, PADRAO_*).
2. **Ícone sem texto duplicado.** A cena de ícone/conceito não escreve frase nem palavra-chave própria; o único texto
   na tela é a legenda, que continua passando por cima do fundo escuro. O ícone sobe para a metade de cima para não
   colidir com a faixa da legenda (y 1180–1600). Arquivos: `main.ts` (cenaIcone, cenaConceito), `motion.css`,
   `legendas.ts` (a legenda só some sob a citação).
3. **Card de informação externa.** O recorte de papel (cena "documento") é o formato para tudo que vem de fora da
   conversa: lei, decisão, norma e frase de filósofo/autor ("como dizia Sócrates…"). O chapéu diz a origem ("LEI",
   "SÓCRATES"). Arquivo: `motion.py` (`documentos_por_regras`).

Validação: testes do motor, `tsc`, lab de cenas (icone, conceito, documento) e re-render dos cortes 05 e 08 do vídeo
2026-11-03 16-27-18-002; conferir quadro a quadro o flash e as cenas.
