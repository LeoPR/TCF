# Resultado — dual do RLE (multiplicidade), medido

**[probatório]** `run.py` valida RT nos dois modelos antes dos bytes.
Contra-prova: [`outputs/10-conclusao.txt`](outputs/10-conclusao.txt). Interpretação
completa no [README](README.md). Sintético, viés declarado
([datasets-provenance.md](datasets-provenance.md)).

## Números (RT-exato A e B)

| entrada | campos-pai | A tabelão | B nível-aware | Δ |
|---|---:|---:|---:|---:|
| 01-estreito | 1 | **135 B** | 140 B | A vence +5 |
| 02-largo | 11 | 466 B | **423 B** | B vence −43 |

## Veredito

- A intuição do owner (a multiplicidade não repete por coluna; RLE deduzível; sincronismo)
  **confere e já estava concluída** — peça 9 (2328) + H-CARD-06 + teoria §3-4 (RLE↔counts↔fk
  duais, ×N conservada).
- **Crossover por largura**: poucos campos-pai → tabelão (A); muitos → nível-aware (B, counts 1×).
- Meu protótipo (2301/2325) = Modelo A (dual explícito, simples, correto). O mínimo é B.
- **Resposta TCF**: A e B são candidatos de `min()` (como o FLOOR) — encoda os dois, fica com
  o menor por documento. Firmar = decisão do owner (A / B / min()).

`confianca: Média` (sintético, N=1 lab, medida de forma). Falta gate real-world + a extensão
multi-array/aninhado-profundo.
