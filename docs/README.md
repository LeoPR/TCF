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

**Verdade canonica atual (v0.6 — algoritmo de compressao):**

→ [../experiments/lab/dirty/notas/historia-dirty-lab.md](../experiments/lab/dirty/notas/historia-dirty-lab.md)
— **narrativa canonica M0-M9** (atualizada 2026-05-17)

→ [../experiments/lab/dirty/notas/roadmap-hipoteses.md](../experiments/lab/dirty/notas/roadmap-hipoteses.md)
— direcoes futuras (pre-tx, decomposicao, escala)

→ [../experiments/lab/dirty/README.md](../experiments/lab/dirty/README.md)
— indice dos macros M0-M9

→ [workbench/research-notes/](workbench/research-notes/) — notas
de pesquisa vivas + INDEX apontando pra dirty

→ [../CHANGELOG.md](../CHANGELOG.md) — versoes consolidadas

**Material historico (v0.5 e anterior — LLM comprehension):**

→ [workbench/_archive/DEVELOPMENT.md](workbench/_archive/DEVELOPMENT.md)
— timeline operacional em 8 fases (ARQUIVADO; nao canonico)

→ [workbench/_archive/SCIENCE.md](workbench/_archive/SCIENCE.md)
— timeline logico das hipoteses (ARQUIVADO)

→ [workbench/_archive/tickets/](workbench/_archive/tickets/) —
tickets H/M/T/P/E/S do ciclo v0.3-v0.5 (ARQUIVADO)

## Para arquivistas — material historico

→ [archive/](archive/) — versoes legacy (v0.1 article rascunhos)

→ [workbench/research-notes/_archive/](workbench/research-notes/_archive/) —
notas obsoletas (cobertas pelos consolidados)
