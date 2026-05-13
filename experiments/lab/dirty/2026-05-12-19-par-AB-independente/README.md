# 19 — par A+B independente (busca exaustiva)

## Princípio / motivação

O README do exp 15 declarou uma limitação:

> "Há combinações ainda não exploradas (ex: `pref_id_A + suf_id_B`
> onde A != B com tamanhos diferentes simultaneamente)."

Em exp 16, o `_escolher_par` fixa uma das âncoras no máximo
(best_pref ou best_suf) e procura redução só na outra. Isso é
**conservador**: nunca testa pref de tamanho intermediário de
uma string A combinado com suf de tamanho intermediário de outra
string B.

Pergunta dirigida: existe margem oculta nessa busca completa?

## Propósito

Resposta às **perguntas 1 e 4** do dirty (viabilidade técnica de
variante + comparação ponto a ponto vs exp 16). O algoritmo muda
em apenas uma função (`_escolher_par`); o restante é idêntico ao
exp 16.

## Comparação

- **Compara com**: [16 (online cleanup)](../2026-05-11-16-online-cleanup/).
  Bytes, unidades, cobertura e tempo medidos lado a lado.
- **É comparável?** Sim — mesma sintaxe de saída, mesmos
  datasets em 3 grupos:
  - G1: 3 datasets do exp 15 (D2-mini, D2-completo, D4)
  - G2: 6 famílias do exp 17 (N=12 cada)
  - G3: 4 famílias × 3 tamanhos do exp 18 (N=50, 200, 1000)

## Algoritmo

Em `_escolher_par`:

```
prefs = [(id, max_lcp) para cada anterior com max_lcp >= min_len]
sufs  = [(id, max_lcs) para cada anterior com max_lcs >= min_len]

melhor = (0, 0, 0, 0)
para cada (pid, pmax) em prefs:
    para cada (sid, smax) em sufs:
        se pmax + smax <= len(s):
            candidato = (pid, pmax, sid, smax), cobertura = pmax + smax
        senão:
            opção A: manter pmax, reduzir suf para n - pmax (se >= min_len e <= smax)
            opção B: manter smax, reduzir pref para n - smax (se >= min_len e <= pmax)
            escolher melhor entre A e B
        atualizar melhor se cobertura > anterior
também considerar: só pref, só suf, nada
```

Custo: O(|prefs| × |sufs|) por string nova. No pior caso O(N²)
por string e O(N³) total.

## Resultado observado

Roundtrip **21/21 OK**.

### G1 — Datasets do exp 15

| Dataset | bytes 19 | bytes 16 | Δ | unid 19 | unid 16 | Δ |
|---|---:|---:|---:|---:|---:|---:|
| D2-mini | 193 | 193 | 0 | 47 | 47 | 0 |
| D2-completo | 441 | 441 | 0 | 78 | 78 | 0 |
| D4 | 399 | 399 | 0 | 75 | 75 | 0 |

**Nenhuma mudança.** Os 3 datasets do exp 15 já estavam no ótimo
para essa heurística.

### G2 — 6 famílias do exp 17

| Família | bytes 19 | bytes 16 | Δ | unid 19 | unid 16 | Δ |
|---|---:|---:|---:|---:|---:|---:|
| urls | 433 | 433 | 0 | 128 | 128 | 0 |
| uuids | 563 | 563 | 0 | 430 | 430 | 0 |
| iso-timestamps | 380 | 380 | 0 | 49 | 49 | 0 |
| ips | 304 | 304 | 0 | 52 | 52 | 0 |
| cpfs | 291 | 291 | 0 | 168 | 168 | 0 |
| codigos | 307 | 307 | 0 | 38 | 38 | 0 |

**Nenhuma mudança em nenhuma família.** Em N=12 a busca exaustiva
confirma os mesmos resultados do exp 16.

### G3 — Escala (4 famílias × 3 tamanhos)

