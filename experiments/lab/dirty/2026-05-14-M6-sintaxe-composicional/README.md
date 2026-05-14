# M6 — Sintaxe composicional (revisao M4.C1' e M2.A)

**Data**: 2026-05-14
**Estado**: e' (em curso)
**Sucede**: [M5](../2026-05-14-M5-pilha-M2A-M4C1p/) — apos critica do
user revelar:
  (1) M2.A com preambulo era regressao; inline economiza 2+len(N)
      bytes/alias
  (2) M4.C1' `~tupla~` tem close redundante; open-only `~tupla`
      economiza 1 byte/alias
  (3) Markers entre refs sao OPERADORES composicionais: `,` = concat
      efemero, `~` = concat + cria novo ref auto-nomeado. Generaliza
      tudo e expoe a hierarquia natural do alg16.

## Perguntas

- M2.A inline (sem preambulo) reverte a "dominacao" de M5?
- M4.C1' open-only economiza o byte projetado?
- Sintaxe composicional realmente domina por R bytes/alias?

## Hipoteses (algebra de marcadores-multiplo-proposito.md)

| Sintaxe | 1a aparicao | reuso | savings/reuso |
|---|---|---|---|
| M1.E (baseline) | Lr_inline | Lr_inline | 0 |
| M4.C1' atual | Lr_inline + 2 | 1 + len(N) | Lr_inline - 1 - len(N) |
| M4.C1' open-only (M6.B) | Lr_inline + 1 | 1 + len(N) | Lr_inline - 1 - len(N) |
| **Composicional (M6.C)** | **Lr_inline** | **len(N)** | **Lr_inline - len(N)** |

Estimativa D1-D4:
- M4.C1' atual: 636
- M6.B (open-only): ~629 (-7)
- M6.C (composicional): ~615 (-21)

## Estrutura

```
M6-sintaxe-composicional/
  data/                         (D1-D4 canonicos)
  M1-E-range-baseline/          (referencia)
  M4-C1p-batch-subsequencias/   (referencia — M4.C1' atual)
  M6-A-m2a-inline/              (M2.A sem preambulo)
  M6-B-m4c1p-open-only/         (M4.C1' sem close marker)
  M6-C-composicional/           (`~` cria ref, `,` nao; range cria)
  resultados/                   (matriz consolidada)
  notas/                        (analise pos-rodagem)
```

## Decisoes de design M6.C

- **Pairwise (binary left-assoc)**: chain `a~b~c` cria 2 refs
  (`a~b` → X, `X~c` → Y)
- **Range cria ref**: `a..b` auto-nomeia como composicao
- **Reuso bare**: ref id sem prefixo (`13` em vez de `&1`)

## Direcoes registradas (nao M6)

- **Nos pos-construcao com literal+ref**: composicao pode envolver
  novos literais + refs existentes (ver
  [`../notas/marcadores-multiplo-proposito.md`](../notas/marcadores-multiplo-proposito.md)).
  Adiado pro protótipo se sintaxe simples mostrar gap.

## Resultados

| Sintaxe | D1 | D2 | D3 | D4 | Total | vs M1.E |
|---|---:|---:|---:|---:|---:|---:|
| M1.E baseline | 149 | 180 | 206 | 141 | 676 | 0 |
| M4.C1' atual | 138 | 174 | 196 | 128 | 636 | -5.9% |
| M6.A (M2.A inline) | 142 | 177 | 203 | 142 | 664 | -1.8% |
| **M6.C (composicional)** | **128** | **175** | **194** | **122** | **619** | **-8.4%** |

RT 16/16 OK. M6.C **-17 bytes** sobre M4.C1' atual.

Detalhes: [`resultados/matriz_comparativa.md`](resultados/matriz_comparativa.md).

## Conclusoes

**M6.C composicional supera M4.C1' atual.** Algebra previa -R bytes/comp;
empirico -17 bytes total em D1-D4 (~3-4 bytes/composicao em media).

**M6.A (M2.A inline) ainda dominada** por M4.C1' atual e por M6.C, mas
ganho real (-2 bytes vs M5) e' menor que algebra previa pq M2.A detector
e' sufix-only (coverage limitada).

**Direcao prototipo**: sintaxe core = M1.E + M6.C composicional. M4.C1'
obsolescido.

Detalhes: [`notas/conclusoes_M6.md`](notas/conclusoes_M6.md).
