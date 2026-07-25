# Proveniência — null como índice 0 numa coluna de string (2026-07-24-2210)

**Fonte**: 100% sintético/determinístico. Nenhum dado real, nenhum download, nenhum CPF/CNPJ.

## Casos nomeados (5)

| id | dados | por que existe |
|---|---|---|
| `A-exemplo-owner` | `[null, "", "true", "false", "oi", null, "null"]` | **o exemplo literal do owner** — exercita as 4 vias numa coluna de string |
| `B-n7-1null` | 7 status, 1 null | n pequeno com null único (sem repetição p/ `^N`) |
| `C-todos-null` | 12× null | borda: coluna 100% null |
| `D-null-bordas` | null na 1ª e na última posição | posição extrema (o 1º elemento semeia o tokenizador) |
| `E-sem-null` | 4 status, 0 null | **CONTROLE**: o protótipo tem que sair byte-idêntico ao flat |

## Regimes varridos (12)

`n ∈ {10, 100, 1000}` × `densidade de null ∈ {1, 10, 50, 90}%`, vocabulário de baixa
cardinalidade (5 status realistas), null sorteado por **LCG local com seed fixa (7)** — sem
`random` não-seedado, sem relógio.

**Desvio declarado**: em `n=10`, as densidades de 1% e 10% produziram **0 nulls** (o LCG não
sorteou nenhum). As linhas não foram removidas — continuam válidas como controles extras de
byte-identidade — mas **não medem o que o rótulo sugere**. Está anotado no README e visível na
coluna `nulls` do `result.md`.

## Comparação

- **`hoje`** = `src/tcf` **REAL** (`encode`/`decode` da API pública, rota `.8H`). Não é
  simulação — é o produto.
- **`proto`** = wire do protótipo. O encode/decode do protótipo **delega ao core real**
  (pré-avaliador que traduz entre camada implícita e explícita), então o RT é fiel e não há
  reimplementação do compressor.

Ambos têm o RT validado em todos os 17 casos — a comparação só vale porque os dois lados
round-trip.

## Reprodutibilidade

`python run.py` regenera byte-a-byte. Zero escrita em `src/tcf`. Saídas em `outputs/`:
`*-hoje.tcf` (wire REAL) e `*-proto.tcfp` (extensão `.tcfp` = protótipo, não é formato vigente).
