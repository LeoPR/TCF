# Varredura de snippets — docs vivos

Gerado por `varre_snippets.py`. Re-rode com `python varre_snippets.py`.

- blocos encontrados: **72**
- executados e OK: **52**
- **falharam: 0**
- pulados (não auto-contidos): 20 — **declarados abaixo, não contam como aprovados**

## Falhas

Nenhuma.

## Pulados (declarados)

| arquivo | linha | motivo |
|---|---|---|
| `docs/algorithms/output-convention.md` | 43 | sem import — provavelmente continuacao de outro bloco |
| `docs/algorithms/output-convention.md` | 82 | sem import — provavelmente continuacao de outro bloco |
| `docs/divulgacao-tcf.md` | 53 | sem import — provavelmente continuacao de outro bloco |
| `docs/how-to/encode-csv-file.md` | 39 | sem import — provavelmente continuacao de outro bloco |
| `docs/how-to/encode-csv-file.md` | 99 | sem import — provavelmente continuacao de outro bloco |
| `docs/how-to/encode-csv-file.md` | 148 | sem import — provavelmente continuacao de outro bloco |
| `docs/how-to/encode-csv-file.md` | 176 | sem import — provavelmente continuacao de outro bloco |
| `docs/how-to/encode-csv-file.md` | 205 | sem import — provavelmente continuacao de outro bloco |
| `docs/how-to/encode-csv-file.md` | 216 | sem import — provavelmente continuacao de outro bloco |
| `docs/how-to/log-run-metadata.md` | 30 | contem placeholder/reticencias — pseudo-codigo |
| `docs/how-to/use-natures.md` | 262 | sem import — provavelmente continuacao de outro bloco |
| `docs/how-to/use-natures.md` | 303 | sem import — provavelmente continuacao de outro bloco |
| `docs/reference/api.md` | 69 | sem import — provavelmente continuacao de outro bloco |
| `docs/reference/encode-knobs.md` | 8 | nao compila (Invalid star expression) — trecho ilustrativo |
| `docs/reference/lazy-view.md` | 106 | sem import — provavelmente continuacao de outro bloco |
| `docs/reference/lazy-view.md` | 120 | sem import — provavelmente continuacao de outro bloco |
| `docs/tutorials/getting-started.md` | 111 | sem import — provavelmente continuacao de outro bloco |
| `docs/tutorials/getting-started.pt-BR.md` | 114 | sem import — provavelmente continuacao de outro bloco |
| `README.md` | 322 | sem import — provavelmente continuacao de outro bloco |
| `README.pt-BR.md` | 325 | sem import — provavelmente continuacao de outro bloco |

## O que este gate NÃO pega

Prosa falsa, número solto no texto, e saída-esperada que não esteja num bloco
adjacente. Ele complementa o `run.py` (que confere afirmações nomeadas), não o substitui.
