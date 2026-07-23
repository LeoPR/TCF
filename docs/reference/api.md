# API pública do TCF — superfície de entrega (reference)

**Fonte única da superfície pública.** Se um símbolo não está aqui, **não é API** — é interno
(prefixo `_`) ou acessório (gadget fora do `src/tcf`). Objetivo: zero deslize de leitura sobre "o
que o dev usa". Contrato de tipos vive nos testes (`tests/test_multi_col_rt.py`, `test_core_rt.py`,
`test_hierarchical_rt.py`, `test_f0_boundary_fixes.py`).

```python
from tcf import encode, decode, view, SideOutputs, PipelineConfig, build_schema
from tcf import SPEC_CPF, SPEC_CNPJ, SPEC_IP, TemplatedCheckedSpec, TemplatedPaddedSpec
```

| símbolo | papel |
|---|---|
| **`encode(data, **kwargs)`** | dataset → wire `str`. **Porta única de encode**; rota por TIPO (tabela abaixo). |
| **`decode(str)`** | wire → dataset. Auto-rota pelo magic (`#TCF.8M`/`#TCF.8H`/single órfão). |
| **`view(...)` · `LazyTCF` · `Filtered`** | consulta lazy read-only (só `#TCF.8M`; ver [`lazy-view.md`](lazy-view.md)). |
| **`SideOutputs`** | telemetria opt-in (`encode(x, side_outputs=so)`). |
| **`PipelineConfig`** | toggles do pipeline flat (`encode(x, layers=cfg)`). |
| **`build_schema` · `TableSchema` · `ColumnSchema`** | schema per-tabela. |
| **specs** (`SPEC_CPF/CNPJ/IP`, `TemplatedCheckedSpec`, `TemplatedPaddedSpec`) | naturezas opt-in. |

> **Não existe `encode_hierarchical` público** (Passo 2, 2026-07-23). O hierárquico `#TCF.8H` é
> alcançado por `encode()` roteando entrada aninhada — simétrico ao `decode`. A capacidade/wire é a
> do [ADR-0033](../adr/0033-hierarchical-codec-weld.md); só a porta mudou.

## Dispatch de `encode(data)` — por tipo de entrada (type-coherent)

| entrada | rota | wire |
|---|---|---|
| `list[str]` (todos str), ≥1 item | single-col flat | órfão (0 B header) |
| `dict[str, list[str]]` retangular, **≥1 linha** | multi-col flat | `#TCF.8M` |
| `list[dict]` (dataset) · `dict` com valor escalar/aninhado · dict **ragged** ou **0-linha** · escalar solto · `[]` · `{}` · `list`/coluna **tipada** (item não-str) | hierárquico | `#TCF.8H` (`#D`/`#E`/`#O`/`#V`) |
| tipo não-JSON (bytes, tuple, função, objeto custom) ou **array de tipos mistos** (union) | **fail-loud** | — (ensina a converter/separar) |

**Regra**: só o **flat puro** (todos str) fica flat; qualquer coisa tipada/aninhada/vazia vai pro
`.8H`, que **preserva o tipo** (`[1,2,3]` → array int; `None` preservado, não vira `""`). Isso
elimina o deslize de stringificação silenciosa do pré-Passo-2.

**Contrato pré-1.0 (mudanças do Passo 2, declaradas)**: `encode([])`/`encode({})` deixaram de ser
fail-loud e viram `.8H` (`#D0`/`#E`, representáveis); `encode([1,2,3])` vira array `.8H` tipado (era
single-col `"1","2","3"`); coluna com `None`/int vira `.8H` (era stringificada no flat); tuple/bytes
no lugar de lista viram fail-loud de tipo (eram convertidos calados).

## kwargs de `encode` por rota

- **`side_outputs`**, **`nature_per_col`** ({path→spec}): valem em **todas** as rotas (flat multi e `.8H`).
- **`nature`** (spec único): só **single-col flat** (`list[str]`).
- **`parallel`, `layers`, `fallback`, `min_header`, `min_len`, `sort_by`, `name`, `stamp`, `drop_names`**:
  só **flat**. Passados com entrada `.8H` → **fail-loud** (nunca ignorados calados).

Knobs detalhados por camada: [`encode-knobs.md`](encode-knobs.md).
