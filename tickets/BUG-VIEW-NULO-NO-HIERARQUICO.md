---
title: "BUG-VIEW-NULO-NO-HIERARQUICO: um None numa coluna densa tira a tabela inteira do view()"
status: open
priority: P1
severity: "R1 (recusa indevida na API pública; o dado está íntegro e o decode lê)"
created: 2026-08-28
updated: 2026-08-28
gate: "correção em src/tcf só com aprovação explícita do owner (I5); o conserto mexe no WIRE, logo exige re-pin de baselines (ADR-0024 permite: minors #TCF.N são marcadores de dev)"
blocked-by: []
related: [
      src/tcf/hierarchical.py,
      src/tcf/view.py,
      tickets/BUG-VIEW-RECUSA-COLUNA-TIPADA.md,
      tickets/T-CODE-VIEW-SUBTCF-RECORTE.md,
      experiments/lab/dirty/notas/2026-08/2026-08-27-consistencia-tres-familias.md,
]
---

# BUG-VIEW-NULO-NO-HIERARQUICO

**[probatório → execução]** Uma tabela retangular perfeita, com um `None` numa coluna, sai
do `encode` em `#TCF.8H` e é **recusada inteira** pela `view`, que a chama de ragged. O
`decode` lê a mesma tabela sem reclamar, e **a mesma tabela** na família `.8M` é consultável
normalmente.

Divergência #6 da [auditoria de consistência de
2026-08-27](../experiments/lab/dirty/notas/2026-08/2026-08-27-consistencia-tres-familias.md),
registrada aqui por não ter ticket próprio. Irmã de
[`BUG-VIEW-RECUSA-COLUNA-TIPADA`](BUG-VIEW-RECUSA-COLUNA-TIPADA.md), que era o mesmo tipo de
recusa por outra causa e já fechou.

## Repro mínimo

```python
from tcf import decode, encode, view

w = encode([{"a": "x"}, {"a": None}])      # '#TCF.8Ha?:5'

decode(w)                                   # [{'a': 'x'}, {'a': None}]   correto
view(w).select()                            # ValueError: `view()` precisa de uma tabela
                                            # retangular: a coluna 'a' é opcional (ragged).

view(encode({"a": ["x", None]})).select()   # [{'a': 'x'}, {'a': None}]   a MESMA tabela, em .8M
view(encode([{"a": "x"}, {"a": "y"}])).select()   # funciona: o que muda é só o None
```

O controle da última linha é o que separa causa de coincidência: tire o `None` e o mesmo
wire, na mesma família, é consultável.

## Causa

O `encode` de dataset emite a flag `?` (masked) para **duas coisas diferentes**: "esta chave
não existe nesta linha" e "esta chave existe e vale nulo"
([`hierarchical.py`](../src/tcf/hierarchical.py), no emit e no parse).

O **corpo** distingue as duas (`\0` para nulo, `-` para ausente, conferido em
`'#TCF.8Hc?:5\n\0\n-\n'`), e é por isso que o `decode` é lossless. Mas a distinção **não
sobe ao header**, e a `view` lê só a flag ([`view.py`](../src/tcf/view.py), no gate de
retangularidade) e recusa antes de olhar o corpo.

Detalhe que barateia o conserto: a `view` **já tem o caminho certo implementado**
(`elem_null` + `_emask`). Ele é inalcançável pela rota `list[dict]` porque o encoder nunca
produz `elem_null` nesse nível.

## Alcance

29 wires do corpus de paridade, **19,3% da família `.8H`**. É a maior fatia de recusa
indevida medida na auditoria. Coluna densa com nulo é a forma mais comum de dado real que
existe, então a borda é de nome só.

## O certo

**Nulo não é ausência**, e essa é invariante do projeto, não preferência: uma coluna densa
com nulos é retangular e tem que ser consultável. É a mesma frase que fechou
[`BUG-VIEW-UMA-STRING-VAZIA`](BUG-VIEW-UMA-STRING-VAZIA.md) do lado do vazio.

## Custo, e por que não fica nas ondas baratas

Não há conserto só na `view`, porque a informação que ela precisa não está no wire que ela
recebe. As duas saídas mexem no formato:

| saída | o que muda | consequência |
|---|---|---|
| header ganha como separar "opcional" de "denso com nulos" | grafia do `.8H` | re-pin de baselines |
| `encode` de dataset passa a emitir `elem_null` neste caso | wire emitido | re-pin de baselines |

Por isso ficou como onda 4 na ordem de ataque, depois das que não tocam o wire. ADR-0024
já autoriza o re-pin: minors `#TCF.N` são marcadores de desenvolvimento, não compromisso
de compatibilidade.

## Critérios de aceite

- [ ] `view(encode([{"a": "x"}, {"a": None}]))` responde, e `select()` devolve o mesmo que
      o `decode`.
- [ ] Chave **ausente** de verdade (`[{"a": 1}, {"b": 2}]`) continua sendo recusada pela
      `view` como ragged, com a mensagem atual. A correção separa os dois casos; não pode
      passar a aceitar ragged.
- [ ] A `.8H` e a `.8M` respondem a mesma coisa para a mesma tabela lógica com nulos, em
      `select`, `count`, `distinct` e `group_count`.
- [ ] Os 29 wires do corpus de paridade passam a ser consultáveis, e o número é conferido
      por execução, não estimado.
- [ ] Lab de evidência em disco (I2) com o antes e o depois, no padrão canônico.
- [ ] Baselines re-pinados com a razão registrada, e o CHANGELOG anotando a mudança de wire.
- [ ] Suíte completa verde.
