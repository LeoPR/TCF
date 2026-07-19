# TCF ↔ JSON — quasi-equivalências (referência)

> **Semente do manual.** Registro consolidado do que o `#TCF.8H` traduz de/para JSON, o que faz a
> MAIS, e a fronteira declarada. Todos os wires abaixo foram **confirmados por execução**
> (`encode_hierarchical` → `.tcf` → `decode`, RT). Estado: 2026-07-17, suíte 853 passed.
>
> **Escopo**: o TCF **não lê texto JSON** — ele lê o **dataset** (dict/array/escalar) que a
> linguagem constrói ao parsear a fonte. São **dois contratos independentes**: o da lib json
> (`texto → dataset → texto`) e o do TCF (`dataset → .tcf → dataset`). Ver
> [dataset-json-dois-contratos](../../experiments/lab/dirty/notas/dataset-json-dois-contratos.md).

## 1. A classe D_json (o que o TCF traduz de JSON)

**D_json** = a imagem do que a lib json gera na linguagem, definida pela **tabela oficial de
conversão** do módulo `json` (CPython) + RFC 8259/7493:

```
dict[str, D]  ·  list[D]  ·  str (Unicode transmissível)  ·  int  ·  float FINITO
              ·  True  ·  False  ·  None          — e qualquer um deles na RAIZ
```

Critério de equivalência (executável, `tests/test_json_flow_parity.py`):
**∀D ∈ D_json:  json faz round-trip ⟹ TCF faz round-trip** (medido sobre bytes UTF-8, com a etapa
de transmissão). Hoje: **`LACUNAS = {}`** — D_json completo.

## 2. Tabela de equivalência (construto JSON → `.8H`)

| construto JSON | incremento | wire `.8H` (exemplo) | RT |
|---|---|---|:--:|
| objeto `{}` (1:1) | espinha | `#TCF.8Ha:3n,nome` | ✅ |
| aninhamento arbitrário | espinha | `#TCF.8Ha{b#:3[]:8n` | ✅ |
| array de objetos (1:N) | espinha | `#TCF.8Hitens#:3[n:8n` | ✅ |
| **chave opcional / ragged** | P1 | `#TCF.8Ha:8n,b?:4:3n` (máscara 3-estados) | ✅ |
| **number (int/float)** | P2 | `#TCF.8Hn:4n` (tag `n`, `json.dumps/loads`) | ✅ |
| **`true`/`false`** | P2 | `#TCF.8Hok:5b` (tag `b`) | ✅ |
| **`null` em campo** (≠ ausente ≠ `"null"`) | P3a | `#TCF.8Ha?:3:0,b:3n` (máscara `0`=None) | ✅ |
| **`null` em elemento de array** | P3b | `#TCF.8Hv#:3?:8[]:8n` (element-mask) | ✅ |
| **array-em-array** (profundidade arbitrária) | P4a | `#TCF.8Hm#:3[#:8[]:8n` (count recursivo) | ✅ |
| **raiz = objeto único** | P4b | `#TCF.8H#Oa:3n` | ✅ |
| **raiz = array** | P4b | `#TCF.8H#V\z#:3[]:8n` (envelope) | ✅ |
| **raiz = escalar / string / null** | P4b | `#TCF.8H#V\z:4n` · `#V\z?:3` | ✅ |
| **raiz = `[]` / `[{}]` / `[{},{}]`** | P4b | `#TCF.8H#D0` · `#D1` · `#D2` | ✅ |
| **raiz = `{}`** | P4b | `#TCF.8H#E` (definição) | ✅ |
| string (unicode, separadores, `\t`, `\x00`) | espinha+escape | — (RT-exato) | ✅ |
| **`\n`/`\r`/`\\` em valor** (multilinha) | escape D_json | folha escapada (L1 intocado) | ✅ |
| **chave `""` · chave com `\n`/`\r`** | escape D_json | `\z` / `\n` no meta | ✅ |
| chave NFC vs NFD (parecem iguais) | — | distintas, preservadas | ✅ |

