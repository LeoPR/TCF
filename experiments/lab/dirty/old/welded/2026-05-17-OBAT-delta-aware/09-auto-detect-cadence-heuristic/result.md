# Resultado — Sub-exp 09 (H-DA-09b auto-detect cadence)

**Data**: 2026-05-17
**Estado**: concluido
**Plano**: [README.md](README.md)
**Tabela**: [summary.md](summary.md)

## Conclusao executiva

**H-DA-09b CONFIRMADA-EMPIRICA.** Heuristica simples (length
uniformity + LCP+LCS ratio >= 0.7) acerta 18/20 datasets:
- Evita TODAS as regressoes catastroficas de always-on (D5 +203B,
  D6 +67B, D7 +100B)
- Captura QUASE TODOS os ganhos (mantem -92B em D9, -49B em D11d/f/g/h,
  -32B em D16c, etc.)

| Pipeline | Total bytes | vs baseline |
|---|---:|---:|
| Baseline | 2770 | — |
| Always-on (sub-exps 04/06) | 2619 | -5.5% |
| **Auto-detect (este)** | **2272** | **-18.0%** |

Auto-detect **3x melhor** que always-on no total.

## Tabela completa (todos 20 datasets)

| Dataset | det? | baseline | always-on | auto | ao-bl | au-bl |
|---|---|---:|---:|---:|---:|---:|
| D1-emails-simples | off | 118 | 104 | 118 | -14 | 0 ← **miss** |
| D2-emails-quote-id | off | 166 | 169 | 166 | +3 | 0 |
| D3-stress-substring | off | 177 | 185 | 177 | +8 | 0 |
| D4-caos-mix | off | 113 | 113 | 113 | 0 | 0 |
| **D5-padroes-multiplos** | off | 281 | 484 | 281 | **+203** | **0** ← avoided! |
| D6-poucos-em-ruido | off | 287 | 354 | 287 | +67 | 0 ← avoided |
| D7-aninhamento | off | 215 | 315 | 215 | +100 | 0 ← avoided |
| D8-cabeca-cauda | on | 100 | 100 | 100 | 0 | 0 |
| D9-frequencia-alta | on | 158 | 66 | **66** | -92 | **-92** ← captured |
| D11a-datas-dia | on | 87 | 71 | 71 | -16 | -16 |
| D11b-datas-borda | off | 173 | 153 | 173 | -20 | 0 ← **miss** |
| D11c-datas-mensal | on | 109 | 72 | 72 | -37 | -37 |
| D11d-datetime-min | on | 110 | 61 | 61 | -49 | -49 |
| D11e-datetime-mensal | on | 121 | 84 | 84 | -37 | -37 |
| D11f-datetime-ms | on | 115 | 66 | 66 | -49 | -49 |
| D11g-datetime-us | on | 120 | 71 | 71 | -49 | -49 |
| D11h-datetime-ns | on | 123 | 74 | 74 | -49 | -49 |
| D16a-ids-3digits | off | 65 | 11 | 11 | -54 | -54 |
| D16b-ids-4digits | on | 62 | 28 | 28 | -34 | -34 |
| D16c-ids-prefixados | on | 70 | 38 | 38 | -32 | -32 |

RT 20/20 OK em ambos always-on e auto.

## Casos onde heuristica falha

### Misses (heuristica disse "off" mas always-on ganhava)

**D1-emails-simples** (-14B perdidos):
- Reason: lengths variam entre emails (nomes diferentes)
- Always-on funcionava porque shape-preserve fez OBAT usar refs
  consistentes apesar de variacao
- Heuristica de "lengths uniformes" rejeita esse caso

**D11b-datas-borda** (-20B perdidos):
- Reason: lengths variam (datas como "2024-02-28" vs "2024-02-29"
  vs com timestamp diferente)
- Mesma logica: always-on cria pattern parallel beneficial mesmo
  sem strict cadence

