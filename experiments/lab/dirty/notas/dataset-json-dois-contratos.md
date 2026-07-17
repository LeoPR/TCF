---
title: DOIS CONTRATOS — o TCF lê DATASET, não JSON (a classe D_json definida por documento oficial)
type: report
status: aberta
created: 2026-07-17
related:
  - experiments/lab/dirty/2026-07-17-0140-paridade-fluxo-json-vs-tcf/ (o lab, re-enquadrado)
  - experiments/lab/dirty/notas/escala-implementacao-paridade-json.md (a escala — conclusões mantidas)
  - experiments/lab/dirty/notas/perfil-json-like-condicoes-parametro.md
  - tests/test_json_flow_parity.py (os pinos, re-enquadrados)
  - tickets/T-CODE-TCF8H-JSON-PARITY.md
  - tickets/T-STUDY-DATASETH-COMPLETE-SEMANTICS.md (contrato S0)
---

# Dois contratos: o TCF lê dataset, não JSON

**[dispositivo→registro + probatório]** Correção de enquadramento do owner (2026-07-17):
*"o tcf não é json... o TCF não lê Json de fato, ele lê um dataset que PODE ser resultado de um
json... não podemos depender da linguagem pra implementar... temos que seguir documentos oficiais...
usamos o python como guia pois tudo está implementado, mas deixamos essa camada bem modularizada."*
Tudo em §2-§4 é citação de documento oficial ou medição.

## 1. A arquitetura: dois contratos independentes

```
CONTRATO A (da lib json — NÃO é responsabilidade do TCF; é nossa responsabilidade CONHECER):
    texto JSON --loads--> dataset --dumps--> texto JSON      (100%? onde a DOC diz que quebra?)

CONTRATO B (do TCF — o único que o core assina):
    dataset --encode--> .tcf --decode--> dataset             (100% sobre a classe D_json)

COMPOSIÇÃO (o "caso encerrado" do owner):
    A 100% sobre D_json  ∧  B 100% sobre D_json   ⟹   transporte fecha em qualquer combinação
```

O core do TCF **não vê texto JSON, nunca**. Ele lê as condições de dataset. JSON é o *exemplo
popular a seguir* (define a classe mínima D_json), não uma dependência. Banco de dados, XML,
protobuf — cada fonte tem sua tradução para dataset; nossa missão é **ajudar com exemplos de
tradução (adaptadores, fora do core)**, e o core só precisa cobrir a classe.

**Correção ao enquadramento anterior**: nada é "limite da linguagem" como desculpa. A régua é:
(1) a **norma** define o modelo; (2) a **documentação oficial da lib** declara como ela mapeia
norma↔dataset e ONDE desvia; (3) se a doc declara conformidade e o round-trip quebra, o erro é
NOSSO uso — se a doc declara o desvio, o desvio é **contrato conhecido**, não surpresa.

## 2. O Contrato A do CPython — o que a DOC OFICIAL declara (3.13, verbatim)

A doc **não alega conformidade total** — ela declara os desvios, um a um:

> *"This module does not comply with the RFC in a strict fashion, implementing some extensions
> that are valid JavaScript but not valid JSON. In particular: Infinite and NaN number values are
> accepted and output; Repeated names within an object are accepted, and only the value of the
> last name-value pair is used."*

E dá os **interruptores de conformidade estrita** — a própria doc diz como ser RFC-strict:

| desvio declarado | interruptor documentado | citação |
|---|---|---|
| NaN/Infinity aceitos e emitidos | `allow_nan=False` no dump | *"...will result in a ValueError, **in strict compliance with the JSON specification**"* |
| NaN/Infinity aceitos no load | `parse_constant` | *"can be used to raise an exception if invalid JSON numbers are encountered"* |
| nomes repetidos: last-wins | `object_pairs_hook` | *"The object_pairs_hook parameter can be used to alter this behavior"* |
| chave não-str coagida | — (declarado LOSSY) | *"**loads(dumps(x)) != x** if x has non-string keys"* — a doc AVISA que o round-trip quebra |
| surrogates não-Unicode | — (declarado) | *"By default, this module accepts and outputs... code points for such sequences"* + alerta de interop |
| encoding | — | *"The RFC requires that JSON be represented using either UTF-8, UTF-16, or UTF-32, with UTF-8 being the recommended default"*; BOM na entrada → `ValueError` |

