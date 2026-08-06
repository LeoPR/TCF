# ADR-0037 — denso b2 ternário: domínio IMPLÍCITO para bool com null

- **Status**: aceito (weld 2026-07-31)
- **Escopo**: single-col tipado bool (`#TCF.8b`), modo denso no índice 7. **Fora**: tags
  `n`/`s` (enum tipado numérico = T-BN-TIPADO), `.8M`, `.8H`, rota flat.
- **Interage com**: ADR-0029 (header posicional — o modo mora no índice 7),
  ADR-0032 (discriminador/fail-loud), ADR-0035 (polaridade — candidata irmã no mesmo
  `min()`), ADR-0036 (bN de domínio **declarado** — a alternativa para domínio
  NÃO-conhecido a priori).

## Contexto

`bool + null` (ternário) caía no core: **546 B** para n=200. O denso `b1` é bool-**sem-null**
por construção — 1 bit só tem 2 estados, e o trio `{null, false, true}` não cabia.

O lab `2026-07-28-0829` mediu a saída pelo bN tipado com domínio **declarado**
(`#TCF.8bB2c8` + 3 linhas de domínio): **94 B**. Mas `true`/`false`/`null` são tipos
**puros do JSON** — o domínio é conhecido a priori, e declará-lo é redundante. O próprio
`b1` já tinha estabelecido o precedente: domínio implícito congelado (`false=0, true=1`),
47 B para n=200, sem uma linha de domínio no wire.

A pergunta que ficou da ADR-0036 era, então, ao contrário: não "como declarar o domínio na
rota tipada", e sim **"quando o domínio pode NÃO viajar"**. Resposta: quando ele é fixo por
tipo — exatamente o caso da família bool.

## Decisão

`#TCF.8b2<n-hex>\n<b64>` — mesma grafia posicional do `b1`: tag `b` no índice 6, modo `2`
(2 bits/símbolo) no índice 7, `n` em hex, payload base64 de índices empacotados
(`pack_w(idx, 2)` — o mesmo `bitpack` soldado do `b1`).

**Domínio implícito, congelado e canônico:**

```
0 = null   1 = false   2 = true   3 = RESERVADO (fail-loud no decode)
```

- **Cobertura**: qualquer subconjunto de `{null, false, true}` com algum `null`. Bool puro
  sem null segue no `b1` (1 bit domina 2 bits — o FLOOR garante); `k≤1` sem null segue no
  core (RLE).
- **Fail-loud herdado do denso**: base64 estrito (`validate=True`), payload de tamanho
  EXATO `ceil(2n/8)`, padding não-zero rejeitado pelo `unpack_w`; acrescenta-se o símbolo
  `3` rejeitado ("fora do domínio ternário — wire adulterado").
- **Encoder**: mais um candidato no mesmo `min()` da rota tipada — FLOOR nunca-pior, sem
  caminho à parte.

### A ordem dos slots

`null=0` segue a convenção já soldada do `dominio_bn` (slot 0 pré-alocado é do null) e fixa,
para a família bool, o "null=0, e depois?" do T-FLOAT-SLOTS: **null=0, valores na ordem de
declaração do tipo**. A alternativa `false=0, true=1, null=2` (bit-compatível com o `b1`)
foi descartada: o FLOOR já emite `b1` para bool puro, então a compatibilidade de bits não
comprava nada — e a consistência cross-formato com o slot 0 do `dominio_bn` vale mais.

## Medição

Lab `experiments/lab/dirty/2026-07/2026-07-31/2026-07-31-2350-denso-b2-ternario/`:

| coluna | core | bN tipado (domínio declarado) | **b2** |
|---|---:|---:|---:|
| `bool-null` (n=200) | 546 | 94 | **79** |
| `bool-null-esparso` (n=200) | 601 | 94 | **79** |
| Adult ternário (n=100, real-ish) | 232–250 | 61 | **47** |

- Os 15 B de diferença sobre o bN tipado são exatamente o domínio declarado que deixou de
  viajar. A estimativa prévia (header 11 B + b64 de 50 B ≈ 79 B) bateu exata.
- **Vence o core em TODO o intervalo medido, inclusive n=3** (14 vs 21 B) — o domínio
  implícito zera o custo fixo que fazia o bN tipado perder em n pequeno.
- RT estrito (valor **e** tipo **e** comprimento) em todas as colunas do lab; fail-loud 3/3
  (símbolo 3, payload truncado, b64 não-canônico).

## Consequências

- Suíte **1077 passed**; baselines intactos (D1-D9 1545, D17a 300, real-world 89430) — os
  gates são rota flat (`list[str]`), zero colunas tipadas.
- **T-BN-TIPADO perde a família bool do escopo** — resta o enum tipado NUMÉRICO (int/float
  de baixa cardinalidade, ganhos −555/−519 B medidos no lab 0829).
- O modo `2` do índice 7 fica **reservado para o ternário bool**; `n`/`s` com `w≥2` seguem
  fail-loud (domínio embutido é outra grafia, não esta).
- `T-DENSO-PADDING` passa a valer para dois modos: o `b2` nasce com padding `=` como o `b1`,
  e a dedução proposta se aplica aos dois.
