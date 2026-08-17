# 2026-08-17-0600 — os limites do `.8H`: profundidade, largura, bordas do meta

## A pergunta

O owner pediu: pesquisar estruturas complexas de hierarquia, ver **limites**, registrar.
A pesquisa interna mostrou o que já temos (chave repetida, `int>2^53`, array-em-array) e
o buraco: **ninguém tinha medido o limite de profundidade** — nem conferido se a quebra é
fail-loud tipada ou `RecursionError` cru.

## O resultado central

**O `.8H` já tem guarda tipada em 128 níveis** — e ela não estava documentada em nenhum
doc vivo.

| escada | último OK | quebra em | como |
|---|--:|--:|---|
| objeto (`{"a":{"a":…}}`) | 129 | 130 | `HierarchicalError: profundidade estrutural excede o limite de 128 níveis (objetos+arrays)` |
| array (`[[["x"]]]` num campo) | 128 | 129 | idem |
| largura (chaves no mesmo objeto) | **16 384 OK** | — | sem teto encontrado |

- A guarda é `_MAX_DEPTH = 128` ([`hierarchical.py:305`](../../../../../../src/tcf/hierarchical.py)),
  aplicada em **três** pontos: encode (`:266`), parse de forma (`:318`) e decode (`:738`).
  Nunca chega ao `RecursionError` (o `sys.recursionlimit` da máquina era 1000).
- A diferença de 1 degrau entre as escadas (129 vs 128) é a raiz: na escada de objeto o
  dataset embrulha em `[v, v]`, e a contagem começa no caminho do campo — o registro aqui
  é o **fato medido**, não uma interpretação.
- Largura não tem guarda própria: 16 384 chaves passam com round-trip. O header cresce
  linear (uma entrada por chave), sem teto além da memória.

## A régua externa (verificada 2026-08-17)

O texto JSON permite profundidade arbitrária; **quem limita é o parser**
(RFC 8259 §9: *"An implementation may set limits on the maximum depth of nesting"*).

| parser/formato | limite default | fonte |
|---|--:|---|
| **TCF `.8H`** | **128** (objetos+arrays, tipado) | medido aqui |
| serde_json (Rust) | 128 (`unbounded_depth` desliga) | serde-rs/json #334 |
| MongoDB / BSON | 100 níveis | MongoDB Limits and Thresholds |
| Jackson (Java) | 1000 (`StreamReadConstraints`, 2.15+) | jackson-core #637 |
| protobuf-go | 10 000 | protobuf-go v1.28.0 release |
| Python `json` | recursão (~`sys.recursionlimit`) | comportamento conhecido |

O nosso 128 coincide com o serde_json e fica acima do MongoDB. **Posição confortável** —
e agora documentada (edição no `json-equivalence.md`, neste commit).

## As bordas do meta (casos mínimos, todos RT OK)

| caso | header | o que prova |
|---|---|---|
| `{"a{b": …}` | `#TCF.8Ha\{b` | `{` em nome de campo é **escapado** |
| `{"a#b": …}` | `#TCF.8Ha\#b` | `#` idem |
| `{"a[b": …}` | `#TCF.8Ha\[b` | `[` idem |
| `{"a?b": …}` | `#TCF.8Ha\?b` | `?` idem |
| `{"endereço🏠": …}` | `#TCF.8Hendereço🏠` | unicode multi-byte passa cru |
| `{"b":…,"a":…}` | `#TCF.8Hb:6,a` | ordem = **schema** (1ª aparição), como o `json-equivalence` afirma |
| `{"a":[{"b":…}]}` | `#TCF.8Ha#:6[b` | objeto-em-array-em-objeto: 3 formas alternadas num header só |
| `2^53+1` | `#TCF.8Ha:24n` | ⊃ I-JSON, caso mínimo do que o §N2 já registrava |

## Decode adversarial: campo duplicado forjado

A chave repetida no objeto Python **não existe** (dict deduplica) — o levantamento
[`json-chave-repetida`](../../../notas/2026-07/json-chave-repetida-levantamento.md) cobriu
o *texto* JSON. Faltava o **wire forjado**:

```
decode('#TCF.8Ha:2,a\nx\ny\n')      -> HierarchicalError: campo duplicado 'a' no header
decode('#TCF.8Ha:2,a:2,b\n...')     -> idem
```

**Fail-loud nos dois.** O `.8H` está na família "erro" da RFC 8259 §4 — coerente com a
decisão S0 do levantamento (fail-loud, não last-wins calado).

## Conexões

- Registro consolidado (literatura + o que já tínhamos + o que falta):
  [`notas/2026-08/2026-08-17-0630-limites-de-hierarquia-registro.md`](../../../notas/2026-08/2026-08-17-0630-limites-de-hierarquia-registro.md)
- Gramática do header em casos mínimos: [`0500`](../2026-08-17-0500-header-do-H-sintetico/)
- Chave repetida (2026-07): [`json-chave-repetida-levantamento`](../../../notas/2026-07/json-chave-repetida-levantamento.md)
- Fronteira JSON: [`docs/reference/json-equivalence.md`](../../../../../../docs/reference/json-equivalence.md)
