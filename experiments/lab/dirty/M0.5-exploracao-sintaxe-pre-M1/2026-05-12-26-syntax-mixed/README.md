# 26 — sintaxe mixed (escolha por literal) vs escolha global

## Princípio / motivação

Após o exp 25 ter limpado o que não funciona, restaram apenas 2
sintaxes universais: **v4-quote-fixed** (aspas para K≥1 chars
ambíguos) e **v4-escape** (escape `\X` por char ambíguo).

A hipótese natural: uma **v4-mixed** que escolhe por literal
individualmente (escape se K≤1, quote se K≥2) deveria ganhar
porque pega o melhor de cada.

Este experimento testa essa hipótese com escopo mínimo:
**1 dataset, 3 sintaxes**.

## Dataset

`emails-quote-id.csv` — 12 strings combinando 2 fontes de
ambiguidade:

- Nomes irlandeses com `'` (apóstrofo): `d'angelo`, `o'brien`,
  `de'mello`, `m'baye`, `o'connor`, `d'arcy`
- IDs numéricos de tamanho variado (1, 2, 3 dígitos)
- 3 domínios (`gmail.com`, `hotmail.com`, `yahoo.com`)

Coleção de fragmentos literais resultantes do algoritmo:

| K (chars ambíguos) | Quantos fragmentos | Exemplos |
|---:|---:|---|
| 0 | 11 | `d'a`, `nge`, `@g`, `mail`, `.com`, `o'brien`, `@hot`... |
| 1 | 2 | `1`, `1` |
| 2 | 3 | `42`, `03`, `42` |
| 3 | 2 | `o'connor103`, `rcy256` |

## Sintaxes

| Sintaxe | Regra para literal |
|---|---|
| v4-escape | Sempre escape `\X` por char ambíguo |
| v4-q-fix | Aspas se K≥1; sem aspas se K=0 |
| **v4-mixed** | NOVA — K=0: raw; K=1: escape; K≥2: aspas |

## Resultado observado

Roundtrip 3/3 OK.

| Sintaxe | Bytes |
|---|---:|
| compact_v4_escape | 200 |
| **compact_v4_quote_fixed** | **198** |
| **compact_v4_mixed** | **198** |

**Empate entre v4-q-fix e v4-mixed.** Contra-intuitivo: v4-mixed
deveria ganhar nos fragmentos K=1 (escape 1B + sep, vs aspas
2B + 1 sep), mas não ganhou.

## Por que v4-mixed não ganhou — análise

A teoria pura (escape +1 vs quote +2) ignora o **custo de
separador `*`** entre literais consecutivos sem aspas.

### Cenário típico: literal de meio (entre 2 outros literais)

| Configuração | Aspas? | Sep antes | Sep depois | Total extra |
|---|---|---|---|---|
| v4-escape K=1 | não | `*` (1B) | `*` (1B) | escape 1 + sep 2 = **3** |
| v4-q-fix K=1 | sim (`'X'`) | `*` (1B) | nada (`'` delimita) | aspas 2 + sep 1 = **3** |
| v4-q-fix K=2 | sim | `*` (1B) | nada | aspas 2 + sep 1 = **3** |
| v4-escape K=2 | não | `*` | `*` | escape 2 + sep 2 = **4** |

**Para K=1**, escape e quote **empatam** (3 bytes extras cada).
v4-mixed escolhe escape em K=1 = mesmo custo que v4-q-fix
escolhendo quote.

Para K=2 ou maior, quote vence por 1+ byte. v4-mixed e
v4-q-fix usam quote → empate.

### Exemplo concreto

Linha 2 dos 3 TCFs (literais `lo`, `1`, `@g`):

**v4-escape**: `d'a*nge*lo*\1*@g*mail*.com` (26 chars)
- Literal `1` escapado para `\1` (1B extra)
- Separadores `*` antes e depois de `\1` (2B)

**v4-q-fix**: `d'a*nge*lo*'1'@g*mail*.com` (26 chars)
- Literal `1` em aspas `'1'` (2B extra)
- Separador `*` antes de `'1'`, mas `'` delimita depois → 0B (1B economizado)

**v4-mixed** (mesma escolha que v4-escape em K=1): igual ao v4-escape.

Ambas usam 26 chars. **Empate confirmado.**

## Insight

A "escolha por literal" só ganharia se as opções tivessem
**custos absolutos diferentes** dependendo do K. Mas a presença
do separador `*` compensa exatamente o ganho do escape sobre
aspas em K=1.

**v4-mixed não traz valor mensurável** em datasets reais com
literais ladeados por outros literais.

### Quando v4-mixed venceria

- Se o literal estivesse **no início ou fim da linha** sem
  separador (caso atípico no algoritmo do online.py)
- Se as aspas tivessem custo > 2B (não é o caso)
- Se o algoritmo emitisse literais sem outros adjacentes
  (caso raro em datasets fatorizados)

## v4-q-fix é a sintaxe vencedora

| Critério | v4-q-fix | v4-mixed |
|---|---|---|
| Bytes em emails-quote-id | 198 | 198 (empate) |
| Complexidade do encoder | 1 regra (K≥1 → aspas) | 2 regras |
| Complexidade do decoder | igual | igual |
| Robustez (`'` no literal) | OK | OK |

**Conclusão pragmática**: v4-q-fix é simples, universal e
equivalente. Não vale adicionar v4-mixed.

## Conclusões consolidadas — fim do refinamento de sintaxe

Após 5 experimentos de sintaxe (21, 22, 23, 24, 25, 26), o
panorama está claro:

| Tema | Conclusão |
|---|---|
| Sintaxe vencedora | **v4-quote-fixed** — simples, robusta, próxima do ótimo |
| Compressão vs verbose | ~50% de redução em datasets fatorizados |
| Substituição global | não compensa em datasets fatorizados (overhead do header) |
| Escolha por literal | empata com escolha única (separador compensa) |
| Próximo grande salto possível | sintaxe binária (chars Unicode reservados) ou benchmark externo |

## Direção sugerida — benchmark externo

Após este exp, **chega de mexer em sintaxe textual**. Sugiro:

**Próximo passo: benchmark externo**
- Comparar TCF (v4-q-fix) + gzip vs CSV + gzip
- Saber se o ganho de 50% em sintaxe textual sobrevive a
  compressão estatística
- Se sim: TCF compete; vale continuar
- Se não: TCF é solução para legibilidade, não densidade

Sem essa medida, refinar mais é otimização sem norte.

## Como reproduzir

```bash
cd experiments/lab/dirty/2026-05-12-26-syntax-mixed
python run.py
```

Imprime: lista de fragmentos com K, TCFs lado a lado, tabela
final.
