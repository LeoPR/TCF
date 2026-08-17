# 2026-08-17 — REGISTRO: limites de hierarquia — o que temos, a literatura, o que faltava

**[probatório onde diz medido; dispositivo no resto.]** Pedido do owner: *"pesquise outras
estruturas complexas de hierarquia, crie testes sintéticos, lembro que tínhamos pesquisado
sobre alguns limites, registre. veja literatura, rfcs, json, outros formatos"*.

Método: primeiro **achar o que já existe no repo** (lição EXP-012), depois complementar
fora, depois medir só o buraco.

---

## 1. O que JÁ tínhamos (e onde)

| tema | estado | onde |
|---|---|---|
| **Chave repetida** | FECHADO — normas (ECMA-404 vs RFC 8259 §4) + medição do `json.loads` (last-wins calado) + decisão S0 fail-loud revisada | [`json-chave-repetida-levantamento`](../2026-07/json-chave-repetida-levantamento.md) + lab `2026-07-17-0050` |
| **`int > 2^53`** | FECHADO — RT exato no TCF, **⊃ I-JSON** (RFC 7493 §2.2 proíbe; nós preservamos), ressalva de interop é sinal, não recusa | [`json-equivalence.md`](../../../../docs/reference/json-equivalence.md) §N2, :80-81 |
| **Array-em-array** | funciona (P4a, count recursivo) — profundidade dita "arbitrária" **sem medição do teto** | `json-equivalence.md:67` |
| **Modelo Dremel** | mapeado: máscara `?` = definition-level; contagem `#` = repetition-level; validity-bitmap do Arrow citado | ADR-0033 `:117,163,207,222` |
| **NaN/±Inf, tuple, chave não-str, lone surrogate, union, all-folhas-vazias** | fronteira declarada, fail-loud | `json-equivalence.md` §fronteira |
| **Funil J0→J1→J2→L→G** | os cinco patamares definidos; J0 fechado; G = DAG/N:N/grafos (direção v2.0) | [`funil-fechamento`](../2026-07/2026-07-17-0124-funil-fechamento-json-language.md) |
| **Bordas de ROTA** (o que cai no `.8H`, 40 formas) | medido no retrato do H (workflow `wf_091c3b09`) | lab `0400` + INDEX 08-17 |

## 2. O que a literatura diz (verificado 2026-08-17)

### Profundidade — o texto permite, o parser limita

RFC 8259 §9: *"An implementation may set limits on the maximum depth of nesting."* O JSON
não tem teto; cada parser inventa o seu — e os defaults reais variam **100×**:

| parser/formato | default | mecanismo |
|---|--:|---|
| MongoDB / BSON | **100** | limite de servidor, documentado |
| serde_json (Rust) | **128** | `Deserializer`; feature `unbounded_depth` desliga |
| Jackson (Java) | **1000** | `StreamReadConstraints.maxNestingDepth` (2.15+, anti-DoS) |
| Python `json` | ~`sys.recursionlimit` | recursão; `RecursionError` cru |
| protobuf-go | **10 000** | recursion limit no unmarshal |

Fontes: [serde-rs/json #334](https://github.com/serde-rs/json/issues/334) ·
[jackson-core #637](https://github.com/FasterXML/jackson-core/issues/637) ·
[MongoDB Limits](https://www.mongodb.com/docs/manual/reference/limits/) ·
[protobuf-go v1.28.0](https://github.com/protocolbuffers/protobuf-go/releases/tag/v1.28.0).

### Modelos de hierarquia dos vizinhos (pro funil L/G)

| formato | aninhamento | união | chave dinâmica | recursão de schema |
|---|---|---|---|---|
| **Parquet/Dremel** | shredding por r/d-levels (nosso espelho, ADR-0033) | não | não (schema fixo) | **não** |
| **Arrow** | `List`/`Struct`/`Map` | **`Union` (sparse/dense) existe** | `Map` | não |
| **Avro** | records/arrays/maps | **union é o idioma** (nullable = `[null, T]`) | `map<T>` | **SIM — named types** (árvores/listas ligadas) |
| **Protobuf** | messages aninhadas | `oneof` | `map<k,v>` | sim |
| **CBOR** (RFC 8949) | livre | — | **chave não-string é válida** | não |
| **YAML** | livre | — | — | **âncoras/aliases = DAG** |

O que isso diz pro TCF: a recusa de union (P5) diverge de Arrow/Avro **por decisão** — em
Avro o nullable É union, enquanto nós resolvemos null com máscara (definition-level), que é
o modelo Parquet. Recursão de schema (Avro) e DAG (YAML) são exatamente a camada **G** do
funil — registrado como direção, não como pendência do `.8`.

## 3. O que foi MEDIDO agora (lab [`0600`](../../2026-08/2026-08-17/2026-08-17-0600-limites-de-profundidade-do-H/))

1. **O `.8H` tem guarda tipada em 128 níveis** — `_MAX_DEPTH = 128`
   (`hierarchical.py:305`), aplicada em encode, parse de forma E decode. Quebra com
   `HierarchicalError` de mensagem clara, nunca `RecursionError`. Coincide com o default
   do serde_json; acima do MongoDB. **Não estava documentada em doc vivo** — corrigido
   no `json-equivalence.md` neste commit.
2. **Largura sem teto próprio**: 16 384 chaves num objeto passam com RT; header linear.
3. **Escape no nome de campo cobre os 4 chars do meta**: `{` `#` `[` `?` viram `\{` `\#`
   `\[` `\?`; unicode multi-byte passa cru. RT em todos.
4. **Campo duplicado forjado no wire → fail-loud** (`campo duplicado 'a' no header`).
   Fecha o elo que o levantamento de chave repetida deixou: lá era o *texto* JSON; aqui é
   o *wire* `.8H`. Família "erro" da RFC 8259 §4, coerente com a decisão S0.
5. Casos mínimos novos com wire legível: objeto-em-array-em-objeto (`a#:6[b`), ordem de
   schema, bigint minimal.

## 4. O que segue ABERTO (registrado, sem ticket novo)

- **Union tipada** (Arrow/Avro): recusada por P5; a exceção viva é o lazytype `bB`
  (bool+str). Se um dia abrir, o modelo de referência é o dense-union do Arrow.
- **Recursão de schema / DAG / N:N**: camada G do funil — v2.0, coerente com
  [`project_json_alvo_pratico_objetivo_amplo`].
- **Chave não-string** (CBOR aceita): fora do D_json, segue fail-loud.
- **O limite 128 é congelável?** Hoje é constante interna. Se algum corpus real
  precisar de mais, a decisão é do owner (o serde_json expõe knob; nós não).

## Conexões

- Labs do dia: [`0400`](../../2026-08/2026-08-17/2026-08-17-0400-o-candidato-unico-do-H/) ·
  [`0500`](../../2026-08/2026-08-17/2026-08-17-0500-header-do-H-sintetico/) ·
  [`0600`](../../2026-08/2026-08-17/2026-08-17-0600-limites-de-profundidade-do-H/)
- Fronteira: [`docs/reference/json-equivalence.md`](../../../../docs/reference/json-equivalence.md)
- Funil: [`2026-07-17-0124`](../2026-07/2026-07-17-0124-funil-fechamento-json-language.md)
- ADR-0033 (Dremel/validity-bitmap): `docs/adr/0033-hierarchical-codec-weld.md:117,163,207`
