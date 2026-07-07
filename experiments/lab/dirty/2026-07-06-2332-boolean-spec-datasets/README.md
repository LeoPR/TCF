# 2026-07-06-2332 — boolean nos datasets + spec binária/enum (estudo)

**Ticket**: [T-OPT-INFERENCE](../../../../tickets/T-OPT-INFERENCE.md) · nota-mãe
[tipos-como-specs](../notas/tipos-como-specs.md) · natures ADR-0015. Pedido do owner: **olhar os nossos
datasets** pra entender boolean antes de desenhar a spec.

## Estado

- **era**: assumia-se "boolean = true/false" como um tipo.
- **foi**: varridos synthetic + hubs (adult, tpch, ibge, receita, br-identidades) por domínio ≤3.
- **é** (achado do dado real): **ZERO true/false**. O que existe é **enum-2/3 com superfície = DADO**
  (Male/Female, <=50K/>50K, F/O, A/N/R, F/O/P) + `matriz_filial=1|2` (**não** 0/1!). → o primitivo útil é
  **ENUM/domínio-k**; boolean true/false é caso especial semântico **raro** em tabela. Spec binária/enum
  prototipada, RT-OK. Bytes: raw 97KB → textual 49KB (~2×) → bitmap 6KB (~16×).
- **será**: registro de specs (enum/nature) no pre-pass; enum-k geral; bitmap na camada binária (V2-L).

## Achados-chave

1. **Boolean-como-true/false quase não existe** em dado tabular real; domina **enum-2/3** cujo rótulo é dado.
2. **`matriz_filial=1|2`** (não 0/1) — prova o risco de assumir semântica binária no CSV cru (sanidade).
3. **Compressão**: textual ∝ encurtamento da superfície (Male/Female→0/1 = 2×); o ganho grande/constante
   (1 bit/val) é **binário** (bitmap, ~16×). Em texto a spec vale por aceleração + header mínimo.
4. **Gabarito-da-spec**: variante padrão → `@bool:<variante>` (2 valores do registry); enum arbitrário →
   `@enum:v0|v1` (gabarito na coluna, uma vez).

## Eixos ORTOGONAIS de uma spec (além de compressão/aceleração — pedido do owner)

compressão · aceleração · **autoridade** (mandatório/natural/deduzido) · **normalizabilidade** (canonicalizar
vs byte-locked) · **fechamento de domínio** (fechado=enum/bitmap) · **variante** (superfície do mesmo
semântico) · **reversibilidade** (round-trip) · **validação/sanidade** (nature alerta).

## Arquivos

- `scan.py` — varredura domínio ≤3 (CSV + SQLite) + `classify` (bool-variante vs enum-2 vs domN).
- `boolean_spec.py` — spec binária: variantes (registry), autoridade, gabarito-da-spec, RT.
- `run.py` — scan + catálogo + RT + bytes (raw/textual/binário). `python run.py` regenera `artifacts/`.
- `artifacts/` — `00-resumo` · `01-catalogo-dominio2` · `02-spec-binaria-rt` · `03-bytes-coluna-real`.

## Como rodar

```
python experiments/lab/dirty/2026-07-06-2332-boolean-spec-datasets/run.py
```

## Escopo

Dirty (estudo empírico + protótipo). NÃO toca `src/tcf`. Dados: `datasets/synthetic/` + `Z:/tcf-data/interim/`.
