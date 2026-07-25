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
| `list[str \| None]` (str e/ou null), ≥1 item | single-col flat | `#TCF.8` (7 B, **default**; ADR-0034) |
| `list[bool \| None]` · `list[int \| float \| None]` | single-col **tipada** | `#TCF.8b` · `#TCF.8n` |
| `dict[str, list[str]]` retangular, **≥1 linha** | multi-col flat | `#TCF.8M` |
| `list[dict]` (dataset) · `dict` com valor escalar/aninhado · dict **ragged** ou **0-linha** · escalar solto · `[]` · `{}` · `list`/coluna **tipada** (item não-str) | hierárquico | `#TCF.8H` (`#D`/`#E`/`#O`/`#V`) |
| tipo não-JSON (bytes, tuple, função, objeto custom) ou **array de tipos mistos** (union) | **fail-loud** | — (ensina a converter/separar) |

**Regra**: uma **coluna plana de um tipo só** fica no single-col — string (implícita, sem tag),
bool (`b`) ou número (`n`); `None` convive com qualquer uma delas (slot 0). Aninhado, misto,
escalar solto ou `{}` vai pro `.8H`. `None` é preservado em **todas** as rotas — nunca vira
`""` — o que elimina o deslize de stringificação silenciosa do pré-Passo-2.

### Tags de tipo do single-col

| tag | tipo | emitida? |
|---|---|---|
| *(nenhuma)* | string — o tipo **implícito por exclusão** | sim (default) |
| `b` | bool; modo denso `b1` (bit-pack) compete no FLOOR | sim |
| `n` | número (int/float, uma tag só como no JSON) | sim |
| `s` | string **explícita** | **não** — decoda, mas o encoder usa a forma implícita |

O modo denso é **bool sem null**, por construção: 1 bit são 2 estados e o trio
`{null, false, true}` não cabe. Com null, a coluna usa o modo core.

**NaN/±Inf ficam fora** (RFC 8259) nas duas pontas: o encoder recusa e o decode também.

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

## Índices de referência PRÉ-ALOCADOS (slot 0 = null)

A tabela de referências de uma coluna tem **duas metades**: os slots altos vêm do **dado**
(literais descobertos no encode) e os slots baixos vêm do **formato** (dicionário da versão,
que **não viaja no arquivo**). Essa segunda metade já existia — é o domínio `{false,true}` do
modo denso do bool. **null é outra entrada dela**, não um caso com regra própria.

| grafia | significado |
|---|---|
| `^0` | slot reservado 0 = `null` (forma explícita) |
| `0` | mesma coisa, grafia **otimizada** (a linha **inteira** igual a `0`) |
| `^1`, `^2`, … | 1º, 2º, … nó **declarado** — inalterado |

**Incondicional e grátis**: `^N` sempre foi 1-based, então `^0` era espaço morto. Ocupá-lo não
tira endereço de nenhum dado (`^1` continua sendo o 1º nó declarado, byte-idêntico) e evita
que null consuma um endereço **vivo**. Como nada viaja no wire, a consistência entre encode e
decode é garantida por ser constante da **versão** do formato.

**Desambiguação posicional**: só a linha inteira igual a `0` é o especial. Um `0` dentro de
composição (`1~0`, `0..3`) continua sendo referência de **fragmento** — então "compor uma
string com null" permanece inexprimível na gramática.

**Rota flat aceita `list[str | None]`** (2026-07-25): uma coluna de string com nulls fica no
flat em vez de ser expulsa pro `.8H`. Medido no lab `2026-07-25-1630`: **−36% mediano** em
colunas com null (pior caso −4%, melhor −58%), e **0%** — byte-idêntico — em colunas sem null.

`decode` de single-col pode devolver `list[str | None]`. Rota por tipo **inalterada**:
`[1, None]` e `[True, None]` seguem no `.8H` (tipo preservado), e `{"a": ["x", None]}`
tambem — a rota aberta e' a do single-col.

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
