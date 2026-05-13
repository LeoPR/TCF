# Stress-test rodada 2 (apos M1.D)

Datasets descartaveis em `data_extra/` (DE5/DE6 adicionados aos
DE1-DE4) rodados via `run_lote_extra.py`. RT 30/30 OK.

## Matriz completa (6 datasets x 6 sintaxes)

| dataset | M1.A | M1.A' | M1.B | M1.E | M1.C | **M1.D** |
|---|---:|---:|---:|---:|---:|---:|
| DE1-adversarial-E | 53 | 53 | 63 | 53 | 53 | **78** |
| DE2-favoravel-E | 132 | 132 | 132 | 82 | 82 | **85** |
| DE3-adversarial-C | 101 | 100 | 100 | 96 | 96 | **121** |
| DE4-favoravel-C | 84 | 77 | 77 | 77 | 69 | **110** |
| DE5-adversarial-D | 54 | 54 | 64 | 54 | 54 | **78** |
| DE6-favoravel-D | 58 | 58 | 58 | 57 | 57 | **70** |

**M1.D perde em todos os 6 stress-tests.** Mesmo no DE6 (desenhado
para favorecer slice), perde 13 bytes vs M1.E.

## Por que mesmo DE6 (favoravel-D) nao salva M1.D

DE6 desenhado para minimizar refs (poucos descendentes, no fonte
com varias quebras). TCFs:

```
M1.E:
  abcd*ef*gh*ijklmn     (eid=1 — 17 chars, 3 separadores `*`)
  1..3xxxxyz            (eid=2 — pref(1,8) virou range 1..3)
  1,2xx5                (eid=3 — pref(1,6) + suf(1,2))
  1xx6,5                (eid=4 — refs simples 1 + 6,5)
  abxx7,6,5             (eid=5 — refs 7,6,5)

M1.D:
  abcdefghijklmn        (eid=1 — 14 chars, sem frag)
  1:0-8xxxxyz           (eid=2 — slice prefixo)
  1:0-6xx2:8-14         (eid=3 — perde 7 chars)
  1:0-4xx3:6-14         (eid=4 — perde 7 chars)
  abxx4:4-14            (eid=5)
```

Diferenca por eid: M1.D economiza 3 em eid=1 (sem fragmentar) mas
perde 7+7+1+1 nos descendentes = +13 total.

## Diagnostico estrutural

O algoritmo do exp 16 (`processar`) garante que descendentes
referenciam frags **consecutivos** do no fonte (porque pref/suf
sao contiguos). Isso significa:

> **Refs de pref/suf SEMPRE viram seq consecutiva de idx-frags.
> M1.E (range) comprime isso em `a..b` (2 numeros). M1.D (slice)
> tem 3 numeros fixos. Range SEMPRE vence slice nesse regime.**

Slice so' ganharia em regime onde:
1. Algoritmo gera **slice central real** (a > 0 E b < n_eid), nao
   apenas pref/suf — isso REQUER MEXER no algoritmo do exp 16, nao
   so' na sintaxe.
2. Descendente cobre regiao central que NAO e' pref+suf — caso
   raro no exp 16.

Nos canonicos D1-D4, slice central rigoroso (a > 0 E b < n) NAO
aparece — todos os slices que `slice(e,a,b)` emite sao tecnicamente
prefix ou suffix (a=0 ou b=n).

## Conclusao para M1.D

**M1.D na implementacao minimal (sem mexer no algoritmo) e'
estrutralmente dominada por M1.E** em qualquer dataset gerado pelo
algoritmo do exp 16. Razao matematica: refs consecutivas (que pref/
suf sempre produz) sao melhor comprimidas por range que por slice.

**Para M1.D virar competitivo**, precisaria:
- M1.D2: estender online.py com TokRefSlice(eid, a, b) gerado pelo
  algoritmo quando detectar trecho central reutilizado. Isso muda
  o ALGORITMO, nao so' a sintaxe. Fica fora do escopo macro M1.
- Ou: contexto onde refs consecutivas nao apareciam (datasets
  bem diferentes do regime exp 16 — caso de outro algoritmo raiz).

## Decisao apos analise rodada 2

1. **M1.D fica registrada como dimensao mapeada com perda
   estrutural** nos regimes do exp 16. RT 4/4 + 6/6 OK valida
   funcionalidade — bytes confirma trade-off ruim.
2. **Datasets DE5/DE6 ficam arquivados** em `data_extra/` (mesma
   regra de DE1-DE4: efemeros, nao entram nos canonicos).
3. **Macro M1 fechado por bytes**: M1.E e M1.C vencem (676 bytes
   nos canonicos). M1.D fica documentada como nao-competitiva neste
   regime.
4. **Pendente**: F2 (medir gzip + statefulness), F3 (substituicao),
   F4 (fechamento formal).

## Insight metodologico

A regra de ouro [(notas/regra-de-agrupamento.md)](regra-de-agrupamento.md)
fica reforcada: agrupamento (range) compete contra alternativas que
ofereçam "1 expressao por ref" (slice) porque a economia de
agrupamento se aplica POR ref agrupada. Slice e' overhead fixo,
range e' overhead variavel — variavel vence quando ha' o que
agrupar.

## Memorizado

Para futuros macros: ao propor nova sintaxe de referencia, comparar
contra range/agrupamento em regime onde refs naturais sao
consecutivas. Se nao houver caso onde refs nao sao consecutivas,
sintaxe de referencia mais rica que idx-simples provavelmente perde.
