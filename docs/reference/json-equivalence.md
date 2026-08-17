# TCF ↔ JSON — quasi-equivalências (referência)

> **Semente do manual.** Registro consolidado do que o `#TCF.8H` traduz de/para JSON, o que faz a
> MAIS, e a fronteira declarada. Todos os wires abaixo foram **confirmados por execução**
> (`encode` → `.tcf` → `decode`, RT — entrada aninhada roteia pro `#TCF.8H`). Estado: 2026-07-23, suíte 861 passed.
>
> **Escopo**: o TCF **não lê texto JSON** — ele lê o **dataset** (dict/array/escalar) que a
> linguagem constrói ao parsear a fonte. São **dois contratos independentes**: o da lib json
> (`texto → dataset → texto`) e o do TCF (`dataset → .tcf → dataset`). Ver
> [dataset-json-dois-contratos](../../experiments/lab/dirty/notas/2026-07/dataset-json-dois-contratos.md).

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

### 1-bis. Escala de atendimentos (owner, 2026-07-21)

O TCF **entende dataset** (dict/array/escalar), não JSON — o JSON é só uma *materialização* de um
dataset possível. O objetivo é uma **escala de níveis**, e o `.8` contrata só o primeiro:

| Nível | O que é | Estado |
|---|---|---|
| **N1 — imitar a jsonlib** | entender todo dataset **possível pro json** e, perante o resto, **comportar-se como um consumidor json** (o que a lib não round-trip`a, o TCF recusa igual). É o **contrato do `.8`**. | **contratado** |
| **N2 — além da borda** | o que a lib json *não* faz mas o TCF poderia, tipando: `"NaN"`/`"Infinity"` como valor tipado, um RFC teórico completo, `int > 2^53` exato (§3). | registrado, pós-`.8` |
| **N3 — dataset complexo** | formato de dataset rico e completo (N:N/grafo, tipos ricos) — "faria qualquer coisa" (§5). | registrado, 1.0/2.0 |

Corolário do N1 (o que o gate mede): a **classe** é o que a jsonlib **round-trip`a** — não o que só o
Python permissivo *aceita*. `NaN`/`Infinity`/chave-não-string **saem** (JSON inválido; `loads(dumps)≠x`).
`int > 2^53` **fica** (a jsonlib round-trip`a) mas leva **ressalva de interop** (I-JSON; um parser
int64/double de outra linguagem perde precisão) — a ressalva é **sinal, não recusa** (isso é N2).

**Teto (owner, 2026-07-21): o TCF nunca gera JSON — gera um DATASET.** Só emitimos um dataset na
linguagem; mesmo que o round-trip cubra construtos complexos do RFC, ainda **não produzimos JSON de
fato** — quem serializa é uma libjson (melhor) consumindo o nosso dataset. Logo o máximo do TCF é
deixar um **dataset POSSÍVEL de RFC-JSON**, e as libs que se encarreguem de serializar bem. Igualar o
melhor json-que-funciona-na-linguagem (N1) já é o alvo útil e obrigatório do `.8`.

**Questão aberta — clareza/warning** (`H-JSON-CLARITY-WARN-01`, sem solução): ser *mais capaz* que o
json não gera clareza sozinho. Se o TCF deixa um dataset que uma libjson popular não round-trip`a
(int gigante, ou N2/N3) **sem avisar**, confunde — JSON é popularíssimo. Falta um mecanismo de
**comunicação** (warning apontando pra manual/RFC, ou "extrapolamos a limitação"). O `ijson_flags`
(`scripts/bench_perf/pivot.py`) é semente; o mecanismo pleno é **pós-`.8`, indefinido** (registrado no
roadmap-hipoteses). Anotado, não resolvido.

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
| **union / tipo-misto** no mesmo slot (`[1,"a"]`, campo int-depois-string) — **exceto** a união bool+str, ver nota | fail-loud que ENSINA | **P5 RATIFICADO** fora do `.8` (union real ~0 em dado tabular; Parquet — ref. colunar — também recusa). Saída: separar por tipo OU stringificar (o TCF faz RT de qualquer string) |
| **objeto all-folhas-vazias** (`{"a":{}}`) | fail-loud que ENSINA | contagem-vazio (problema B); representação plena = registro-'0'/O-FMT-20 (armazenamento, pré-1.0) |

**Nota — a união bool+str saiu do fail-loud (2026-08-01)**: uma coluna single-col
`{bool, str, None}` com **≥1 bool E ≥1 str** tem rota própria desde a
[ADR-0039](../adr/0039-lazytype-bool-cabeca-congelada-extras.md): o **lazytype `#TCF.8bB`**,
com cabeça congelada `null=0/false=1/true=2` e extras str declarados a partir do slot 3.
Ele **preserva o tipo** — `decode(encode([True, "abc", False])) == [True, "abc", False]`,
e não `["true", "abc", "false"]`, que é o que o flat-string devolvia. É o caso concreto de
"true/false/null com exceções string" (`"other"`, `"N/A"`, `" ?"`) em dado tabular real.
Toda **outra** união escalar (`int+str`, `bool+int`, …) segue fail-loud como acima.

**Nota de propriedade (não é perda)**: **ordem de chaves** — o `.8H` devolve chaves na ordem do
**schema** (union por 1ª aparição), não na ordem por-registro do texto. É **canônico** (como
Arrow/Parquet: colunar-shredded não preserva ordem por-registro); ECMA-404 diz que ordem de chave
**não é significativa**; a igualdade semântica (dict) é sempre preservada. Só a byte-ordem de um
`json.dumps` re-serializado pode diferir (RFC permite).

## 5. Evolução além do JSON (registrado, não `.8`)

O JSON é o **alvo prático** (o que as pessoas transmitem), não o teto — o funil J0→J1→J2/L/G
([funil-fechamento-json-language](../../experiments/lab/dirty/notas/2026-07/2026-07-17-0124-funil-fechamento-json-language.md))
separa uso (fechado) de completude (registrada). Fronteiras para 1.0/2.0: **union tipado**
(dense-union à Arrow — desenho em
[p5-union-levantamento](../../experiments/lab/dirty/notas/2026-07/p5-union-levantamento.md) §4);
**N:N/grafo/shared-ref** (o que `list[dict]` não representa — a capacidade exclusiva pós-paridade);
tipos ricos (Decimal/datetime tipados).

## Fontes

Medições e decisões desta referência: labs `2026-07-17-0140` (critério de fluxo), `-0230` (escape),
`-0233` (P4b); notas `dataset-json-dois-contratos`, `escala-implementacao-paridade-json`,
`p5-union-levantamento`; ADR-0033 (§escape, §P4b); testes `test_json_flow_parity.py`,
`test_hierarchical_rt.py`, `test_hierarchical_control_synthetics.py`.
