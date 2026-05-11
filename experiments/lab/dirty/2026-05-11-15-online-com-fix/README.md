# 15 — online com fix dos defeitos + métrica de unidades

## Princípio / motivação

Continuação direta do [exp 14](../2026-05-10-14-online-sem-revisao/).
O exp 14 identificou 3 defeitos:

1. `no5` descartou pref(4,11) por overlap quando podia caber
2. `no6` ficou com literal `"yahoo.com"` quando `no3[-9:]` daria
   o mesmo conteúdo
3. `"joao.souz"` duplicado como literal em duas linhas

Causa raiz: heurística **descarta o menor em overlap** sem buscar
alternativa de tamanho intermediário.

Este experimento aplica **fix conservador**: quando há overlap,
considera 4 candidatos:
- (a) `pref_max + suf_reduzido` (maior suf que cabe)
- (b) `pref_reduzido + suf_max` (maior pref que cabe)
- (c) `pref_max` sozinho
- (d) `suf_max` sozinho

Escolhe a opção de maior cobertura.

**E** introduz uma **métrica nova** — "unidades de informação" —
conforme registrado em [`notas/2026-05-11-custo-de-marcadores.md`](../notas/2026-05-11-custo-de-marcadores.md):
1 ref = 1 unidade; 1 char literal = 1 unidade. Aproxima o que o
formato compacto custaria na fase prototype.

## Propósito

1. **Viabilidade do fix**: corrige os 3 defeitos identificados sem
   quebrar nada?
2. **Comparação justa**: sob a nova métrica (unidades), o online
   se mantém ou vence Re-Pair (exp 13)?

## Comparação

- **Compara com**: [13 (Re-Pair batch)](../2026-05-10-13-repair-bottomup/)
  e [14 (online sem fix)](../2026-05-10-14-online-sem-revisao/).
- **Datasets**: mesmos 3 (D2-mini, D2-completo, D4).
- **Métricas**: bytes literais + unidades de informação.

## Algoritmo

Mudança vs exp 14 em `_escolher_par`:

```
para nova string s:
    calcular best_pref (LCP máximo entre s e todas anteriores)
    calcular best_suf  (LCS máximo idem)

    se best_pref + best_suf <= len(s):
        usar direto (sem overlap)

    senão (overlap):
        candidatos = []
        # (a) mantém pref, busca maior suf que caiba
        espaco = len(s) - best_pref
        novo_suf = max sobre anteriores de LCS limitado por espaco
        candidatos += [(best_pref, novo_suf)]
        # (b) mantém suf, busca maior pref que caiba
        análogo simétrico
        # (c) só pref
        # (d) só suf
        escolher candidato com maior cobertura (tie: maior pref)
```

Custo adicional: O(N · max_len) por overlap.

## Resultado observado

Roundtrip **3/3 OK**.

### Tabela 1 — Bytes literais

| Dataset | exp 13 | exp 14 | **exp 15** | vs 14 | vs 13 |
|---|---:|---:|---:|---:|---:|
| D2-mini | 192 | 198 | **193** | -5 | +1 |
| D2-completo | 447 | 463 | **441** | -22 | **-6** |
| D4 | 424 | 399 | **399** | 0 | -25 |

Exp 15 venceu exp 14 em D2 (5 e 22 bytes). Manteve D4 (já estava
ótimo). Venceu também exp 13 em D2-completo e D4. Empate técnico
em D2-mini (+1 byte).

### Tabela 2 — Unidades de informação

| Dataset | exp 13 (Re-Pair) | **exp 15 (online+fix)** | delta |
|---|---:|---:|---:|
| D2-mini | 70 | **47** | **-23 (-33%)** |
| D2-completo | 124 | **78** | **-46 (-37%)** |
| D4 | 105 | **75** | **-30 (-29%)** |

**Exp 15 vence Re-Pair em unidades nos 3 datasets** com margens
grandes (29-37%).

A diferença entre as 2 métricas revela: a aparente vantagem do
Re-Pair em bytes literais (que existia em D2 do exp 14) vinha da
**sintaxe verbosa** do `noN[a:b]` (9-12 chars) vs `RN` (3 chars
no Re-Pair). Em unidades de informação, o online produz **estrutura
mais econômica** porque cada string vira poucos tokens (refs +
literais curtos).

### TCF D2-mini — antes e depois do fix

**Exp 14 (com defeitos)**:
```
no5: "joao.souz" + no2[-13:]              ← literal duplicado
no6: no4[0:11] + "yahoo.com"              ← "yahoo.com" duplicado
```

**Exp 15 (fix aplicado)**:
```
no5: no4[0:11] + no2[-11:]                ← pref no4 + suf no2 (sem overlap)
no6: no4[0:11] + no3[-9:]                 ← pref no4 + suf no3 (sufixo menor que LCS max)
```

`no5` e `no6` viraram **2 refs cada, sem literal**. Antes eram
~10-11 unidades por linha.

## Limitações

- O fix é **conservador**: gera 4 candidatos por overlap. Há
  combinações ainda não exploradas (ex: `pref_id_A + suf_id_B`
  onde A != B com tamanhos diferentes simultaneamente).
- Ainda **sem revisão retroativa**. Defeito C (literal "joao.souz"
  ainda aparece em no4 como `"joao.souz" + no1[-11:]`) persiste —
  exigiria reabrir no4 quando aparece um segundo `joao.souz`.
  Fica para exp 16 (Opção B do trade-off triangular).
- 3 datasets pequenos. Não fala sobre escala.
- Custo computacional O(N²·max_len) — mesmo do exp 14.
- Não testado em datasets onde overlap é raro (D4 do exp 14 já
  estava no ótimo).

## Como reproduzir

```bash
cd experiments/lab/dirty/2026-05-11-15-online-com-fix
python run.py
```

2 tabelas + roundtrip 3/3. Debug em `debug-output/`. TCFs em
`encoded/`.

## Contexto teórico

Métrica nova ("unidades de informação") motivada por discussão
registrada em [`../notas/2026-05-11-custo-de-marcadores.md`](../notas/2026-05-11-custo-de-marcadores.md).
Sumário: refs/índices/nós são **elásticos** (1-2 bytes na fase
prototype); dados literais são fixos. Comparar algoritmos em bytes
verbosos hoje pode distorcer; em unidades aproxima o regime
compacto futuro.
