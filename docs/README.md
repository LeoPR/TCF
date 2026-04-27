# TCF — Documentation Hub

Hub central da documentacao do projeto TCF (Textual Columnar Format).
Estrutura otimizada para 4 perfis de leitor:

## Para usuarios — quero usar TCF

→ [manual/](manual/) — manual de uso com 7 capitulos (quickstart, encode/decode,
niveis de compressao, integracao LLM, modelos recomendados, exemplos, troubleshooting)

→ [../README.md](../README.md) — visao geral GitHub-style

## Para pesquisadores — quero entender os achados

→ [findings/README.md](findings/README.md) — resumo paper-ready com 7 achados
centrais e tabela 2D

→ [findings/](findings/) — catalogo completo F-Q1..F-Q38 dividido por tema

→ [article/](article/) — capitulos do paper em desenvolvimento

## Para arquitetos — quero entender o sistema

→ [theory/architecture/](theory/architecture/) — snapshot atual da arquitetura
(boundaries, data-pipeline, components)

→ [theory/components/](theory/components/) — TCF Core, LLM Interface, DB Extractor

→ [theory/methodology/](theory/methodology/) — protocolo experimental,
LLM research rigor, model ranking

→ [theory/research-lines/](theory/research-lines/) — Linha A vs Linha B

## Para devs — quero entender a evolucao

→ [workbench/DEVELOPMENT.md](workbench/DEVELOPMENT.md) — timeline operacional
em 8 fases (encoder v0.0..v0.2, M-series, naturalness, M-Acomm, schema-scope)

→ [workbench/SCIENCE.md](workbench/SCIENCE.md) — timeline logico das hipoteses
em 5 partes

→ [workbench/history.md](workbench/history.md) — origem do projeto

→ [workbench/tickets/](workbench/tickets/) — tickets abertos e fechados

→ [workbench/research-notes/](workbench/research-notes/) — notas de pesquisa

→ [../CHANGELOG.md](../CHANGELOG.md) — versoes consolidadas

## Para arquivistas — material historico

→ [archive/](archive/) — versoes legacy (v0.1 article rascunhos)

→ [workbench/research-notes/_archive/](workbench/research-notes/_archive/) —
notas obsoletas (cobertas pelos consolidados)
