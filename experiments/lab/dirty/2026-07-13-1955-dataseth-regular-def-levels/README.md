# Lab 2026-07-13-1955 — P4: especiais × topologia regular (def-levels)

**Status**: pesquisa/medido, sintético. **Ticket**:
[T-STUDY-HIERARCHICAL-TCF](../../../../tickets/T-STUDY-HIERARCHICAL-TCF.md).
**Plano**: [dataseth-hierarquia-completa-plano.md](../notas/dataseth-hierarquia-completa-plano.md) (P4).
**Hipótese**: H-HIER-SCALAR-01 × forma regular.

Cruza os escalares especiais com **presença/definition levels, arrays ragged e a forma
REGULAR** (schema no header, multiplicidade implícita — a forma multirow que o grupo de
labs do `#TCF.8H` validou). Não toca `src/tcf`; wires de estudo `#PROTO.R1/R2`.

## Pergunta e contra-prova

Na forma regular, um stream de kind **só por folha** (R1: `{absent, null, nan, …}`)
carrega presença suficiente? **Não** — contra-exemplo executável: `{}` (b ausente) e
`{"b": {}}` (b presente-vazio) produzem streams de folha IDÊNTICOS (`absent`,`absent`)
e colidem no decode. A informação de **onde a cadeia quebra** não vive na folha.

**R2 (def-level+kind)** funde profundidade-de-presença e kind terminal num único
símbolo por ocorrência: `{cut@0, …, cut@(d-1), null, nan, pos_inf, neg_inf, false,
true, str, int, num}` — espírito dos definition levels do Dremel (Melnik 2010),
estendido com `null ≠ ausente` (Protobuf não tem null) e com os kinds especiais do
DatasetH. Arrays rasos ganham canal de contagem (ausente ≠ `[]` via marca, não
sentinela no count). Payloads (str/int/num) vão pro canal de texto por coluna —
**generaliza o HK do lab-irmão** (`1921-typed-header-domain`) para topologia.

## O que passou (RT sob o oráculo semântico)

- contra-exemplo killer: 4 linhas `{}` / `{b:{}}` / `{b:{c:null}}` / `{b:{c:NaN}}` —
  R1 colide (refutado), R2 distingue as 4 (`cut@0`/`cut@1`/`null`/`nan`);
- `opt-chain-specials`: cadeias opcionais 3 níveis com `-0.0`, `NaN`, `Inf`, `"NaN"`;
- `ragged-arrays-specials`: `[]` vs ausente vs `[NaN,-Inf]` vs `["NaN",null]`;
- `mixed-regular-100`: 100 linhas regulares com NaN periódico e arrays ragged.

## Limites (registrados)

- **Escopo**: objetos aninhados opcionais + arrays RASOS de escalares. Objeto-em-array
  e array-de-array na forma regular = peça seguinte (repetition levels completos).
- **Bytes são estimativa**: streams de marca reportados como b4-est (4 bits/símbolo,
  `d + 9 ≤ 16` vale até profundidade 7; mais fundo → b8 ou separar def de kind).
  Packing real = território `bN`/V2-L; payload medido como texto.
- Sintético, N=1 lab; sem decisão de gramática (P5).

## Rodar

```powershell
python experiments/lab/dirty/2026-07-13-1955-dataseth-regular-def-levels/run.py
```

Artifacts: `01-r1-counterexample.txt` (a colisão), `02-r2-streams-sample.txt` (streams
inspecionáveis), `03-bytes-comparison.txt` (após RT verde), `04-rt-counterproof.txt`.
Ver [result.md](result.md).
