---
title: "BUG-ENCODE-PRIMEIRO-VALOR-NULO: `None` na primeira linha estoura o encode multi-col"
status: open
priority: P1
severity: R1 (erra alto, com excecao crua em vez de fail-loud; entrada comum em dado real)
created: 2026-08-24
updated: 2026-08-24
gate: `src/tcf` so' com aprovacao (I5). Nada soldado.
blocked-by: []
related:
  - src/tcf/multi/split.py
  - src/tcf/multi/core.py
  - experiments/lab/dirty/2026-08/2026-08-24/2026-08-24-0500-lazy-oportunista/
---

# BUG-ENCODE-PRIMEIRO-VALOR-NULO

## O que acontece

Numa tabela multi-coluna, se o **primeiro** valor de qualquer coluna for `None`, o
`encode` levanta `TypeError` cru, vindo de dentro do codec:

```python
encode({"uf": ["SP", "RJ"], "v": [None, 1]})
# TypeError: expected string or bytes-like object, got 'NoneType'
```

## O gatilho e' a POSICAO, nao a presenca do nulo

Medido em 2026-08-24:

| entrada | resultado |
|---|---|
| `None` na posicao 0 | **TypeError** |
| `None` na posicao 1 | OK, 95 B |
| `None` na ultima posicao | OK, 92 B |
| coluna inteira `[None] * 60` | **TypeError** |
| single-col `[None] * 60` | OK, 13 B, round-trip fecha |

Nulo no meio da coluna funciona e faz round-trip. Só a primeira linha derruba.

## Causa

[`src/tcf/multi/split.py:32`](../src/tcf/multi/split.py):

```python
toks0 = _DIGITS.split(values[0])
```

O candidato `%split` inspeciona `values[0]` para deduzir o template, sem guarda de
`None`. Como `_best_of` avalia o split para **toda** coluna na competicao
`min(tcf, raw, dict, split)`, basta o primeiro valor ser nulo para a competicao inteira
morrer, mesmo que o split fosse perder para outro candidato.

Os outros candidatos ja' tem a guarda: `_fallback_safe` recusa coluna com `None`. O
split ficou de fora dessa protecao.

## Por que importa

Primeira linha com campo ausente e' entrada comum em dado real (CSV exportado, JSON de
API, planilha). O erro nao diz qual coluna nem qual linha, e nao vem do encoder: vem de
um `re.split` tres camadas abaixo.

## Criterio de aceite

- [ ] `encode` com `None` na primeira linha funciona, ou recusa com mensagem que nomeia
      a coluna e a razao. Escolher qual e' decisao do dono do projeto.
- [ ] O comportamento nao depende da POSICAO do nulo: mesma entrada, mesma resposta.
- [ ] Round-trip preservado onde hoje ja' funciona (nulo no meio), sem re-pin de gate.
- [ ] Teste cobrindo posicao 0, meio, fim, e coluna inteiramente nula.

## Descoberta

Achado por acaso em 2026-08-24, montando as bordas do lab
[`2026-08-24-0500-lazy-oportunista`](../experiments/lab/dirty/2026-08/2026-08-24/2026-08-24-0500-lazy-oportunista/):
o caso `tudo-nulo` derrubou o lab antes de chegar ao atalho que ele ia medir.
