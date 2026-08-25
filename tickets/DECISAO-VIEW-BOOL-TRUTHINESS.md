---
title: "DECISAO-VIEW-BOOL-TRUTHINESS: int numa coluna bool passa por truthiness, e a doc promete o contrario"
status: open
priority: P3
severity: R3 (comportamento defensavel, mas inconsistente com a promessa escrita)
created: 2026-08-24
updated: 2026-08-24
gate: decisao do dono do projeto; `src/tcf` so' com aprovacao (I5)
blocked-by: []
related:
  - src/tcf/view.py
  - docs/reference/lazy-view.md
---

# DECISAO-VIEW-BOOL-TRUTHINESS

## O que acontece

Filtrar uma coluna booleana com um `int` passa por `bool(value)`, entao qualquer inteiro
diferente de zero vira `True`:

```python
v = view(encode({"ativo": [True, False, True, True], "k": [...]}))
v.where("ativo", 5)    # 3 linhas (leu como True)
v.where("ativo", -1)   # 3 linhas (leu como True)
v.where("ativo", 0)    # 1 linha  (leu como False)
```

Medido em 2026-08-24, achado por auditoria da documentacao.

## Por que e' uma decisao, e nao so' um bug

A propria referencia se compromete com o oposto, no paragrafo ao lado:

> String nao-vazia **nao** vira `True` por truthiness, que e' a armadilha classica de
> `astype(bool)` no pandas.

A protecao existe no eixo TEXTO (`"banana"` levanta `TypeError`, e so' uma lista fechada
de grafias e' aceita) e nao existe no eixo NUMERO. As duas metades do mesmo contrato
seguem regras diferentes.

## As saidas

1. **Manter e documentar** (feito por ora): e' a regra do Python, e quem escreve
   `where(col, 5)` numa coluna bool provavelmente errou a coluna, nao o valor. A doc
   passou a dizer isso explicitamente.
2. **Restringir a 0 e 1**, coerente com a lista fechada do texto: qualquer outro inteiro
   levanta `TypeError` dizendo que a coluna e' booleana. Fica igual ao PostgreSQL, que e'
   o espirito que o paragrafo invoca.
3. **Recusar int por completo** numa coluna bool, exigindo `True`/`False`.

A opcao 2 e' a que fecha a inconsistencia sem tirar conveniencia real: `0` e `1` sao
grafias que a lista de texto ja' aceita (`"0"`, `"1"`).

## Criterio de aceite

- [ ] O contrato de coercao segue a MESMA regra nos dois eixos, ou a diferenca esta'
      escrita como decisao deliberada.
- [ ] Teste cobrindo `0`, `1`, `5`, `-1` e `True`/`False` numa coluna booleana.
- [ ] Sem re-pin de gate byte-canonico (a rota e' read-only).

## Descoberta

Auditoria da documentacao do view, 2026-08-24: cada afirmacao da reference foi testada
por execucao. Este foi um dos 13 pontos em que o texto e o codigo discordavam.
