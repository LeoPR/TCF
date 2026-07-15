---
title: BUG-SEQRLE-RANGE-EMPTY-B — decode(encode(x)) crasha quando um afixo tem sufixo `..`/`...`
status: open
priority: P1
severity: R0
created: 2026-07-15
updated: 2026-07-15
gate: byte-canonical (toca HCC core — precisa aprovação + test_real_world_snapshots)
blocked-by: []
related:
  - src/tcf/composicional/syntax.py
  - src/tcf/composicional/hcc_seqrle.py
  - experiments/lab/dirty/2026-07-15-0125-p1-presenca-ragged-estudo/probe_realworld.py
  - tickets/T-REL-08-CLOSEOUT.md
---

# BUG-SEQRLE-RANGE-EMPTY-B — colisão do range `A..B` do seq-RLE com `..` literal em afixo

**[probatório, R0]** `decode(encode(x)) != x` (crasha) para uma entrada que o encoder público aceita
→ satisfaz o **critério 1 da regra de ROI do T-REL-08** (preempta). Pré-existente no core (afeta o
codec PLANO single/multi-col, não só a hierarquia); descoberto pelo probe real-world do P1
(receita-cnpj `nome_fantasia` com elipse `...`).

## Repro MÍNIMO (2 strings)

```python
from tcf import decode, encode
decode(encode(["ETC & TAL", "ETC & TAL..."]))
# ValueError: invalid literal for int() with base 10: ''
#   src/tcf/composicional/syntax.py:734  refs.extend(range(int(a), int(b) + 1))
```

## Caracterização (medido)

Crasha quando um valor **estende outro por um SUFIXO contendo `..`** (dois+ pontos) — o afixo é
comprimido como referência (`1...` = "fragmento 1 + `...`") e o `_parse_decl` interpreta o `..` do
sufixo como o **operador de range `A..B`**, com B vazio → `int('')`.

| entrada | resultado |
|---|---|
| `["ETC & TAL", "ETC & TAL..."]` | **CRASH** |
| `["ETC & TAL", "ETC & TAL.."]` | **CRASH** |
| `["ETC & TAL", "ETC & TAL...X"]` | **CRASH** |
| `["abc", "abc..de"]` | **CRASH** |
| `["ETC & TAL", "ETC & TAL."]` (1 ponto) | RT OK |
| `["ETC & TAL", "..ETC & TAL"]` (prefixo, não sufixo) | RT OK |
| `["ETC & TAL..."]` (valor único, sem afixo) | RT OK |
| `["casa", "casa123"]` (afixo sem `..`) | RT OK |
| `["1","2","3","4","5"]` (range numérico real) | RT OK |

## Causa (src/tcf/composicional/syntax.py:727-736)

```python
for grp in unit.split("~"):
    if ".." in grp:                      # <- casa TAMBÉM o '..' literal do sufixo do afixo
        a, b = grp.split("..")           # grp="1.." -> a="1", b=""
        refs.extend(range(int(a), int(b) + 1))   # int("") -> ValueError
    else:
        refs.append(int(grp))
```

O gramática de decl usa `..` como operador de range de referências; um afixo cujo delta/sufixo
contém `..`/`...` produz um token de decl (`1..`) ambíguo com o range. Real: texto com elipse
(`"...continua"`, `"ETC..."`) é comum → não é entrada patológica sintética.

## Escopo / impacto

- **É R0** (corrompe/crasha no domínio aceito), mas **pré-existente e independente do P1** (o codec
  plano tem o mesmo bug; o P1 só o EXPÔS via dado real). Os gates byte-canônicos atuais (D1-D9,
  retail Description, lineitem l_comment) passam porque **aquele** padrão (afixo-extensão com sufixo
  `..`) não ocorre neles — receita `nome_fantasia` ocorre.
- **Fix toca o HCC core** (`syntax.py`/`hcc_seqrle.py`) → precisa aprovação explícita do owner +
  gate `test_real_world_snapshots.py` + re-pin de baselines (ADR-0024). NÃO consertar sem isso.

## Direção de fix (a validar)

Desambiguar o `..`-range do `..`-literal na EMISSÃO (o encoder deve escapar/marcar afixo cujo
delta contém `..`, ou usar um token de range que não colida) — o decode segue o que o encode
marcar. Alternativa: o encoder NÃO comprime como afixo quando o delta contém `..` (fallback raw
para esses casos raros — mais simples, custo mínimo). Escolher por byte-custo + simplicidade.

## Critério de aceite

- [ ] Repro mínimo vira teste red→green (+ a matriz de caracterização acima).
- [ ] `test_real_world_snapshots.py` verde (incl. um snapshot que exercite `..`/`...` em free-text).
- [ ] Baselines re-pinados se o wire mudar; aprovação arquivo-a-arquivo do owner (HCC core).
- [ ] Probe PW3 do P1 (receita população inteira) passa a fazer RT após o fix.
