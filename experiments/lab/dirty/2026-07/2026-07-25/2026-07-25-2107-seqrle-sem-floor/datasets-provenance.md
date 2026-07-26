# Proveniência — seq-RLE sem FLOOR (2026-07-25-2107)

**Fonte**: 100% sintético/determinístico (LCG de seed fixa). Nenhum download, nenhum dado real.

## Desenho da matriz

Os grupos existem para **separar a decisão**, não para amostrar o mundo:

- **A. SENSÍVEIS (8)** — dado sem cadência, onde a suspeita do owner se aplica. Varre
  cardinalidade (`k = 10, 100, 10⁶`) × tamanho (`n = 100, 1000`), mais dois casos de forma
  diferente (hex pseudo-aleatório e preços com 2 casas). É onde o marcador de delta tende a
  não pagar.
- **B. FAVORÁVEIS (5)** — cadência limpa (sequencial, passo 5, ids) e estrutura textual
  (datas ISO, emails). Existem como **controle**: o FLOOR não pode estragar o que já ganha.
- **C. MISTOS (3)** — a fronteira. `C-blocos` (metade sequencial, metade ruído) é o caso que
  decide entre FLOOR por-corpo e "desligar em dado desordenado".

## Baselines

- **`bruto`** = `_encode_column(..., cfg=hcc_seq_rle=False)`. É **exatamente** o corpo que o
  `super().encode()` produz dentro do `HCCSeqRLE` — a mesma classe (`M8AVirtualRefsSyntax`),
  não uma aproximação.
- **`sempre`** = `_encode_column(...)` no default, isto é, o comportamento **atual**.
- **`floor`** = `min` dos dois, computado no lab. Nada em `src/tcf` foi alterado para medir.

## Validação

RT verificado nas **duas** formas reais: o wire com marcador e o wire sem. O corpo sem
marcador é um wire **válido** — o decode não exige o marcador, só expande quando existe.
32/32.

## Limites declarados

- **Métrica única: bytes do corpo.** Sem gzip, sem latência, sem memória. O cabeçalho fica
  fora porque é constante entre as três formas.
- **Dado sintético.** `range(n)` é o melhor caso do seq-RLE, o LCG uniforme é próximo do
  pior. Coluna real fica entre os dois — a matriz cobre os extremos e um misto, não uma
  distribuição realista.
- **Uma coluna por vez.** Multi-col e `.8H` não entram, embora o mesmo `_encode_column` os
  sirva (o efeito medido se aplica a eles por construção).
- **A economia total (929 B) é da matriz**, não uma expectativa de ganho — ela depende
  inteiramente de quantos casos sensíveis se inclui.

## Reprodutibilidade

`python run.py` regenera byte a byte — LCG de seed fixa, sem `random` global, sem relógio,
sem rede. **Zero escrita em `src/tcf`.**
