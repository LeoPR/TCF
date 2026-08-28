# API pública do TCF: superfície de entrega (reference)

**Fonte única da superfície pública.** Se um símbolo não está aqui, **não é API**, é interno
(prefixo `_`) ou acessório (gadget fora do `src/tcf`). Objetivo: zero deslize de leitura sobre "o
que o dev usa". Contrato de tipos vive nos testes (`tests/test_multi_col_rt.py`, `test_core_rt.py`,
`test_hierarchical_rt.py`, `test_f0_boundary_fixes.py`).

```python
from tcf import encode, decode, view, SideOutputs, PipelineConfig, build_schema
from tcf import SPEC_CPF, SPEC_CNPJ, SPEC_IP, SPEC_DATA_ISO, SPEC_INT_PAD, SPEC_REGISTRY
from tcf import TemplatedCheckedSpec, TemplatedPaddedSpec
```

| símbolo | papel |
|---|---|
| **`encode(data, **kwargs)`** | dataset → wire `str`. **Porta única de encode**; rota por TIPO (tabela abaixo). |
| **`decode(str)`** | wire → dataset. Auto-rota pelo magic (`#TCF.8M`/`#TCF.8H`/`#TCF.8`/órfão). |
| **`view(...)` · `LazyTCF` · `Filtered`** | consulta lazy read-only: `#TCF.8M`, `#TCF.8H` retangular e a rota de coluna única (ver [`lazy-view.md`](lazy-view.md) e [`view-usos.md`](view-usos.md)). |
| **`SideOutputs`** | telemetria opt-in (`encode(x, side_outputs=so)`). |
| **`PipelineConfig`** | toggles do pipeline flat (`encode(x, layers=cfg)`). |
| **`build_schema` · `TableSchema` · `ColumnSchema`** | schema per-tabela. |
| **specs** (`SPEC_CPF/CNPJ/IP`, `TemplatedCheckedSpec`, `TemplatedPaddedSpec`) | naturezas opt-in. Os 5 do registry são públicos (`SPEC_REGISTRY` mapeia nome→spec). O **`SPEC_CNPJ` é alfanumérico** (IN RFB 2.229/2024) e cobre também o numérico, que compacta em 7 chars byte-idênticos ao wire histórico. Não há spec numérico separado ([ADR-0044](../adr/0044-cnpj-um-so-alfanumerico.md)). |

> **Não existe `encode_hierarchical` público** (Passo 2, 2026-07-23). O hierárquico `#TCF.8H` é
> alcançado por `encode()` roteando entrada aninhada, simétrico ao `decode`. A capacidade/wire é a
> do [ADR-0033](../adr/0033-hierarchical-codec-weld.md); só a porta mudou.

## Dispatch de `encode(data)`: por tipo de entrada (type-coherent)

| entrada | rota | wire |
|---|---|---|
| `list[str \| None]` (str e/ou null), ≥1 item | single-col flat | `#TCF.8` (7 B, **default**; ADR-0034) |
| `list[bool \| None]` · `list[int \| float \| None]` | single-col **tipada** | `#TCF.8b` · `#TCF.8n` |
| `dict[str, list[str]]` retangular, **0 linhas inclusive** | multi-col flat | `#TCF.8M` |
| `list[dict]` (dataset) · `dict` com valor escalar/aninhado · dict **ragged** · escalar solto · `[]` · `{}` · `list`/coluna **tipada** (item não-str) | hierárquico | `#TCF.8H` (`#D`/`#E`/`#O`/`#V`) |
| `list[bool \| str \| None]` com **≥1 bool E ≥1 str** | single-col **lazytype** | `#TCF.8bB` (ADR-0039) |
| tipo não-JSON (bytes, tuple, função, objeto custom) ou **array de tipos mistos** (union) **fora** da união bool+str | **fail-loud** | nenhum (ensina a converter/separar) |

> **Tabela de 0 linhas (2026-08-26).** `{"v": []}` sai em `#TCF.8M@v` + `0` (12 B), e não
> mais em `#TCF.8H` (18 B). O corpo `@` conta linhas por `len(stream) // width`, e não por
> separador, então stream vazio diz **zero** sem colidir com *uma linha vazia* (que sai no
> modo `!`, com corpo de zero byte). Antes disso, tirar a última linha fazia o wire **crescer**.
> O `.8H` continua dono do **ragged** e do `{}`. Uma spec declarada numa coluna de 0 linhas
> continua **fail-loud**: não há valor a transformar, e aplicar calado esconderia a
> declaração.

