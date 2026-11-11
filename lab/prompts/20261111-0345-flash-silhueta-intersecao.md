# Ciclo 30 — flash cut: silhueta = interseção dos dois modelos

Folha do flash (rodada 20261111-033040) e mapa de classes: o modelo multiclasse (256x256, quadro 9:16 esmagado) rotula a
tampa do notebook como "roupa" e um pedaço da mesa como "pele" — a silhueta branca vaza sobre eles (regra do cliente:
silhueta só da pessoa). Letterbox e ladrilhos não resolvem (notebook 0,34 → 0,22/0,17). O modelo binário antigo
(`onnx-community/mediapipe_selfie_segmentation`, já em cache como `mediapipe_selfie.onnx`) dá 0,03 no notebook, mas
engole microfone e notebook em outras cenas (ciclo 10). A interseção (média geométrica) dos dois mantém a pessoa e as mãos
e tira o notebook/mesa (teste em `scratchpad/intersecao.png`).

Mudança pedida (UMA): em `transicoes.mascara_pessoa`, multiplicar a probabilidade de pessoa do multiclasse pela do binário
(sqrt(multi * binário)) antes do limiar `(m-0,35)/0,3` e do desfoque. O binário é um 2º `InferenceSession` com cache
próprio (`_sessao_bin`), baixado por `recursos.baixar` como antes do ciclo 10.

Sucesso: flash_cut segue 10 (quadros_silhueta 3, vai_e_volta 0, duração 0,2 s); brancura_max cai (0,287 → ~0,26-0,27) e
na folha o notebook e a mesa ficam sem branco; zoom_inicial sem mudança.
