# ADR-0038 — índice interno DEFAULT no core tipado bool

- **Status**: aceito (weld 2026-08-01)
- **Escopo**: single-col tipado bool (`#TCF.8b`), candidato **core/RLE**. **Fora**: tag `n`,
  `.8M`, `.8H`, rota flat, densos `b1`/`b2` (intocados).
- **Interage com**: ADR-0037 (a tabela congelada `null=0/false=1/true=2` que este ADR
  completa no core), ADR-0036 (precedente decodável-não-emitido do modo `C`),
  ADR-0035 (polaridade — candidata do mesmo `min()`, inerte aqui).

## Contexto

No core tipado bool, o null já viajava como `0` cru (slot 0 pré-alocado), mas `true`/`false`
viajavam como **NOMES** — `encode([True]*200)` emitia `#TCF.8b\n*200|true` (18 B). Onde o
core é o vencedor do FLOOR (coluna constante, run-heavy, flags ordenadas), cada literal de
run pagava 3–5 B de nome à toa.

A ADR-0037 congelou a tabela `null=0, false=1, true=2` para o denso b2. O core estava a um
passo de completar a mesma tabela: dois dos três slots já eram implícitos na prática (o `0`
cru do null), faltava grafar os outros dois como índice em vez de nome.

## Decisão

O render da tag `b` emite **slots congelados** — a mesma tabela do b2: `null=0` (já era a
grafia core), `false=1`, `true=2` — grafados pelo `_escape_lit` de sempre (`\1`/`\2`).

- **UMA grafia emitida** (canônica): slots. O decode aceita slots **e** nomes —
  decodável-não-emitido, mesmo contrato do modo `C` (ADR-0036): preserva wires legados e
  semeia o opt-in legível futuro (`T-TIPADO-LEGIVEL-PARAM`: o decode já está pronto, falta
  só o plumbing de encoder).
- **Inequívoco por construção**: o domínio é fechado (`true`/`false`/null), então `\1`/`\2`
  no corpo tipado-b só podem ser slots — não há leitura alternativa.
- **Sempre-é-ganho**: `\2` (2 B) ≤ `true` (4 B), `\1` (2 B) ≤ `false` (5 B) — o candidato
  core nunca piora; o FLOOR (`min()` de sempre) continua decidindo o modo.

### Por que a mesma tabela do b2

Ter **uma** tabela congelada por tipo — `null=0, false=1, true=2` — vale mais que otimizar
cada modo isolado: o core e os densos passam a falar a mesma língua de slots, e o "null=0, e
depois?" do T-FLOAT-SLOTS fica com o precedente reforçado (null=0, valores na ordem de
declaração do tipo).

## Medição

Lab `experiments/lab/dirty/2026-08/2026-08-01/2026-08-01-0037-tipado-bool-indice-default/`:

| coluna | modo | hoje (nomes) | slot | Δ |
|---|:-:|---:|---:|---:|
| `bool-constante` (n=200) | core | 18 (`*200\|true`) | 16 (`*200\|\2`) | −2 |
| `run-heavy-1` (n=200) | core | 30 | 25 | −5 |
| `runs-4` (n=200) | core | 41 | 34 | −7 |
| Adult `sex`/`class` ordenados (n=100) | core | 27 | 22 | −5 |

**Nunca pior em 11 colunas** (Δ somado −24 B). Onde o FLOOR escolhe denso (`b1`/`b2`), o
render não muda nada — o corpo core nem materializa. Caso run-heavy confirmado: o core
**vence o b2 nos dois renders** (30/25 vs 79 B) — é o nicho que o b2 não cobre.

Adversidades verificadas no lab: **polaridade inerte** (corpo bool em slots tem no máximo 2
linhas literais; 0 disparos em 11 corpos — estrutural, não amostral); **seq-RLE não dispara**
em padrão de 2 valores (delta não-uniforme); **legado decodifica**
(`#TCF.8b\ntrue\nfalse\n^1\n` → `[True, False, True]`); **fail-loud 3/3** (`\0`, `\3`, `\15`
→ `ValueError`).

## Consequências

- Suíte **1084 passed**; baselines intactos (D1-D9 1545, D17a 300, real-world 89430) — os
  gates são rota flat (`list[str]`).
- **1 pin alterado** (`tests/test_null_slot0.py`): `encode([True, None])` passou de `#TCF.8b2…`
  para `#TCF.8b\n\2\n0\n` — o core de n=2 em slots **empata** com o b2 (12 = 12 B) e o FLOOR
  fica no 1º candidato. Byte-neutro, comentado no teste.
- **Inspecionabilidade**: `*200|\2` lê pior que `*200|true` — trade-off assumido. A saída
  legível vira contrato estável de decode (nomes sempre leem) e o opt-in de grafia legível
  fica pendente em `T-TIPADO-LEGIVEL-PARAM`.
- A **família bool fecha ponta a ponta**: `b1` (sem null, alternado), `b2` (ternário denso),
  core-com-slots (constante/run-heavy) — os três regimes com uma tabela congelada só.
