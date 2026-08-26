---
title: "BUG-VIEW-UMA-STRING-VAZIA: count e select truncam uma linha vazia"
status: open
priority: P1
severity: R0 (resposta errada e silenciosa na API pública)
created: 2026-08-26
updated: 2026-08-26
gate: correção em src/tcf só com aprovação explícita do owner (I5)
blocked-by: []
related:
  - src/tcf/view.py
  - tests/test_tcf_lazy.py
  - docs/reference/lazy-view.md
  - tickets/DECISAO-GROUPING-SEMANTICA.md
---

# BUG-VIEW-UMA-STRING-VAZIA

**[probatório → execução]** A `view` confunde zero linhas com uma linha cujo valor é a
string vazia. O `encode` e o `decode` estão certos; a resposta errada nasce na contagem
estrutural da camada read-only. Este ticket executa um contrato semântico já decidido; não
abre uma escolha nova sobre o que “vazio” deve significar.

## Contrato semântico

“Vazio” não é sinônimo de “ausente”. A operação precisa respeitar o domínio da pergunta:

| entrada ou situação | interpretação correta na `view` |
|---|---|
| `""` | string presente, portanto **um elemento**: entra em `count`, `nrows`, `distinct` e em `where(col, "")` |
| `[]` | sequência sem elementos: cardinalidade zero |
| `None`/`NULL` | valor ausente; a linha continua existindo para a contagem de linhas, mas uma contagem de valores presentes deve filtrá-lo explicitamente |
| conjunto numérico sem valores aproveitáveis | `sum = 0.0`; `min`/`max`/`avg = None`, pois não há extremo ou média definida |

Assim, `count()` da `view` é contagem de linhas/posições, equivalente a `COUNT(*)`, e não
contagem de strings não vazias. Para contar apenas valores presentes, a receita é um filtro
explícito que remove `None`; para também tratar `""` como missing, o predicado deve dizer
isso. A comparação com NumPy, pandas, Polars e SQL está em
[`mimetizar-pandas-sql-polars.md`](../docs/how-to/mimetizar-pandas-sql-polars.md).

Exemplo do comportamento pretendido:

```python
v = view(encode(["", "a", ""]))

v.count()                    # 3: três posições, inclusive as vazias
v.where(0, "").count()       # 2: duas posições cujo valor é ""
v.n_unique(0)                # 2: "" e "a"
```

## Repro mínimo

```python
from tcf import decode, encode, view

blob = encode([""])
assert blob == "#TCF.8\n\n"
assert decode(blob) == [""]

assert view(blob).count() == 1       # contrato: uma posição, mesmo vazia
assert view(blob).select() == [{"0": ""}]
```

Também afeta multi-coluna quando a primeira coluna disponível para a contagem estrutural
está no modo core:

```python
blob = encode({"a": [""], "b": ["x"]}, fallback=False)
assert decode(blob) == {"a": [""], "b": ["x"]}
assert view(blob).count() == 1       # a linha inteira continua existindo
assert view(blob).select() == [{"a": "", "b": "x"}]
```

## Causa

`_n_somado` remove um `\n` terminal e depois trata o corpo restante vazio como zero
linhas. Com isso, dois wires que o decoder canônico distingue viram o mesmo estado:

| wire | corpo recebido por `_n_somado` | verdade do `decode` |
|---|---|---|
| `"#TCF.8\n"` | `b""` | `[]` |
| `"#TCF.8\n\n"` | `b"\n"` | `[""]` |

Não basta trocar genericamente `return 0` por `return 1`: o corpo originalmente ausente
precisa continuar significando zero linhas. A correção deve preservar a distinção antes de
remover o terminador.

O dano alcança `select()` porque ele itera `range(self.nrows)`. Em multi-coluna, aceitar o
primeiro `0` impede que uma coluna irmã revele a contagem correta.

## Classificação pelo princípio oportunista

É correção óbvia de `0.8.x`, não pesquisa de otimização. O wire já carrega a distinção: o
corpo ausente é `b""`; uma posição vazia é `b"\n"`. Preservar esse byte de informação
mantém `count()` estrutural e não exige materializar a coluna.

Fazer fallback para `decode()` produziria a resposta certa, mas abandonaria informação que
a estrutura já oferece. O aceite é simultâneo: cardinalidade correta e mesmo caminho
barato para zero linhas e uma string vazia.

## Critério de aceite

- [ ] `view(encode([""])).count() == 1` e `select()` devolve a única linha.
- [ ] `view("#TCF.8\n")` continua representando zero linhas; não criar linha fantasma.
- [ ] Multi-coluna `fallback=False` não trunca quando a primeira coluna é `[""]`.
- [ ] A mesma tabela com a coluna vazia em outra posição também permanece correta.
- [ ] Cobrir `[""]`, `["", ""]`, `["a", ""]` e `["", "a"]` contra `decode()`.
- [ ] `count` não exclui `""`; uma receita de valores presentes exclui apenas `None`, e
  uma receita de missing vazio explicita também `x != ""`.
- [ ] `tests/test_tcf_lazy.py` e a suíte completa verdes; nenhum re-pin de bytes (rota
      read-only, `encode` intocado).

## Estado

Repro confirmado em `v0.8.2`. Nenhuma alteração em `src/tcf/` foi feita nesta auditoria.
