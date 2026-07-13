# Reference — knobs de `encode()`

Referência dos parâmetros opt-in de [`tcf.encode`](../../src/tcf/encoder.py). O default
(zero-param) produz o formato **0.8 / `#TCF.8M`** lossless; os knobs abaixo só mudam bytes/layout
**quando passados explicitamente**.

```python
from tcf import encode
encode(data, *, side_outputs=None, parallel=False, nature=None, nature_per_col=None,
       layers=None, fallback=True, min_header=True, min_len=None, sort_by=None)
```

Aplicam-se a **multi-coluna** (`dict[str, list[str]]`); para single-col (`list[str]`) são
ignorados, exceto `min_len` e `nature`. Output é sempre UTF-8, LF only. `decode(encode(x)) == x`
(exceto `sort_by`, ver abaixo).

## Knobs de bytes / layout

| knob | tipo | default | efeito | byte-impact |
|---|---|---|---|---|
| `fallback` | bool | `True` | por coluna escolhe `min(tcf, raw, dict, split)` | **zero-regressão** por construção (escolhe o menor) |
| `min_header` | bool | `True` | header mínimo (meta inline, tamanhos hex, última coluna sem size) | economiza bytes de header |
| `min_len` | int\|None | `None` (auto) | override do `min_len` do OBAT (afixos com `length < min_len` viram literal) | muda bytes só quando passado |
| `sort_by` | str\|None | `None` | reordena as **linhas** pela coluna nomeada antes de encodar | **trade-off** (ver nota), **order-free** |

### `fallback` (default `True`)
Cada coluna é encodada por todos os modos disponíveis e fica com o menor: **tcf** (OBAT+HCC),
**raw** (`!`, V2-A), **dict** (`@`, V2-B), **split** (`%`, estrutural). Como escolhe estritamente o
menor, ligar nunca aumenta bytes. É o que põe colunas low-card em `@dict` automaticamente (e habilita
as queries lazy via dict-stream).
- `fallback=False` → mantém tcf em toda coluna (sem raw/dict/split).
- O formato continua `#TCF.8M`; o legado `.6/.7` é recuperado via git, não por este knob.

### `min_header` (default `True`)
Header compacto: meta inline após `#TCF.8M`, tamanhos em hexadecimal e **última coluna sem `size`** (corpo até EOF).
- `min_header=False` → todas as colunas não-anônimas recebem tamanho no meta.

### `min_len` (int ≥ 1, ou `None`)
`None` (default) = auto por coluna (`detect_min_len`, ADR-0010) — comportamento inalterado.
Um `int` aplica o **mesmo** `min_len` a **todas** as colunas (tuning manual; muda os bytes).
`min_len < 1` levanta `ValueError`.

### `sort_by` (str, ou `None`) — O-FMT-02
Reordena as linhas pela coluna-chave antes de encodar, agrupando valores similares.
- **Trade-off de compressão** (depende da correlação da chave com a estrutura): medido
  `adult sort_by="education"` **−10%**; `online-retail sort_by="CustomerID"` **+2,3%** (desarruma o
  RLE de outras colunas). Pode ganhar ou perder ~2–15%.
- **Order-free**: o `decode` retorna a ordem **ordenada**, **não** a original (a ordem original
  **não** é recuperável). Use só quando a ordem não importa — **nunca** numa transmissão que precise
  preservar ordem.
- Habilita o layout de baixa latência do gadget lazy (`group_ranges`/`agg_by` por slice).
- `ValueError` se a coluna não existe ou se as colunas têm tamanhos diferentes.

## Knobs relacionados (não-byte)

| knob | efeito |
|---|---|
| `nature` / `nature_per_col` | candidato por natureza (CPF/CNPJ/IP, ADR-0015); FLOOR compara o blob completo e o header é autoritativo. Specs core decodificam sem argumento; customizados exigem spec coincidente. Ver [how-to/use-natures](../how-to/use-natures.md). |
| `parallel` | `True`/`int` paraleliza o encode das colunas (multi-col); **output byte-idêntico** ao serial. |
| `side_outputs` | captura logs/stats internos (`column_features`, `hcc_trace`, `seq_rle_runs`, `multi_info`, ...) sem custo quando ausente. |
| `layers` | `PipelineConfig` alternativo (avançado). |

## Notas de versão

O default zero-param é **0.8** (ADR-0032: projeto é pré-1.0; `#TCF.N` são marcadores de dev, não
contratos rígidos). Os invariantes byte-canonical (D1-D9 = 1523 B, D17a = 300 B) são pinados em
[`tests/test_regression_v1_baseline.py`](../../tests/test_regression_v1_baseline.py) e
re-pináveis só com ADR (ADR-0024/0025).

## Ver também

- [ADR-0022](../adr/0022-v2a-fallback-identity-weld.md) (V2-A `!`), [ADR-0025](../adr/0025-v2b-dictionary-categorical-weld.md) (V2-B `@`), [ADR-0026](../adr/0026-structural-split-weld.md) (split `%`)
- [ADR-0023](../adr/0023-v2-minimal-header-weld.md) (header mínimo)
- [docs/algorithms/TCF-format.md](../algorithms/TCF-format.md) (spec do formato)
- [how-to/inspect-compression.md](../how-to/inspect-compression.md)
