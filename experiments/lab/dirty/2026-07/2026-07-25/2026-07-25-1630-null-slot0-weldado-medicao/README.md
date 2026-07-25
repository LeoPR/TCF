# 2026-07-25-1630 — null no slot 0 SOLDADO: medição no produto real

O lab `2026-07-24-2210` mediu um **protótipo** contra o `.8H`. O mecanismo agora está
soldado, e esta rodada mede o **produto real** — para ver se ele entregou o que o protótipo
prometeu ou se algo se perdeu no caminho.

```
coluna : [None, '', 'true', 'false', 'oi', None, 'null']
antes  : '#TCF.8H#V\z#:3?:14[\n\7\n\0\n*4|.\n^1\n^2\n\ntrue\nfalse\noi\nnull\n'   57 B
depois : '#TCF.8\n0\n\ntrue\nfalse\noi\n0\nnull\n'                                31 B
```

## Resultado — **APROVADO**

**RT 17/17.** O protótipo prometeu; o produto entregou o mesmo.

- vs **JSON compacto** (`separators=(',',':')`): mediana **−67%** (pior −24%, melhor −86%)
- vs `.8H`, colunas **com** null (14): **Δ mediano −36%** · pior −4% · melhor −58%
- vs `.8H`, colunas **sem** null (3): **+0%**, byte-idênticas

O ganho cresce com a densidade de null e é maior em **n pequeno** (−46% no exemplo do owner,
7 elementos) — o regime de payload minúsculo. Mesmo no pior caso (n=1000, 1% de null) é −4%:
**nenhum regime medido regrediu.**

> **Atribuição honesta**: a maior parte do −67% vs JSON é do **core** (dedup/RLE/composição),
> não deste weld — colunas sem null nenhum já dão −24% a −43%. A coluna `Δ do weld` isola o
> que esta mudança acrescentou.

## O achado: o `.8H` era MAIOR que o JSON em payload pequeno

| id | JSON | `.8H` | era | virou |
|---|---:|---:|---:|---:|
| A-exemplo-owner | 41 | 57 | **+39%** | **−24%** |
| D-null-bordas | 23 | 40 | **+74%** | **−26%** |
| R-n10-p50 | 72 | 75 | **+4%** | **−35%** |

Antes do weld, uma coluna minúscula com null saía **maior como TCF do que como JSON** — o
envelope hierárquico custava mais do que os bytes que economizava. Isso contradizia
frontalmente o foco declarado do projeto (cada byte conta em payload minúsculo).

**3 de 14 colunas com null** estavam nessa situação; todas viraram ganho. Essa é a
consequência mais relevante da rodada — não o percentual médio.

## Byte-neutralidade em dados REAIS

D1-D9 conferidos contra os pinos do ADR-0034: **9/9 idênticos** (125, 173, 184, 120, 288,
294, 222, 107, 73). Coluna sem null não paga nada — o slot 0 era espaço morto, então não
roubou endereço de dado nenhum.

## Erro DESTE lab (corrigido, registrado)

Na 1ª rodada o `antes` forçava **toda** coluna pro `.8H`. Errado: antes do weld, só a coluna
**com** null era desviada; sem null ela já saía no flat. Isso inflava as linhas de controle
(`E-sem-null` aparecia com −29% quando o correto é **0%**) e contaminava a mediana. Corrigido
— o `antes` de uma coluna sem null é o próprio flat.

## Sob gzip — e aqui a vantagem sobre JSON some

Sinal qualitativo, **não critério** (o TCF não é medido por compressão externa). Mas o
resultado é honesto e vale registrar em vez de esconder:

| id | JSON gz | `.8H` gz | TCF gz | vs JSON gz |
|---|---:|---:|---:|---:|
| A-exemplo-owner | 50 | 77 | 50 | **+0%** |
| B-n7-1null | 52 | 75 | 54 | **+4%** |
| C-todos-null | 29 | 50 | 33 | **+14%** |
| D-null-bordas | 39 | 60 | 35 | −10% |
| E-sem-null | 45 | 49 | 49 | **+9%** |

Contra JSON **gzipado**, os −67% viram ~0%, e em alguns casos o TCF fica ligeiramente maior.
Duas razões: (a) nestes tamanhos o cabeçalho do gzip (~20 B) domina tudo; (b) o entropy-coder
recupera boa parte da redundância que o TCF já tinha eliminado — mesmo fenômeno do "brotli
colapsa bN sobre V2-B".

Isso **não invalida o weld** (a melhora vs `.8H` sobrevive ao gzip em todas as linhas), mas
delimita onde a vantagem vive: no **wire não-comprimido** — latência, terminal,
inspecionabilidade — que é o eixo declarado do bN/3-fluxos, não a razão de compressão final.

## O que este lab NÃO cobre

- **Multi-coluna e `.8H`**: `{"a": ["x", None]}` continua indo pro `.8H`. A rota aberta é a
  do single-col flat. Escala firmada pelo owner: uma coluna de um tipo.
- **Outros especiais**: NaN/±Inf seguem fail-loud (RFC 8259); ausência segue máscara. A
  ordem canônica dos demais slots reservados continua **não fixada**.
- **Contrato público**: `decode` de single-col agora pode devolver `list[str | None]`.
  Mudança de superfície pública — provável ADR.

## Rodar / layout

```
python run.py     # 17 casos: antes (.8H) vs depois (produto) + D1-D9 + gzip
```
`inputs/*-fonte.json` · `intermediates/*-dataset-consumido.json` ·
`outputs/*-antes-8H.tcf` + `*-wire.tcf` (REAL) + `*.roundtrip.json` · `result.md`.