## 3. O que o TCF faz A MAIS que o JSON de interoperabilidade

- **⊃ I-JSON em inteiros**: `int > 2^53` faz RT no TCF (`#TCF.8Ha:18n`); a RFC 7493 (I-JSON) os
  **proíbe** (§2.2, faixa segura IEEE 754). O TCF preserva o inteiro exato.
- **É mais SEGURO que o `json.dumps` do Python** em 4 pontos (o TCF fail-louda onde o json perde
  calado — ver §4): NaN/Infinity, tuple→list, chave não-str (o json **fabrica duplicata**), lone
  surrogate (o json faz RT mas o texto não é UTF-8 transmissível).
- **Explicável enquanto comprimido**: o wire é textual e inspecionável — RLE/counts/masks mostram
  agrupamento sem descomprimir (ver [lazy-view](lazy-view.md): `select`/`where`/agregação
  column-pruning). JSON não tem esse eixo.
- **Estrutura tabular-plana nativa** (o `.8M`), fora do escopo desta tabela.

## 4. A fronteira declarada (o que o TCF NÃO traduz — e por quê)

Fora de D_json — **não é lacuna, é a fronteira** (a própria doc das libs declara perda aqui):

| fora de D_json | `.8H` | razão |
|---|---|---|
| **NaN / ±Infinity** | fail-loud | RFC 8259 §6 não permite; NaN quebra RT (`nan != nan`). O Python emite por default (extensão declarada) |
| **tuple** | fail-loud | a tabela oficial mapeia tuple→array→list: o tipo não volta |
| **chave não-string** | fail-loud tipado | o `json.dumps` coage e **perde** (`loads(dumps(x)) != x`) |
| **lone surrogate** | fail-loud | não é UTF-8 transmissível (RFC 8259 §8.1; I-JSON §2.1) |
| **union / tipo-misto** no mesmo slot (`[1,"a"]`, campo int-depois-string) | fail-loud que ENSINA | **P5 RATIFICADO** fora do `.8` (union real ~0 em dado tabular; Parquet — ref. colunar — também recusa). Saída: separar por tipo OU stringificar (o TCF faz RT de qualquer string) |
| **objeto all-folhas-vazias** (`{"a":{}}`) | fail-loud que ENSINA | contagem-vazio (problema B); representação plena = registro-'0'/O-FMT-20 (armazenamento, pré-1.0) |

**Nota de propriedade (não é perda)**: **ordem de chaves** — o `.8H` devolve chaves na ordem do
**schema** (union por 1ª aparição), não na ordem por-registro do texto. É **canônico** (como
Arrow/Parquet: colunar-shredded não preserva ordem por-registro); ECMA-404 diz que ordem de chave
**não é significativa**; a igualdade semântica (dict) é sempre preservada. Só a byte-ordem de um
`json.dumps` re-serializado pode diferir (RFC permite).

## 5. Evolução além do JSON (registrado, não `.8`)

O JSON é o **alvo prático** (o que as pessoas transmitem), não o teto — o funil J0→J1→J2/L/G
([funil-fechamento-json-language](../../experiments/lab/dirty/notas/funil-fechamento-json-language-2026-07-17.md))
separa uso (fechado) de completude (registrada). Fronteiras para 1.0/2.0: **union tipado**
(dense-union à Arrow — desenho em
[p5-union-levantamento](../../experiments/lab/dirty/notas/p5-union-levantamento.md) §4);
**N:N/grafo/shared-ref** (o que `list[dict]` não representa — a capacidade exclusiva pós-paridade);
tipos ricos (Decimal/datetime tipados).

## Fontes

Medições e decisões desta referência: labs `2026-07-17-0140` (critério de fluxo), `-0230` (escape),
`-0233` (P4b); notas `dataset-json-dois-contratos`, `escala-implementacao-paridade-json`,
`p5-union-levantamento`; ADR-0033 (§escape, §P4b); testes `test_json_flow_parity.py`,
`test_hierarchical_rt.py`, `test_hierarchical_control_synthetics.py`.
