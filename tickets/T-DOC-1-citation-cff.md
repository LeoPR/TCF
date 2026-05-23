---
title: T-DOC-1 — Adicionar CITATION.cff e preparar DOI (Zenodo)
status: closed
resolution: citation-cff-created-doi-deferred
priority: P3
created: 2026-05-22
updated: 2026-05-23
closed: 2026-05-23
blocked-by: []
related:
  - ../README.methodology.md
  - LICENSE
  - CITATION.cff
---

# T-DOC-1 — Adicionar CITATION.cff e preparar DOI (Zenodo)

## Contexto / motivacao

Auditoria de aderencia a `README.methodology.md` (2026-05-22) apontou
§3.5 (citacao academica) como gap de baixo custo. Projeto ainda nao
e' publicado, mas TCF tem trajetoria de pesquisa formalizavel
(M0-M14 + Pacotes + ADRs) e pode virar release citavel.

[Citation File Format](https://citation-file-format.github.io/)
e' o padrao agnostico de SCM (GitHub renderiza nativo). DOI via
Zenodo da identidade permanente que persiste se o repo migrar.

## Plano

1. Criar `CITATION.cff` com campos minimos: `authors`, `title`,
   `version` (0.6), `date-released`, `repository-code`, `license`
2. Decidir se publicar release agora (cria DOI) ou apenas preparar
   o arquivo (defer Zenodo ate' v1.0 ou primeiro paper)
3. Adicionar link no `README.md` ("How to cite this work")

## Criterio de aceite

- [ ] `CITATION.cff` na raiz, validado por
  [cffconvert](https://github.com/citation-file-format/cffconvert)
- [ ] Render correto na pagina do repo (badge "Cite this repository")
- [ ] Mencao em `README.md`

## Riscos

- Versionar autor/afiliacao pode ficar obsoleto — politica: atualizar
  na release, nao por commit individual
- DOI permanente: uma vez publicado, errar metadata e' caro de
  corrigir. Preferir defer Zenodo ate' ter conviccao de release

## Conexoes

- Metodologia §3.5 (citacao academica)
- §11 bibliografia (JOSS, Zenodo)

## Updates datados

### 2026-05-23 — execucao + fechamento

CITATION.cff criado na raiz com campos minimos:
- authors: Leonardo Marques Souza
- title: TCF — Tabular Compact Format
- version: 0.6
- date-released: 2026-05-22
- repository-code: github.com/LeoPR/TCF
- license: MIT
- abstract com pipeline canonical M10 + validacao Adult+TPC-H 11.73%
- keywords: tabular-data, compression, etc.

README.md atualizado com seção "How to cite" apontando pra CITATION.cff.

DOI/Zenodo: **DEFERRED** ate' v1.0 OR primeiro paper (conforme plano).
Risco de DOI permanente com metadata errada e' alto; preferivel defer.

Resolution: citation-cff-created-doi-deferred. Quando publicar v1.0
ou primeiro paper, abrir T-DOC-1b pra Zenodo + DOI permanente.