| Caso | bytes Δ% | unid Δ% | cobertura 19 | cobertura 16 |
|---|---:|---:|---:|---:|
| urls-N50, 200, 1000 | 0.0 | 0.0 | igual | igual |
| iso-N50, 200, 1000 | 0.0 | 0.0 | igual | igual |
| ips-N50, 200 | 0.0 | 0.0 | igual | igual |
| ips-N1000 | **+0.9%** | 0.0 | 96.3% | 96.3% |
| codigos-N50 | **+4.6%** | **−0.8%** | **95.0%** | 93.3% |
| codigos-N200 | **+4.6%** | **−1.2%** | **97.3%** | 95.4% |
| codigos-N1000 | **+4.2%** | **−1.1%** | **97.9%** | 95.9% |

**Padrão observado em `codigos`**: par A+B troca literal curto
("2", "3", "4") por ref a sufixo. Reduz unidades 1% e aumenta
cobertura 2 pp, **mas aumenta bytes verbosos** porque `noN[-K:]`
ocupa 9 chars e o literal `"X"` ocupa 3 chars.

Exemplo no `codigos-N0050`:

```
exp 18: no8: no4[0:13] + "2"             (16 chars)
exp 19: no8: no4[0:3]  + no6[-11:]       (22 chars)
```

Ambos = 2 unidades, mas o exp 19 paga sintaxe verbosa.

### Tempo

| Caso | t exp 19 | t exp 18 | razão |
|---|---:|---:|---:|
| urls-N1000 | 11030 ms | 3829 ms | **2.9×** |
| iso-N1000 | 65797 ms | 3431 ms | **19.2×** |
| ips-N1000 | 1081 ms | 1595 ms | 0.68× |
| codigos-N1000 | 896 ms | 1469 ms | 0.61× |

Variação grande. Em `iso`, o número de prefs/sufs disponíveis é
alto (timestamps muito parecidos), e o produto cartesiano explode.
Em `codigos` e `ips`, o filtro por `min_len=3` corta a maior
parte, e o exp 19 fica até mais rápido (variância de execução).

## Análise do resultado

A busca exaustiva mostrou que **o exp 16 já está perto do ótimo
greedy** para essa família de heurística. Em 17 dos 21 casos, os
candidatos avaliados em A+B não trouxeram nenhuma combinação
melhor que a do exp 16.

Onde o exp 19 mudou (4 casos em `codigos` + 1 em `ips-N1000`), a
mudança foi **trocar literal curto por ref**, com 3 efeitos:

- **Unidades**: pequena redução (1%) em codigos. Em ips: 0.
- **Cobertura ref%**: aumenta 2 pp em codigos
- **Bytes verbosos**: aumenta 4-5% por sintaxe `noN[-K:]` >
  `"X"`

A diferença bytes ↔ unidades é exatamente o tema da nota
[`marcadores-compactos`](../notas/2026-05-11-marcadores-compactos.md):
em sintaxe verbosa atual, ref custa 9 chars; em sintaxe compacta
futura, ref custaria 1-2 bytes e venceria o literal curto.

## Limitações

- **Não é prova de otimalidade**. A busca é greedy por string
  (escolhe melhor par dado prev_a, prev_b). Não considera o
  efeito cascata: uma escolha aqui pode habilitar melhor escolha
  adiante. Apenas revisão retroativa atacaria isso.
- **Custo O(N³)** torna o exp 19 inviável em N >> 1000 sem
  otimização.
- **min_len = 3 fixo**, como em todos os anteriores.

## Como reproduzir

```bash
cd experiments/lab/dirty/2026-05-12-19-par-AB-independente
python run.py
```

21 datasets. Output: 3 tabelas + roundtrip 21/21 + TCFs em
`encoded/`.

## Conclusões

Ver [conclusoes.md](conclusoes.md). Pontos principais:

1. **Par A+B independente não reduz unidades em nenhum caso**
   além de margem marginal em `codigos`
2. **Bytes verbosos pioram** quando troca literal curto por ref
3. **A escolha do exp 16 já é boa o suficiente** para essa
   heurística
4. **Direção honesta para a frente**: exp 20 (revisão
   retroativa). Ataca limitação **estrutural diferente** — não é
   "escolher melhor par dada uma string", é "rearranjar strings
   já emitidas quando padrão emerge".
