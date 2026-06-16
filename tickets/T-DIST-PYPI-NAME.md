---
title: T-DIST-PYPI-NAME — Capturar nome de distribuicao no PyPI
status: closed-done
priority: P2
created: 2026-06-14
updated: 2026-06-16
blocked-by: []
related:
  - CITATION.cff
  - pyproject.toml
  - docs/adr/0024-pre-1.0-versioning-git-as-compat.md
---

# T-DIST-PYPI-NAME — Capturar nome no PyPI

> **Decisao do owner (2026-06-15)**: nome escolhido = **`tcf-format`** (mantendo
> `import tcf`). `pyproject.toml` ja' preparado: `name = "tcf-format"`,
> `version = "0.7.0"` (alinha ADR-0024), e a auto-ref do meta-grupo `all` corrigida
> pra `tcf-format[dev,eval,datasets]`. `[tool.hatch.build.targets.wheel] packages =
> ["src/tcf"]` ja' desacopla o nome da distribuicao do pacote importavel.
>
> **FECHADO (2026-06-16)**: **`tcf-format` 0.7.1 PUBLICADO no PyPI pelo owner**
> (nome capturado). O patch e' contador de release, desacoplado do formato `#TCF.7`
> e do comportamento. Build validado via `uv build` -> `tcf_format-0.7.1.{tar.gz,whl}`
> (wheel `py3-none-any`, METADATA Name=tcf-format). `import tcf` inalterado.
> Nota: a versao 0.7.1 no PyPI e' imutavel; o exemplo CPF do README so' aparecera'
> na long-description numa proxima publicacao (0.7.2+). Automacao de release
> (release.yml + Trusted Publishing) adiada por escolha do owner (follow-up).

**Intencao do owner (2026-06-14)**: reservar **logo** um nome de distribuicao no
PyPI pro TCF, mesmo pré-1.0 (evitar squatting; garantir o nome quando publicar).

## Disponibilidade (checada 2026-06-14, via PyPI JSON API)

| nome | status |
|---|---|
| `tcf` | **TOMADO** — Tencent Cloud Serverless Cloud Function (v0.3.0) |
| `pytcf` | TOMADO (reservado por Xilinx) |
| **`tabular-compact-format`** | **LIVRE** ✅ |
| **`tcf-format`** | **LIVRE** ✅ |

> Re-checar na hora de reservar (disponibilidade muda).

## Nota importante: nome de distribuicao != nome de import

O nome no `pip install X` (distribution) pode diferir do `import tcf` (package).
Da' pra distribuir como **`tcf-format`** (ou `tabular-compact-format`) e manter
`import tcf` no codigo (via `[project] name` no pyproject vs o diretorio
`src/tcf/`). Ou seja, o nome PyPI nao força renomear o pacote Python.

## Recomendacao

- Distribuir como **`tcf-format`** (curto, casa com `#TCF.N`, livre) mantendo
  `import tcf`. Alternativa descritiva: `tabular-compact-format`.
- **Pré-1.0**: a versao publicada seguiria `0.x` (ADR-0024). Pra so' **reservar**
  o nome agora, opcoes:
  1. Publicar um placeholder `0.0.1` (README minimo) e iterar; OU
  2. Esperar o 0.7.0 estar publicavel e subir direto.
- Owner faz o upload (credenciais PyPI). Passos: conta PyPI + token, ajustar
  `[project] name = "tcf-format"` no `pyproject.toml`, `python -m build`,
  `twine upload`.

## Criterio de aceite

- [ ] Decidir nome final (recomendado: `tcf-format`).
- [ ] Re-checar disponibilidade.
- [ ] `pyproject.toml` com `name` + metadata (description, license, urls, authors
      alinhados a CITATION.cff).
- [ ] Owner reserva no PyPI (placeholder 0.0.1 OU release 0.7.0).
- [ ] Registrar o nome escolhido em README + CITATION + STATUS.

## Riscos

1. Nome curto some rapido — reservar logo (motivacao do ticket).
2. Confundir distribution vs import — documentar o `import tcf`.
3. Publicar pré-1.0 cria expectativa de estabilidade — deixar claro no README
   que e' pré-1.0 sem compat rigida (ADR-0024).