**Regra**: uma **coluna plana de um tipo só** fica no single-col, string (implícita, sem tag),
bool (`b`) ou número (`n`); `None` convive com qualquer uma delas (slot 0). Aninhado, misto,
escalar solto ou `{}` vai pro `.8H`. `None` é preservado em **todas** as rotas (nunca vira
`""`), o que elimina o deslize de stringificação silenciosa do pré-Passo-2.

### Tags de tipo do single-col

| tag | tipo | emitida? |
|---|---|---|
| *(nenhuma)* | string, o tipo **implícito por exclusão** | sim (default) |
| `b` | bool; três modos no índice 7: `b1`, `b2`, `bB` (abaixo) | sim |
| `n` | número (int/float, uma tag só como no JSON) | sim |
| `s` | string **explícita** | **não**: decoda, mas o encoder usa a forma implícita |

#### Os três modos da tag `b`

| modo | domínio | quando |
|---|---|---|
| `b1` | `{false, true}`, 1 bit/símbolo | bool **sem** null; compete no FLOOR |
| `b2` | `{null, false, true}`, 2 bits/símbolo, cabeça **congelada e implícita** (nunca viaja) | bool **com** null |
| `bB` | cabeça congelada `null=0/false=1/true=2` + **extras str declarados** a partir do slot 3 | união `{bool, str, None}` com ≥1 bool E ≥1 str |

Verificável (o modo aparece no índice 7 do header):

```python
encode([True, False] * 12).splitlines()[0]          # '#TCF.8b118'
encode([True, False, None, True] * 6).splitlines()[0]  # '#TCF.8b218'
encode([True, "abc", False]).splitlines()[0]        # '#TCF.8bB23'
```

O `bB` é o **único** candidato que preserva o tipo na união, e por isso emite direto, sem
passar pelo `min()`. As demais uniões escalares (`int+str`, `bool+int`, …) seguem fail-loud.

> **A união bool+str é do single-col, e só dele (2026-08-27).** `{"v": [True, "x"]}` e
> `[{"v": True}, {"v": "x"}]` **levantam**: o `.8M` e o `.8H` não têm esse discriminador e
> recusam toda coluna de tipos mistos, pelo mesmo juiz. Estender a união às outras duas
> famílias, ou removê-la do single-col, é decisão de formato do `.9`
> ([`BUG-ENCODE-VAZIO-EM-COLUNA-TIPADA`](../../tickets/BUG-ENCODE-VAZIO-EM-COLUNA-TIPADA.md)).

**NaN/±Inf ficam fora** (RFC 8259) nas duas pontas: o encoder recusa e o decode também.

**Contrato pré-1.0**: `encode([])`/`encode({})` são **representáveis**; `encode([1,2,3])`
**preserva o tipo** (volta `int`, não `"1","2","3"`); coluna com `None`/int não é
stringificada; `tuple`/`bytes` no lugar de lista dão **fail-loud** de tipo.

| entrada | wire real | rota |
|---|---|---|
| `encode([])` | `'#TCF.8\n'` (7 B) | single-col flat, **não** `.8H`, **não** `#D0` |
| `encode({})` | `'#TCF.8H#E\n'` (10 B) | `.8H`, **a única das três que estava certa** |
| `encode([1,2,3])` | `'#TCF.8n…'` | single-col **tipada** (tag `n`), não `.8H` |
| `encode([1, None])` | `'#TCF.8n…'` | single-col tipada |
| `encode([True, None])` | `'#TCF.8b…'` | single-col tipada |
| `encode(["x", None])` | `'#TCF.8…'` | single-col flat (slot 0 = null) |
| `{"a": ["x", None]}` | `'#TCF.8H#Oa#:3?:5['` | `.8H`, o null só puxa pro `.8H` **dentro de um dict** |

O tipo é preservado nos sete casos (round-trip validado); o que muda é **por qual rota**.

## kwargs de `encode` por rota

- **`side_outputs`**, **`schema`**: valem em **todas** as rotas. O `schema` é o parâmetro
  **único** de spec ([ADR-0047](../adr/0047-schema-parametro-unico-de-spec.md)): aceita
  `"cpf"` (nome do registry), objeto spec, ou `{coluna: spec}` com chave `str` (nome) ou
  `int` (posição). É incremental: sem ele, toda coluna é string semântica.
- **`parallel`, `layers`, `fallback`, `min_header`, `min_len`, `sort_by`, `name`, `stamp`, `drop_names`**:
  só **flat**. Passados com entrada `.8H` → **fail-loud** (nunca ignorados calados).
  - **Exceção declarada, tabela de 0 linhas**: ela agora é flat (`.8M`), então esses kwargs
    são aceitos. Quase todos são inertes sobre uma tabela sem corpo. O `fallback=False` é o
    caso com efeito: ele **não** desliga o corpo `@` do vazio, porque o candidato `raw` de 0
    linhas tem corpo de zero byte e volta como *uma linha vazia*. É desobediência
    deliberada: nenhum knob de bytes compra perda de dado.

