---
title: "BUG-VIEW-UMA-STRING-VAZIA: count e select truncam uma linha vazia"
status: closed-fixed
priority: P1
severity: R0 (resposta errada e silenciosa na API pública)
created: 2026-08-26
updated: 2026-08-27
gate: correção em src/tcf só com aprovação explícita do owner (I5)
blocked-by: []
related:
  - src/tcf/view.py
  - tests/test_tcf_lazy.py
  - docs/reference/lazy-view.md
  - tickets/DECISAO-GROUPING-SEMANTICA.md
  - experiments/lab/dirty/notas/2026-08/2026-08-26-1944-revisao-fechamento-08-view-encode.md
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
| conjunto numérico sem valores aproveitáveis | depende da FAMÍLIA, e as duas estão documentadas: no agregador **escalar**, `min`/`max`/`avg` levantam `ValueError` e `sum` devolve `0`, que é o `sum([])` do Python; na família **`group_*`**, o grupo aparece com `sum = 0.0` e `min`/`max`/`avg = None`, porque ali o grupo existe mesmo sem valor |

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

- [x] `view(encode([""])).count() == 1` e `select()` devolve a única linha.
- [ ] `view("#TCF.8\n")` continua representando zero linhas; não criar linha fantasma.
- [x] Multi-coluna `fallback=False` não trunca quando a primeira coluna é `[""]`.
- [x] A mesma tabela com a coluna vazia em outra posição também permanece correta.
- [x] Cobrir `[""]`, `["", ""]`, `["a", ""]` e `["", "a"]` contra `decode()`.
- [x] `count` não exclui `""`; uma receita de valores presentes exclui apenas `None`, e
  uma receita de missing vazio explicita também `x != ""`.
- [x] `tests/test_tcf_lazy.py` e a suíte completa verdes. A correção é read-only e não
      re-pina byte nenhum por si; o único re-pin da árvore
      (`tests/test_multi_col_rt.py`, `encode({"a": []})`) vem da solda de 0-linha de
      2026-08-26, que é outra mudança.

## Estado

**FECHADO em 2026-08-27.** A correção é a ordem de três linhas em `view.py::_n_somado`:
perguntar se o corpo está AUSENTE **antes** de tirar o `
` terminal. Sem isso, corpo
`b""` (zero linha) e corpo `b"
"` (uma linha vazia) viravam o mesmo estado, e o
`select()` ia junto porque itera `range(nrows)`.

Evidência: [`2026-08-27-0100-contagem-de-linhas`](../experiments/lab/dirty/2026-08/2026-08-27/2026-08-27-0100-contagem-de-linhas/),
onze casos mínimos, 8 de 11 antes e **11 de 11** depois, com `inputs/` e `outputs/` em
disco. Testes: `TestContagemDeUmaLinhaVazia` (11 casos mais a ordem das colunas) e
`TestContarValoresPresentesVsPosicoes` (as duas receitas de contagem do contrato), ambos
em `tests/test_tcf_lazy.py`. Verificação adversarial independente: 900 wires do `encode`
sobre `{"", "a", "bb", "x"}`, 1 a 3 colunas, 0 a 7 linhas, conferindo `nrows`, `distinct`,
`n_unique` e `select` contra o `decode`, **zero falhas**.

Duas correções de TEXTO entraram junto, e a primeira importa mais que o defeito:

1. **a tabela de contrato semântico afirmava um contrato falso.** Ela dizia `sum = 0.0` e
   `min`/`max`/`avg = None` para conjunto sem valores aproveitáveis, sem distinguir
   família. Medido: no agregador **escalar** os três extremos **levantam** `ValueError` e
   `sum` devolve `0` (int); o `None` e o `0.0` valem na família **`group_*`**. A doc
   (`docs/reference/lazy-view.pt-BR.md`) já dizia isso certo, com escopo explícito, nas
   duas linhas. Quem estava errado era este ticket, e fechá-lo sem corrigir congelaria a
   frase falsa;
2. o `mimetizar-pandas-sql-polars.md` dizia que o contrato valia *"mesmo que a
   implementação ainda precise ser corrigida nessa borda"*, ressalva que deixou de valer.

Fica de fora, e é outro ticket: coluna vazia **aninhada**, que o `decode` lê e a `view`
recusa, em [`BUG-VIEW-COLUNA-VAZIA-UNICO-FANTASMA`](BUG-VIEW-COLUNA-VAZIA-UNICO-FANTASMA.md).
O parecer de fechamento relacionado confirmou a classificação como correção local de
`0.8.x`, sem mudança de wire.
