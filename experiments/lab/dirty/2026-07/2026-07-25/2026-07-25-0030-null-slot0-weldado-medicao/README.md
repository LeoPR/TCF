# 2026-07-25-0030 — null no slot 0 SOLDADO: medição no produto real

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

- colunas **com** null (14): **Δ mediano −36%** · pior caso −4% · melhor −58%
- colunas **sem** null (3): **+0%**, byte-idênticas

O ganho cresce com a densidade de null e é maior em **n pequeno** (−46% no exemplo do owner,
7 elementos) — o regime de payload minúsculo. Mesmo no pior caso (n=1000, 1% de null) é −4%:
**nenhum regime medido regrediu.**

## Byte-neutralidade em dados REAIS

D1-D9 conferidos contra os pinos do ADR-0034: **9/9 idênticos** (125, 173, 184, 120, 288,
294, 222, 107, 73). Coluna sem null não paga nada — o slot 0 era espaço morto, então não
roubou endereço de dado nenhum.

## Erro DESTE lab (corrigido, registrado)

Na 1ª rodada o `antes` forçava **toda** coluna pro `.8H`. Errado: antes do weld, só a coluna
**com** null era desviada; sem null ela já saía no flat. Isso inflava as linhas de controle
(`E-sem-null` aparecia com −29% quando o correto é **0%**) e contaminava a mediana. Corrigido
— o `antes` de uma coluna sem null é o próprio flat.

## Sob gzip

Sinal qualitativo, **não critério** (o TCF não é medido por compressão externa). Os ganhos
sobrevivem: −20% a −42%. Serve só para mostrar que não é redundância textual que um
entropy-coder colapsaria.

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
