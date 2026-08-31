---
title: "T-DOC-L10N-REFERENCE: os 5 documentos restantes de docs/reference/ em dois idiomas"
status: open
priority: P3
created: 2026-08-25
updated: 2026-08-25
target: "antes da publicacao 1.0; parcial entregue no 0.8.2"
blocked-by: []
related:
  - docs/reference/lazy-view.md
  - docs/how-to/consultar-sem-decodificar.md
  - docs/algorithms/HCC.md
---

# T-DOC-L10N-REFERENCE

`docs/algorithms/` ja' e' bilingue com um padrao definido: um **router** de 8 linhas com
marcador `<!-- l10n: doc_id=... -->`, e o conteudo em `X.en.md` (canonical) e `X.pt-BR.md`
(traducao declarada). Os links externos apontam pro router e por isso nao quebram quando o
conteudo muda de arquivo.

`docs/reference/` tinha 7 documentos, todos so' em portugues.

## Entregue no 0.8.2

Os dois de consulta, que sao o foco do ciclo:

| doc | EN | PT | router |
|---|---:|---:|---:|
| `lazy-view` | 275 linhas | 276 | 8 |
| `view-usos` | 230 linhas | 229 | 8 |

## Falta

| doc | linhas | por que importa |
|---|---:|---|
| `api.md` | 167 | e' o indice da superficie publica: a primeira parada de quem chega |
| `familia-bn-bits.md` | 250 | descreve as rotas densas (`b`/`B`/`C`), citadas pelo formato |
| `json-equivalence.md` | 142 | o argumento de equivalencia com JSON, usado na divulgacao |
| `bibliografia.md` | 101 | referencias; traducao mais mecanica que as outras |
| `encode-knobs.md` | 82 | os knobs; citado por `lazy-view` nos dois idiomas |

Total: **742 linhas**. Nenhum deles e' bloqueante pro 0.8.2, porque o publico que le'
reference ja' chega pelo README e pelos tutoriais, que estao nos dois idiomas.

## Criterio de aceite

- [ ] Cada um dos 5 com router + `.en.md` canonical + `.pt-BR.md` traducao declarada.
- [ ] Os links de entrada continuam resolvendo pelo router (verificar, nao supor).
- [ ] O verificador de snippets segue em 0 falhas depois do split (os blocos duplicam).
- [ ] Sem travessoes nos arquivos novos.

## Nota de processo

Ao dividir, o conteudo em portugues vira `X.pt-BR.md` e passa a ser **traducao** do EN, com
o cabecalho declarando isso. E' uma inversao de fonte: o que era original vira derivado, e
edicoes futuras devem entrar no EN primeiro. Isso segue o padrao ja' adotado em
`docs/algorithms/` e a diretriz do owner de manter a superficie primariamente em ingles.