**A tabela de conversão oficial** (a definição documental do mapeamento):
encode: `dict→object · list,tuple→array · str→string · int,float→number · True/False→true/false ·
None→null`; decode: `object→dict · array→list · string→str · number(int)→int · number(real)→float
· true/false→True/False · null→None`. Nota da doc: o decode entende NaN/Infinity/-Infinity
*"which is outside the JSON spec"*.

**Resposta à pergunta do owner** ("as libs estão atendendo o roundtrip?"): **sim, e a doc diz
exatamente onde não** — chaves não-str (declarado `!=`), tuple (a tabela mostra `tuple→array` na
ida e `array→list` na volta: o tipo não retorna, POR TABELA), NaN/Inf (extensão declarada,
desligável), surrogates (declarado, com alerta). **Dentro do resto, o round-trip é contrato
documentado.**

## 3. A classe D_json — definida por documento, não por experimento

**D_json** = fecho recursivo de:

```
dict[str, D]  ·  list[D]  ·  str (Unicode válido/transmissível)  ·  int  ·  float FINITO
              ·  True  ·  False  ·  None          — e qualquer um deles na RAIZ
```

Cada construtor vem da **tabela oficial de decode** (só produz esses 8) + norma: float finito
(RFC 8259 §6: *"Infinity and NaN are not permitted"*), chaves str (§4: `member = string
name-separator value`), raiz livre (§2: *"A JSON text is a serialized value"* — a restrição
objeto/array é da RFC 4627, revogada), Unicode válido (§8.1 MUST UTF-8; I-JSON §2.1 MUST NOT
surrogates). **É a imagem exata do decode documentado sob entrada conformante.**

O que fica FORA de D_json — e portanto FORA de qualquer teste de paridade: NaN/±Inf, tuple,
chave não-str, surrogate solto. Não porque "a linguagem não deixa", mas porque **a norma não os
tem no modelo e a doc da lib declara o mapeamento como lossy/extensão**. Esses casos pertencem à
fronteira "dataset ⊃ JSON" (o TCF decide o que fazer com eles POR SI — hoje: fail-loud; futuro:
representar, E7/[[H-HIER-SCALAR-01]]).

## 4. O Contrato A nas outras linguagens (pesquisa 2026-07-17, doc oficial/fonte citada)

Confirma que o modelo D_json é o invariante — e que **cada lib documenta seus desvios**:

| lib | NaN/Inf | dup no parse | chave não-str | surrogate | raiz |
|---|---|---|---|---|---|
| **CPython 3.13** | emite tokens (`allow_nan=True` default) — desvio DECLARADO | last-wins DECLARADO | coerção; doc DECLARA `loads(dumps(x))!=x`; `TypeError` p/ tipos não-básicos | aceita/emite — DECLARADO | ✅ livre |
| **JS (ECMA-262)** | `stringify→null` **normativo, sem toggle**; `parse` lança | last-wins **normativo** (spec com exemplo) | **inexpressível** (chave coage na CRIAÇÃO do objeto) | escape incondicional (well-formed stringify, ES2019) | ✅ (Assert da spec enumera) |
| **Rust serde_json 1.0.150** (medido) | `to_string(NAN)`→**`null` SILENCIOSO** (fonte: `ser.rs` classifica NaN/Inf→`write_null`) | Value/HashMap: last-wins; **struct `deny_unknown_fields`: erro** | mapa tipado não mistura (E0308); `HashMap<i32,_>`→coage; tupla-chave→**Err** loud | **inexpressível** (String é UTF-8 por construção; 3 barreiras) | ✅ |
| **Go encoding/json** | **fail-loud**: `UnsupportedValueError` (único!) | substituição p/ escalares, **MERGE p/ maps/structs** (≠ last-wins!) | tipo único por map; MAS chaves `TextMarshaler` podem **EMITIR duplicata** | literal não compila; bytes crus → **U+FFFD calado** (doc declara) | ✅ |
| **C++ nlohmann** | `dump`→`null` (declarado; overflow de double idem) | doc diz *"unspecified"*; código é last-wins | inexpressível (`std::map<std::string,·>`) | **type_error.316 no dump** (fail-loud) | ✅ |
| **C++ RapidJSON** | strict nas 2 pontas (flags default `kNoFlags`); `WriteDouble(NaN)`→`false` fácil de ignorar | **PRESERVA duplicatas** (a 3ª família da RFC; DOM em array, `FindMember` linear) | inexpressível (`\pre name.IsString()`) | `kParseErrorStringUnicodeSurrogateInvalid` | ✅ |