### `stamp`: o header do single-col

`None` (default) e `True` → wire **com** `#TCF.8\n`. **É o default em 100% dos casos**, mesmo
com conteúdo vazio ([ADR-0034](../adr/0034-header-default-100-porcento-single-col.md)): o
artefato se auto-explica em vez de depender de quem o produziu. Custa 7 B, e isso é aceito.

`stamp=False` → **escape explícito** (órfão, sem header). Só para (a) **transmissão**, onde o
contrato vive nas pontas, e (b) **container que já carrega o contrato** (ex.: parquet). Fora
disso, sair do default é erro.

O header é do **artefato**, não da coluna: o `.8H` usa `encode` internamente como compressor
de coluna e passa `stamp=False`. Todo wire tem **exatamente 1** header.

Knobs detalhados por camada: [`encode-knobs.md`](encode-knobs.md).

## Índices de referência PRÉ-ALOCADOS (slot 0 = null)

A tabela de referências de uma coluna tem **duas metades**: os slots altos vêm do **dado**
(literais descobertos no encode) e os slots baixos vêm do **formato** (dicionário da versão,
que **não viaja no arquivo**). Essa segunda metade já existia: é o domínio `{false,true}` do
modo denso do bool. **null é outra entrada dela**, não um caso com regra própria.

| grafia | significado |
|---|---|
| `^0` | slot reservado 0 = `null` (forma explícita) |
| `0` | mesma coisa, grafia **otimizada** (a linha **inteira** igual a `0`) |
| `^1`, `^2`, … | 1º, 2º, … nó **declarado** (inalterado) |

**Incondicional e grátis**: `^N` sempre foi 1-based, então `^0` era espaço morto. Ocupá-lo não
tira endereço de nenhum dado (`^1` continua sendo o 1º nó declarado, byte-idêntico) e evita
que null consuma um endereço **vivo**. Como nada viaja no wire, a consistência entre encode e
decode é garantida por ser constante da **versão** do formato.

**Desambiguação posicional**: só a linha inteira igual a `0` é o especial. Um `0` dentro de
composição (`1~0`, `0..3`) continua sendo referência de **fragmento**, então "compor uma
string com null" permanece inexprimível na gramática.

**Rota flat aceita `list[str | None]`** (2026-07-25): uma coluna de string com nulls fica no
flat em vez de ser expulsa pro `.8H`. Medido no lab `2026-07-25-1630`: **−36% mediano** em
colunas com null (pior caso −4%, melhor −58%), e **0%** (byte-idêntico) em colunas sem null.

`decode` de single-col pode devolver `list[str | None]`. Rota por tipo **inalterada**: o tipo é
preservado em todos os casos; o que muda é por onde: `[1, None]` sai `#TCF.8n` e `[True, None]`
sai `#TCF.8b` (**single-col tipado**, não `.8H`); só `{"a": ["x", None]}` vai pro `.8H`
(`#TCF.8H#Oa#:3?:5[`). O null puxa pro hierárquico apenas **dentro de um dict**.

## kwargs de `decode`

- **`schema`**: reverse da pré-tx out-of-band (ADR-0015), mesmas formas do encode (incluindo a
  sobrecarga escalar em wire de UMA coluna; em 2+ o escalar é recusado ensinando); o header é
  autoritativo. O schema é **incremental**: só toca o que nomeia.
- **`max_length`**: **teto de descompressão**. Nome e a convenção `0 == sem teto` vêm do
  `zlib`/`bz2`/`lzma`. Unidade = **elementos** decodificados (não bytes: é o que a expansão
  aloca), **por coluna**. `None` → default `10_000_000`.

  Existe porque `*N|` é um repetidor: sem teto, um wire de 15 B pede 1e9 elementos (~8 GB).
  Wire produzido pelo `encode` **nunca** encosta no teto: só entrada corrompida ou hostil.
  Estourar é **fail-loud** (um warning sairia depois da alocação, tarde demais); a mensagem
  nomeia o parâmetro a subir.

  ```python
  decode(wire)                          # teto default
  decode(wire, max_length=50_000_000)   # afrouxa
  decode(wire, max_length=0)            # sem teto (convenção zlib)
  decode(wire, max_length=10_000)       # aperta, p/ entrada não-confiável
  ```

  O default é generoso para nunca barrar wire legítimo, logo corta o **catastrófico**, não o
  **caro**: 13 B ainda produzem 10M elementos. Quem processa entrada hostil deve apertar.
