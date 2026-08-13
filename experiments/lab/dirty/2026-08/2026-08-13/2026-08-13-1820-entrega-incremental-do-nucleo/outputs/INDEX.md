# INDEX

| caso | ideia | wire | entrega incremental | contra-prova |
|---|---|---|---|---|
| `bool-blocos` | RLE: cada marcador e' uma linha AUTOCONTIDA | [.tcf](./bool-blocos.tcf) (36 B, 3 linha(s)) | [curva](../intermediates/bool-blocos.entrega-incremental.json) — 3 ponto(s) | [roundtrip](./bool-blocos.roundtrip.json) |
| `bool-alternado` | bN de dominio: dicionario na frente, indices empacotados numa linha densa | [.tcf](./bool-alternado.tcf) (124 B, 3 linha(s)) | [curva](../intermediates/bool-alternado.entrega-incremental.json) — 1 ponto(s) | [roundtrip](./bool-alternado.roundtrip.json) |
| `bool-aleatorio` | idem, sem estrutura de bloco | [.tcf](./bool-aleatorio.tcf) (124 B, 3 linha(s)) | [curva](../intermediates/bool-aleatorio.entrega-incremental.json) — 1 ponto(s) | [roundtrip](./bool-aleatorio.roundtrip.json) |
| `bool-tudo-true` | RLE total: UMA linha entrega tudo | [.tcf](./bool-tudo-true.tcf) (17 B, 1 linha(s)) | [curva](../intermediates/bool-tudo-true.entrega-incremental.json) — 1 ponto(s) | [roundtrip](./bool-tudo-true.roundtrip.json) |
| `categoria-k5` | bN com 5 valores de dominio | [.tcf](./categoria-k5.tcf) (346 B, 6 linha(s)) | [curva](../intermediates/categoria-k5.entrega-incremental.json) — 1 ponto(s) | [roundtrip](./categoria-k5.roundtrip.json) |
| `data-spec` | seq-RLE: UMA linha — compressao maxima, granularidade minima | [.tcf](./data-spec.tcf) (26 B, 1 linha(s)) | [curva](../intermediates/data-spec.entrega-incremental.json) — 1 ponto(s) | [roundtrip](./data-spec.roundtrip.json) |
| `data-uteis-spec` | seq-RLE periodico: idem, UMA linha | [.tcf](./data-uteis-spec.tcf) (34 B, 1 linha(s)) | [curva](../intermediates/data-uteis-spec.entrega-incremental.json) — 1 ponto(s) | [roundtrip](./data-uteis-spec.roundtrip.json) |
| `texto` | OBAT por afixo: varias linhas | [.tcf](./texto.tcf) (68 B, 5 linha(s)) | [curva](../intermediates/texto.entrega-incremental.json) — 5 ponto(s) | [roundtrip](./texto.roundtrip.json) |
| `email` | idem, afixo mais longo | [.tcf](./email.tcf) (73 B, 4 linha(s)) | [curva](../intermediates/email.entrega-incremental.json) — 4 ponto(s) | [roundtrip](./email.roundtrip.json) |

**Pontos de entrega** = quantos prefixos de linhas integras ja' respondem algo correto. E' a granularidade natural de streaming daquela coluna: o wire e' o MESMO, so' muda em quantos pedacos uteis ele se deixa cortar.

A contra-prova de cada caso e' `diff` entre `outputs/<c>.roundtrip.json` e `inputs/<c>.entrada.json` (mesma formatacao; tem de dar vazio).