Leituras: (1) **ninguém além do CPython emite o token `NaN`** — o ecossistema faz null-out
(JS/serde/nlohmann), fail-loud (Go) ou strict (RapidJSON); (2) as **3 famílias da RFC 8259 §4
existem de verdade** (last-wins: py/js/serde; erro: serde-typed/Go-v2-security; preserva: RapidJSON)
— duplicata é MESMO "unpredictable" entre receptores; (3) nlohmann **reordena chaves
alfabeticamente** (parse→dump não é byte-estável) — contraste que valoriza nosso determinismo.

### ⚠ Restrições pro port Rust do 1.0 (achado da medição, registrar já)

`serde_json` com defaults **viola dois contratos nossos**: (a) NaN→`null` **silencioso** (nosso
fail-loud teria de ser explícito, não herdado); (b) **corrompe números grandes CALADO**
(`12345678901234567890123456789.000000000000000001` → `1.2345678901234568e+28`) — quebraria nosso
"TCF ⊃ I-JSON" de inteiros > 2^53, que hoje fazem RT. A feature **`arbitrary_precision`** existe
para isso (doc do Cargo.toml: *"read into a Number and written back... without loss of
precision"*). O port 1.0 NÃO pode usar serde_json defaults às cegas — ou nem usar serde_json no
caminho de dados (nosso wire não é JSON; a necessidade é só nos ADAPTADORES).

## 5. O que muda no lab e nos testes (o "arrumar pra ser justo")

1. **`tests/test_json_flow_parity.py` re-enquadrado**: grupos viram (i) `CONTRATO A` — sanidade da
   lib contra a PRÓPRIA doc (não testa o TCF); (ii) `D_JSON` paridade/lacunas — o critério
   `J-RT-TX ⟹ T-RT` vale só AQUI (14 paridades + 3 lacunas + 7 de raiz, placar inalterado);
   (iii) `FORA_DA_CLASSE` — NaN/Inf/tuple/chave-não-str/surrogate: **não são paridade**; são pinos
   do comportamento do TCF na fronteira dataset⊃JSON, com a doc da lib citada como razão.
2. **Modularização (diretriz do owner)**: adaptadores texto↔dataset são EXEMPLOS (`scripts/`/labs),
   com o modo estrito documentado (`allow_nan=False` + `parse_constant` + `object_pairs_hook`)
   como perfil `strict` de referência. O core nunca importa `json`.
3. **A escala E0-E7 não muda** — as 3 lacunas e a raiz estão DENTRO de D_json (chave `""`, `\n` em
   valor e em chave são `str` válidas; raiz livre é §2) e continuam sendo a superfície inteira.

## 6. Fronteira honesta (reafirmada no novo enquadramento)

- "Paridade JSON" = **cobrir D_json 100%**. Hoje: D_json − {chave `""`, `\n` em valor, chave com
  `\n`, raiz generalizada}. Nunca dizer "qualquer JSON" (P5/union além; `\n` custa L1).
- O que o TCF recusa fora de D_json não é lacuna nem rigidez: é a fronteira onde **a própria doc
  das libs declara perda** — e onde o TCF, por ser dataset-first, pode um dia fazer MAIS que o
  json (representar em vez de perder), nunca menos.
