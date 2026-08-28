---
title: "BUG-VIEW-COLUNA-VAZIA-UNICO-FANTASMA: distinct e n_unique inventam um elemento em coluna de 0 linhas"
status: open
priority: P2
severity: "R1 (resposta errada e silenciosa na API pública, em entrada de borda)"
created: 2026-08-26
updated: 2026-08-26
gate: "correção em src/tcf só com aprovação explícita do owner (I5)"
blocked-by: []
related: [
      src/tcf/view.py,
      src/tcf/multi/dict_v2b.py,
      src/tcf/decoder.py,
      tickets/BUG-VIEW-UMA-STRING-VAZIA.md,
      tickets/T-CODE-VIEW-SUBTCF-RECORTE.md,
      experiments/lab/dirty/2026-08/2026-08-26/2026-08-26-0300-tres-familias/,
]
---

# BUG-VIEW-COLUNA-VAZIA-UNICO-FANTASMA

**[probatório → execução]** Numa coluna de **zero linhas**, `distinct` e `n_unique`
respondem como se houvesse um elemento, a string vazia. `decode`, `count`, `select` e
`group_count` acertam.

Não é regressão: a rota `.8H` de antes errava igual, e em `group_count` errava mais. O que
mudou em 2026-08-26 é que o defeito **entrou no caminho onde ele não podia estar**, e ganhou
uma inconsistência interna nova.

## Repro

```python
from tcf import encode, view

w = encode({"a": []})          # '#TCF.8M@a\n0\n'

view(w).count()                # 0     certo
view(w).select("a")            # []    certo
view(w).group_count("a")       # {}    certo

view(w).distinct("a")          # ['']  ERRADO, a verdade é []
view(w).n_unique("a")          # 1     ERRADO, a verdade é 0
view(w).distinct(["a"])        # []    CERTO, no mesmo objeto
```

A última linha é a parte nova: **a mesma pergunta, escrita de dois jeitos, dá respostas
diferentes**. Antes da mudança de rota as duas grafias erravam juntas, o que era errado
porém coerente.

## Causa

Duas camadas, e a de baixo é compartilhada com `BUG-VIEW-UMA-STRING-VAZIA`.

**Embaixo:** `_decode_column("")` devolve `[""]`, e não `[]`. É a mesma ambiguidade de corpo
vazio daquele ticket, um nível abaixo: aqui o corpo vazio é a **tabelinha** do slot `@`.

**Em cima:** `_decode_v2b` (`src/tcf/multi/dict_v2b.py`) lê `ntable=0`, chama
`_decode_column("")` e recebe o único fantasma. O `decode` escapa porque o stream está
vazio e o laço de linhas não roda; a `view` não escapa, porque `distinct` e `n_unique` leem
a tabelinha **direto**, que é exatamente o atalho que os torna baratos.

E há um agravante de documentação: o docstring de `_dict_parts` (`src/tcf/view.py`) declara
a invariante *"a tabelinha é exatamente o conjunto de valores distintos da coluna: não há
único morto"*. Com `ntable=0` essa frase deixou de ser verdade no caminho que ela descreve.

## O que a solda de 2026-08-26 mudou aqui

A tabela retangular de 0 linhas passou de `#TCF.8H` para `#TCF.8M` com corpo `@` de
tabelinha vazia. Comparado lado a lado:

| operação | `.8H` (antes) | `.8M` (agora) |
|---|---|---|
| `count` / `select` | 0 / `[]` | 0 / `[]` |
| `group_count` | `{'': 1}` errado | **`{}` certo** |
| `where(col, "").select()` | `[{'a': ''}]`, **fabricava linha** | `[]` certo |
| `distinct` / `n_unique` | `['']` / 1 errado | `['']` / 1 errado |

No saldo a `view` melhorou. O que sobra é esta linha, e ela ficou mais visível porque agora
mora no caminho `@dict`, que é o caminho autoritativo do `distinct`.

## O caso irmão: wire que o `decode` lê e a `view` recusa

Uma coluna vazia **aninhada** continua saindo em `.8H`, e ali a `view` levanta:

```python
view(encode([{"v": []}]))   .count()   # ValueError
view(encode({"a": {"v": []}})).count() # ValueError
```

Isso é anterior à solda e continua de pé. Vale registrar junto porque é a mesma família:
zero linhas lido de formas diferentes conforme a rota.

E o ragged com coluna vazia ainda **fabrica** valor, que é o defeito que a solda curou no
retangular:

```python
view(encode({"a": ["x"], "v": []})).select()   # [{'a': 'x', 'v': ''}]
```

## Correção proposta

Uma linha, e ela fecha os dois: **`_dict_parts` tratar `ntable == 0` como `unicas = []`**,
em vez de confiar no `_decode_column("")`. Alternativa mais funda, e melhor: fazer
`_decode_column("")` devolver `[]`, que é a raiz compartilhada com
[`BUG-VIEW-UMA-STRING-VAZIA`](BUG-VIEW-UMA-STRING-VAZIA.md). A segunda precisa de auditoria
de todos os chamadores; a primeira é local e imediata.

## Critério de aceite

- [ ] `view(encode({"a": []})).distinct("a") == []` e `n_unique("a") == 0`.
- [ ] `distinct("a")` e `distinct(["a"])` concordam.
- [ ] O docstring de `_dict_parts` volta a descrever o que o código faz.
- [ ] Teste de propriedade: para todo wire do corpus, `view(w).nrows == len(decode(w)[c])` e
      `set(view(w).distinct(c)) == set(decode(w)[c])`. Este invariante pega este defeito, o
      do `_n_somado` e o do ragged de uma vez.
- [ ] Coluna vazia **aninhada** decide entre responder ou levantar, e o faz igual nas duas
      rotas.
- [ ] Suíte completa e gates verdes; nenhuma mudança de wire.

## Estado

Repro confirmado no working tree de 2026-08-26, depois da solda que moveu o 0-linha
retangular para o `.8M`. Nenhuma alteração em `src/tcf/` foi feita para este ticket.
