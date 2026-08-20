# 2026-08-17-1900 — vale a pena? (memo de decisão)

> *"no fim é só ver se vale a pena o esforço de fazer o split + header mostrando pra
> recompor e quais mecanismos prontos + alguns ajustes são melhores de reusar."*

## A resposta curta

**Pelo byte: não.** −0,024% do corpus. **Pelo resto: sim** — e o argumento forte não é o
`.8M`, é o `.8H`.

## Prevalência (Shaper, 24 tabelas / 9 datasets, seed=42, vol=4000)

| | |
|---|--:|
| colunas medidas | 198 |
| split **aplica** (passa o gate) | 45 (**22,7%**) |
| split **vence** o `min()` | **40 (20,2%)** |
| bytes nas colunas com split | 693 602 (**15,3% do corpus**) |

Quem vence, no geral:

| modo | colunas | bytes | % dos bytes |
|---|--:|--:|--:|
| `tcf` | 59 | 2 694 644 | 59,4% |
| **`split`** | **40** | **693 602** | **15,3%** |
| `dict` | 77 | 584 314 | 12,9% |
| `raw` | 22 | 562 732 | 12,4% |

**O split não é mecanismo de nicho.** Vence em 1 de cada 5 colunas e responde por 15,3% dos
bytes — mais que o `dict` e mais que o `raw`. Isso é o que torna o esforço discutível; se
vencesse em 3 colunas, a conversa acabava aqui.

## O que o grupo mudaria — em bytes

| | |
|---|--:|
| hoje (slot aninhado), 40 colunas | 693 602 B |
| grupo (corpo + marcador de 11 B) | 692 535 B |
| **delta** | **−1 067 B = −0,024% do corpus** |

Por coluna, o ganho é **constante** (−18 a −53 B, conforme o nº de campos):

| coluna | nf | split | grupo | delta |
|---|--:|--:|--:|--:|
| `tpch-sf01.customer.c_phone` | 4 | 49 037 | 48 994 | −43 |
| `br-identidades.empresas.cnpj` | 5 | 46 118 | 46 065 | −53 |
| `tpch-sf01.orders.o_totalprice` | 2 | 34 948 | 34 930 | −18 |

**Byte não é o argumento** — e isso é coerente com o critério do projeto
([redundância, não byte](../../../notas/2026-08/2026-08-17-1400-split-teoria-e-o-magic-aninhado.md)).
O que o número diz é: **não há regressão** (o grupo devolve mais do que o marcador cobra em
100% das colunas medidas), e o ganho não escala com `n`.

## Onde o esforço se paga de verdade

Três coisas, em ordem de peso:

1. **O `.8H` ganha o split estruturalmente** — medido no
   [lab 1700](../2026-08-17-1700-grupo-como-combinador-do-H/): **−11,7% a −25,4%**, isolado
   por controle e **ortogonal** ao efeito dos candidatos. Hoje a folha do `.8H` não alcança
   o split de jeito nenhum. Este é o maior retorno, e é o que fecha parte do gap de +23% do
   [lab 0400](../2026-08-17-0400-o-candidato-unico-do-H/).
2. **A `view` e o decode paralelo passam a alcançar os campos.** Hoje o slot é caixa-preta —
   `view.py:232,:438`: split *"exige decode"*, *"cai em fallback"*; nem contar linhas dá sem
   abrir o slot. Na forma-grupo o plano de fatias sai da linha 1.
3. **Some redundância de 100%** — o `#TCF.8M` aninhado, o sub-header, a moldura `<ntmpl>` e
   os nomes `c0..cN`, todos dedutíveis do contexto.

## O que reusar, e o que ajustar

**Reuso sem tocar** (o grosso já está pronto):

| mecanismo | onde | papel |
|---|---|---|
| detecção de template | `split.py:24` `_struct_split_encode` | acha o template uniforme e separa os campos |
| `min()` por coluna | `core.py:456` `_best_of` | escolhe o candidato de **cada campo** |
| parse do meta | `core.py:177` `_parse_meta` | já lê `[modo]<size>[=nome]` por coluna |
| decode `dict` | `dict_v2b.py:70` `_decode_v2b` | autossuficiente (deriva `n` do stream) |
| decode `raw` | `core.py:723` `_decode_raw_body` | idem |
| colunas anônimas | ADR-0029 (`drop_names`) | os campos não precisam de nome |
| meta do `.8H` | `hierarchical.py:654` `_parse_meta` | já lê combinadores (`{`, `#:[`, `?:`) |

**Ajustes** — três, e todos pequenos:

1. **`split.py:48-56`** — hoje monta `sub_bytes = _encode_multi({c0:…, c1:…})` e devolve
   `<ntmpl>\n<template><subwire>`. Passaria a devolver **os corpos dos campos + o template
   para o meta**, sem embrulhar. É o único ponto onde código sai.
2. **O marcador no meta** — gramática nova (9–11 B medidos). **Único item genuinamente novo.**
   A escolha entre pôr no `.8M` (indicador de junção) ou no `.8H` (combinador) é de
   **gramática, não de mecanismo** — o [lab 1800](../2026-08-17-1800-o-que-de-fato-falta/)
   provou que o corpo é idêntico nas duas, então **essa decisão pode ser adiada**.
3. **A junção no decode** — uma linha:
   `"".join(partes[k] + cols[k][r] …) + partes[-1]`.

## O custo real do esforço

Não é o código — é o **re-pin**. Mudar o wire do split move **40 de 198 colunas** e
**15,3% dos bytes** do corpus: `D17a` e `real-world` mudam, e isso exige **ADR + re-pin
consciente** (ADR-0024, git-as-compat). É esse o item caro, não as três mudanças acima.

## Recomendação

**`.9`, e pelo `.8H` primeiro.** O ganho no `.8M` é ~zero em byte (embora sem regressão e com
a redundância eliminada); o ganho no `.8H` é real e ainda não existe de nenhuma outra forma.
Como o corpo é idêntico nas duas gramáticas, dá para **soldar o combinador no `.8H`** e
decidir depois se o `.8M` migra — sem retrabalho.

**Bloqueador antes de qualquer weld**: a composição **grupo × array** (H-13-06). Um grupo
dentro de array precisa que os N campos compartilhem a contagem, e isso **não foi testado**.

## Não medido (declarado)

- **Uma seed, `volume=4000` por dataset.** Sem varredura de seeds/volumes.
- **CPU não medida** em lugar nenhum desta cadeia.
- **O marcador de 11 B é estimativa pessimista** do lab 1800 (medido 9–11). A gramática real
  pode diferir.
- A prevalência é **por coluna**, não ponderada por frequência de uso real dos datasets.
- `adult-census` e `wine-quality` entraram no Shaper; se algum falhou, saiu do total — o mix
  declarado no `resultado.json` mostra quais tabelas entraram.

## Evidência

`resultado.json` (198 colunas, com vencedor e bytes de cada) + 6 wires das colunas onde o
split mais pesa, com roundtrip.

## Conexões

- [`1500`](../2026-08-17-1500-split-didatico/) · [`1600`](../2026-08-17-1600-split-como-grupo-no-meta/) ·
  [`1700`](../2026-08-17-1700-grupo-como-combinador-do-H/) · [`1800`](../2026-08-17-1800-o-que-de-fato-falta/)
- [`0400`](../2026-08-17-0400-o-candidato-unico-do-H/) (o gap do `.8H`)
- [roadmap-hipoteses Pacote 13](../../../notas/2026-05/roadmap-hipoteses.md)
