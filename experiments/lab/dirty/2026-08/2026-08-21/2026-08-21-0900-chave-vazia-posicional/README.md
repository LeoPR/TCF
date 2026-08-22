# 2026-08-21-0900 — `BUG-CHAVE-VAZIA-POSICIONAL`: o único caso em que o TCF altera o dado

> ## ⚑ SOLDADO 2026-08-21 — [ADR-0046](../../../../../../docs/adr/0046-nome-vazio-8m-porta-o-z-do-8h.md)
>
> O owner aprovou a opção 2 (`\z`) e pediu duas coisas: revisar a documentação do `\z` (já muito
> discutido) e dizer se era **bug atual ou definição que faltou**. Resposta: **definição superada**
> — `''` = anônima foi decisão deliberada de 2026-07-10; o `.8H` criou o `\z` em 2026-07-17
> (ADR-0033) e a convenção não foi portada de volta. O ADR-0046 **adota** o `\z` de 0033, não o
> re-deriva. Os itens "não medido" abaixo (posição arbitrária, `drop_names`, `nature_per_col`,
> `view()`) foram todos medidos no weld e estão pinados em `TestNomeVazioPreservadoADR0046`.
>
> **O `run.py` deste lab afirma o estado PRÉ-weld** (`assert r != d` no G1: "o RT quebra") e por
> isso **não passa mais** — é registro da medição, não script vivo. Para reexecutá-lo como era,
> `git checkout b4ae39a5`. Os `outputs/*-HOJE.*` são os wires de antes; o `*-CORRIGIDO.tcf` é o
> que o encoder emite agora.

Item do `.8` (fechando **comportamentos**). Ticket aberto desde 2026-08-01, com duas opções
não decididas. Este lab mede para decidir. **`src/tcf` intocado** — o protótipo vive aqui.

## O bug

```python
decode(encode({"": ["a", "b"]}))   # -> {"0": ["a", "b"]}   (com UserWarning)
```

O contrato do TCF é **ou preserva, ou falha alto**. Este caso **muta a chave** — foge do
contrato. Há warning, então não é silencioso, mas o roundtrip quebra.

## A causa raiz

```
encode({"": [...]})                    ->  '#TCF.8M!\na\nb'
encode({"x": [...]}, drop_names=True)  ->  '#TCF.8M!\na\nb'    ← IDÊNTICO
```

**O formato não distingue "nome vazio" de "sem nome".** Um nome vazio simplesmente não emite
nada, e "não emitir nada" já significa coluna anônima. No decode, anônima → posicional.

## A solução já existe no projeto — na rota vizinha

O **`.8H` resolveu isto** com o sentinela `\z` ([`hierarchical.py:114`](../../../../../../src/tcf/hierarchical.py)):

```
{'': {'x': 1}}      ->  '#TCF.8H#O\z{x:3n\n\1\n'          RT=True
[{'': 1, 'a': 2}]   ->  '#TCF.8H\z:3n,a:3n\n\1\n\2\n'      RT=True
```

E o comentário no próprio código diz por quê: *"Por que um marcador e não 'emitir nada': 'nome
vazio no header' é o SENTINELA DE…"* — o `.8H` já enfrentou exatamente esta colisão e escolheu
marcar. **A rota flat/multi não adotou.** Não há o que inventar: é adotar a mesma grafia.

## O slot está livre — verificado

| checagem | resultado |
|---|---|
| `z` está na whitelist de escape do multi (`,=:\!@%`)? | **não** → `\z` livre |
| algum nome real emite `\z` no header? | **0 de 7** testados (`z`, `\z`, `az`, `z `, `\`, `\\z`, `Z`) |

O nome literal `\z` sai como `\\z` (barra escapada), então não colide.

## O protótipo e o custo

A correção é **uma regra, nos dois lados**:

```
encode:  nome == ''   ->  emite `\z`   (em vez de não emitir nada)
decode:  token `\z`   ->  nome ''      (em vez de posicional)
```

| | wire | decode | RT |
|---|---|---|---|
| hoje | `'#TCF.8M!\na\nb'` | `{'0': [...]}` | **False** |
| corrigido | `'#TCF.8M!\z\na\nb'` | `{'': [...]}` | **True** |

**Custo: 2 bytes**, e só na coluna que tem nome vazio. **Nenhum wire existente muda** — 7 de 7
nomes não-vazios produzem bytes idênticos aos de hoje.

## Por que não `fail-loud` (opção 1 do ticket)

O nome vazio **nasce do próprio CSV** (RFC 4180: campo vazio é campo legal, e no header vira
nome de coluna vazio). Três formas comuns, todas quebrando o RT hoje:

| CSV | header lido | RT |
|---|---|---|
| `a,b,` (vírgula sobrando) | `['a', 'b', '']` | **False** |
| `a,,b` (coluna sem título no meio) | `['a', '', 'b']` | **False** |
| `,a,b` (primeira sem título) | `['', 'a', 'b']` | **False** |

`fail-loud` recusaria **CSV válido por RFC 4180**. É caro demais para o que se ganha.

> Na primeira versão deste lab eu usei `pandas.to_csv()` como motivação — o owner apontou que
> pandas não tinha entrado no assunto, e tinha razão: eu trouxe uma ferramenta externa sem
> dizer por quê. O argumento não precisa dela. A propriedade é **do CSV**, não de quem o
> escreve.

## Recomendação

**Opção 2 do ticket — preservar via `\z`**, pelos motivos acima:

1. a grafia **já existe e está provada** na rota `.8H`;
2. o slot está **livre e verificado** no multi;
3. custa **2 bytes** só no caso afetado, e **zero** wire existente muda;
4. `fail-loud` recusaria CSV legítimo.

**Aguarda aprovação** — toca `src/tcf` (rota flat/multi), e o ticket marca
`gate: byte-canonical + test_real_world_snapshots`.

## Não medido (declarado)

- **Interação com `drop_names=True`**: se o chamador pede para dropar nomes, o vazio some junto
  — coerente, mas não testei a combinação.
- **Múltiplas colunas** onde só uma tem nome vazio: o protótipo cobre o caso de coluna única.
  O weld real precisa cobrir posição arbitrária (o `,` separa tokens, então deve ser direto —
  mas *deve ser* não é *medido*).
- O `.8H` já preserva, então **não há divergência entre rotas a resolver depois** — mas não
  verifiquei se `.8M` e `.8H` produzem o mesmo *nome* para o mesmo dado em todos os casos.
- Nome de coluna com **só espaços** (`"  "`): não testado; não é vazio, deve passar intacto.

## Evidência

[`run.py`](run.py) com G1–G5 e asserts (a colisão com `drop_names`, o slot livre, o RT do
protótipo, e os 7/7 wires inalterados). 10 arquivos em [`inputs/`](inputs/)+[`outputs/`](outputs/),
incluindo os wires que decodificam errado hoje. [`resultado.json`](resultado.json).

## Conexões

- Ticket: [`BUG-CHAVE-VAZIA-POSICIONAL`](../../../../../../tickets/BUG-CHAVE-VAZIA-POSICIONAL.md)
- A solução na rota vizinha: `src/tcf/hierarchical.py:92,114` (o sentinela `\z`)
- Lab de origem: `2026-08-01-0309-json-lib-roundtrip-comportamento` (matriz json × tcf, 29 casos)
