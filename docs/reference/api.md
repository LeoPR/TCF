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
| **`decode(str)`** | wire → dataset. Auto-rota pelo magic (`#TCF.8M`/`#TCF.8H`/`#TCF.8`/órfão). |
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
| `list[str]` (todos str), ≥1 item | single-col flat | `#TCF.8` (7 B, **default**; ADR-0034) |
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

### `stamp` — o header do single-col

`None` (default) e `True` → wire **com** `#TCF.8\n`. **É o default em 100% dos casos**, mesmo
com conteúdo vazio ([ADR-0034](../adr/0034-header-default-100-porcento-single-col.md)): o
artefato se auto-explica em vez de depender de quem o produziu. Custa 7 B, e isso é aceito.

`stamp=False` → **escape explícito** (órfão, sem header). Só para (a) **transmissão**, onde o
contrato vive nas pontas, e (b) **container que já carrega o contrato** (ex.: parquet). Fora
disso, sair do default é erro.

O header é do **artefato**, não da coluna: o `.8H` usa `encode` internamente como compressor
de coluna e passa `stamp=False` — todo wire tem **exatamente 1** header.

Knobs detalhados por camada: [`encode-knobs.md`](encode-knobs.md).

## kwargs de `decode`

- **`nature`** / **`nature_per_col`**: reverse da pré-tx (ADR-0015).
- **`max_length`** — **teto de descompressão**. Nome e a convenção `0 == sem teto` vêm do
  `zlib`/`bz2`/`lzma`. Unidade = **elementos** decodificados (não bytes: é o que a expansão
  aloca), **por coluna**. `None` → default `10_000_000`.

  Existe porque `*N|` é um repetidor: sem teto, um wire de 15 B pede 1e9 elementos (~8 GB).
  Wire produzido pelo `encode` **nunca** encosta no teto — só entrada corrompida ou hostil.
  Estourar é **fail-loud** (um warning sairia depois da alocação, tarde demais); a mensagem
  nomeia o parâmetro a subir.

  ```python
  decode(wire)                          # teto default
  decode(wire, max_length=50_000_000)   # afrouxa
  decode(wire, max_length=0)            # sem teto (convenção zlib)
  decode(wire, max_length=10_000)       # aperta, p/ entrada não-confiável
  ```

  O default é generoso para nunca barrar wire legítimo — logo corta o **catastrófico**, não o
  **caro**: 13 B ainda produzem 10M elementos. Quem processa entrada hostil deve apertar.
