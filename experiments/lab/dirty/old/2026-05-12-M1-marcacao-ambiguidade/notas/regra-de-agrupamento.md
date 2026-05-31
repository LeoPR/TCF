# Regra de ouro do agrupamento (apos M1.C)

Validacao empirica em M1 (4 micros, 4 datasets):

> **Agrupar/sumir marcadores so' compensa quando o contexto onde o
> marcador era emitido JA' tinha um separador natural.**

## Evidencia

| Micro | Tecnica | Contexto | Resultado |
|---|---|---|---|
| M1.A' | escape escopo `\<seq>` | dentro de literal nao-digit | -12 bytes (vs M1.A) |
| M1.E | range `a..b` | dentro de seq de refs | -68 bytes (vs M1.A') |
| M1.C | sumir escape | apos ref/range | 0 bytes (empate vs M1.E) |

## Por que M1.A' e M1.E ganham

- M1.A': agrupa K digitos contiguos. Esses digitos estavam INTERNOS
  ao literal. Substituir `\d\d\d` (3 marcadores) por `\ddd` (1) nao
  precisa separador novo — o literal-context ja' continha as
  fronteiras.
- M1.E: agrupa K refs consecutivas. Refs ja' eram separadas por `,`
  natural. Substituir `1,2,3` por `1..3` reaproveita a fronteira
  de inicio/fim da seq de refs.

## Por que M1.C nao ganha

- M1.C: tira `\` mas precisa adicionar `*` quando o sumido segue
  uma ref. O `\` que era marcador de DESAMBIGUACAO LOCAL vira `*`
  separador de FRONTEIRA. 1 byte trocado por 1 byte.

## Implicacao para futuras tecnicas

Ao propor nova tecnica de agrupamento/eliminacao:
1. Identificar o contexto onde o marcador atual e' emitido.
2. Checar se esse contexto JA' tinha separador natural (fronteira
   de literal, sep de refs, inicio/fim de linha).
3. Se sim: provavel ganho.
4. Se nao: provavel empate ou perda (custo de novo separador
   compensa o ganho).

Esta regra ajuda a decidir quais micros valem implementar.

## Casos futuros pra avaliar

- **B' (quote agrupada)**: `'X*Y*Z'` em vez de `'X''Y''Z'`. Contexto
  natural: dentro do bloco entre aspas. Provavel ganho.
- **Alias de tupla de refs**: `$1 = 3,5,7` declarado uma vez,
  reusado. Contexto: linhas inteiras. Provavel ganho se K
  ocorrencias >> custo de declaracao.
- **Slice arbitrario (M1.D)**: extende algoritmo. Nao e'
  agrupamento sintatico — e' nova semantica de token. Regra nao
  se aplica diretamente.
- **Marcadores binarios / outro alfabeto**: muda toda a base.
  Regra nao se aplica.

## Referencias

- [`marcadores-redundantes-agrupamento.md`](marcadores-redundantes-agrupamento.md)
  — discussao inicial.
- [`revisao-critica-M1E-output.md`](revisao-critica-M1E-output.md)
  — 3 camadas de redundancia identificadas.
- [`M1-C-sumida/README.md`](../M1-C-sumida/README.md) — caso
  concreto.