### Anti-correlacao com sub-exp 05

D16a foi marcado "off" (LCP=2 < threshold*3=2.1) mas D16a beneficia
de HCC fork sozinho (-54B). Como auto-detect usa OBAT canonical
quando "off", D16a ainda ganha (HCC fork independe de OBAT decision).

Comportamento correto pra D16a: hint nao ajuda em qualquer caso
(OBAT canonical nao cria refs). Auto-detect e' neutro aqui.

## Confirmacao da heuristica (analise dataset-por-dataset)

| Dataset | det? | Tipo decoded | Auto-detect correto? |
|---|---|---|---|
| D1 | off | emails (variavel) | **NAO** (perdeu -14B) |
| D2 | off | emails+apos (variavel) | sim (regressao evitada) |
| D3 | off | URLs (variavel) | sim |
| D4 | off | caos | sim |
| D5 | off | misto | sim (regressao GRANDE evitada) |
| D6 | off | timestamps unicos | sim |
| D7 | off | aninhamento | sim |
| D8 | on | prefix/X/suffix | sim (uniforme) |
| D9 | on | wrapper | sim (CAPTURA -92B) |
| D11a | on | datas uniformes | sim |
| D11b | off | datas com bordas | **NAO** (perdeu -20B) |
| D11c-h | on | datetime uniforme | sim |
| D16a | off | IDs 3-digit | parcial (OK, hint nao ajudaria) |
| D16b | on | IDs 4-digit | sim |
| D16c | on | IDs prefixados | sim |

**Acertos**: 18/20.
**Misses**: 2/20 (D1, D11b — ambos onde lengths variam mas hint ainda ajudaria)

## Ressalvas conceituais (importante!)

1. **Heuristica e' arbitraria**. Threshold 0.7 e n_sample=5 sao
   escolhas. Outros valores dariam resultados diferentes.
2. **20 datasets sao todos sinteticos**. Generalizacao pra
   real-world TPC-H, Adult Census nao testada.
3. **Detector pode ser fooled**: dataset adversarial que parece
   cadenciado nas primeiras 5 strings mas vira caos depois →
   regressao silenciosa.
4. **Misses sao reais**: -34B em D1+D11b perdidos. Pode ser ok
   no balanco geral mas e' perda concreta.
5. **N=20 datasets**: ainda pequena amostra estatistica.

## Status H-DA-09b no roadmap

**confirmada-empirica** — heuristica funciona melhor que always-on
em datasets sinteticos. Generalizacao real-world pendente.

## Recomendacao operacional

Pipeline final pra dirty lab:
```python
strings = dedupe(rows)
detected, info = detect_cadence(strings, threshold=0.7)
tokens = processar_with_hint(strings, prefer_shape_consistency=detected)
body = HCCForkSeqRLE().encode(rows, strings, tokens, header)
```

Single-pass. Memoria O(N) onde N=5 (heuristica). Type-agnostic
(usa so' propriedades estruturais).

## Hipoteses decorrentes

- **H-DA-09c**: tunar threshold (0.5, 0.6, 0.8, ...) — pode capturar
  D1/D11b? Risco de pegar regressoes em D2/D3
- **H-DA-09d**: heuristica multivariada (lengths + LCP+LCS + variance)
  — mais robusta?
- **H-DA-09e**: re-avaliar a cada N strings durante processamento
  — adaptativo (mas viola single-pass se nao for cuidadoso)

Registradas. Nao testar agora.

## Arquivos

```
09-auto-detect-cadence-heuristic/
├── README.md
├── auto_pre.py        (detect_cadence)
├── run.py             (3 pipelines em 20 datasets)
├── summary.md
├── result.md          (este)
└── outputs/<ds>/
    ├── detect-result.txt        (json: detected + info detalhado)
    ├── body-baseline.tcf
    ├── body-alwayson.tcf
    ├── body-auto.tcf
    └── stats.txt
```
