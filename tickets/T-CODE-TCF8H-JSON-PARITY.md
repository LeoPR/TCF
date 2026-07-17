---
title: T-CODE-TCF8H-JSON-PARITY — o que falta pra fechar "hierarquia" (paridade JSON) + 1 capacidade exclusiva
status: open
priority: P1
created: 2026-07-15
updated: 2026-07-16
gate: capability (paridade JSON), não ≥15%
blocked-by: []
related:
  - tickets/T-CODE-TCF8H-WELD.md
  - tickets/T-API-BOUNDARY-CONTRACTS.md
  - tickets/BUG-SEQRLE-RANGE-EMPTY-B.md
  - experiments/lab/dirty/notas/hierarquia-inventario-hipoteses.md
  - experiments/lab/dirty/notas/tcf-camadas-arquitetura.md
  - docs/adr/0033-hierarchical-codec-weld.md
---

> **PROGRESSO 2026-07-15**: **P1 (presença/ragged) WELDED** (`bcb6405`) — chave opcional faz RT;
> endureceu tipo/null/frame junto (auditoria fechou corrupções silenciosas pré-existentes). Probe
> real-world (receita-cnpj ragged) RT byte-exato em sample; população inteira esbarra em bug
> pré-existente do L1 ([BUG-SEQRLE-RANGE-EMPTY-B](BUG-SEQRLE-RANGE-EMPTY-B.md), R0, separado do P1).
> **Próximo (owner): null (P3)** — o mais barato (`0` já reservado na máscara do P1). Depois P2 tipos, P4 rep-level.
>
> **P3a WELDED 2026-07-15** (`0`=None na máscara; ADR-0033 §Update P3a; lab 2026-07-15-2130 didático→realista→massa,
> null REAL de receita RT byte-exato). **P3b WELDED 2026-07-15** (element-mask, null em elemento; ADR-0033
> §Update P3b; lab 2026-07-15-2230 didático 8/8 + realista + massa 6000/6000; auditoria adversarial fechou
> F1 data-loss pré-existente + F2). **Família null COMPLETA** (campo + elemento; raiz depende de P4/N-raízes).
> **Decisão de mecanismo (Ciclo 4)**: máscara = canônico (O(1)/stream/view; converge Arrow/Parquet/ORC);
> índice-de-substituição = nicho de perfil ([[H-PROFILE-01]]).
>
> **P2 tipos WELDED 2026-07-16** (number tag `n` json / bool tag `b`; insight Python-tipado → tag por-coluna;
> ADR-0033 §Update P2; lab 2026-07-16-0110 didático 10/10 + realista + massa 6000/6000). **ESCALARES JSON
> COMPLETOS** (string/number/bool/null). Falta ESTRUTURA: **P4** (rep-level: array-em-array, N-raízes,
> null-raiz) e **P5** (union: array polimórfico / tipo-misto). Próximo: levantamento do P4.
>
> **REVISÃO P2/P4 2026-07-16 [probatório→opinião]**: P2 válido e endurecido em `268608d`; suíte
> **731 passed, 2 skipped, 2 xfailed**. Resta hardening de metadata: tag desconhecida após size pode
> ser reinterpretada como campo e produzir `[]` silenciosamente (`x:<size>x`), portanto deve falhar
> alto. Para P4, investigar em dois atos: **P4a count recursivo/array-em-array** primeiro; **P4b raiz
> generalizada** depois, pois muda o contrato público. “N-raízes” fica como termo histórico; JSON tem
> uma raiz e arrays preservam ordem. Parecer e matriz de gates:
> [p4-replevel-nroots-levantamento.md](../experiments/lab/dirty/notas/p4-replevel-nroots-levantamento.md).

> **PROGRAMA S0–S7 2026-07-16 [dispositivo→pesquisa]**: capacidade semântica passa a ser fechada antes
> da simplificação de representação. S0–S3 executados em
> [lab próprio](../experiments/lab/dirty/2026-07-16-1708-dataseth-s0-s3-semantica-vinculos/): 20/20 RT,
> 20/20 álgebras de vínculo, 8/8 fail-loud e round-trip canônico byte-idêntico, sem tocar `src/tcf`.
> Tickets: [semântica](T-STUDY-DATASETH-COMPLETE-SEMANTICS.md),
> [vínculos](T-STUDY-HIERARCHY-LINK-ALGEBRA.md) e [execução](T-EXP-DATASETH-S0-S3.md). O resultado é
> probatório sintético; header, busca no corpo e forma física ficam para S4–S7 antes de novo weld.

> **REVISÃO DE ESCOPO 2026-07-15 — opinião registrada; decisão pendente do owner.** P3 não é um
> único incremento mecânico. **P3a** = null em CAMPO de objeto (`{x:null}`), inclusive quando o campo
> não-nulo é escalar/objeto/array: reutiliza diretamente `0` na definition mask e não consome corpo nem
> descendentes. **P3b** = null em ELEMENTO de array (`["a",null,"b"]` ou `[{},null,{}]`): precisa de
> máscara alinhada aos elementos, pois a máscara P1 está alinhada às instâncias do campo. **Null na
> raiz** fica junto da decisão P4/N-raízes. Recomendação probatória: P3a → P3b, com gates separados;
> não declarar “família null fechada” após P3a. NaN/±Infinity ficam fora (não são JSON RFC 8259 e
> dependem da camada de tipos P2). Fonte do raciocínio e ordem de retomada: checkpoint
> [2026-07-15-revisao-null-pos-p1](../experiments/lab/dirty/notas/checkpoints/2026-07-15-revisao-null-pos-p1.md).

> **CRITÉRIO EXECUTÁVEL + ESCALA DE ROI 2026-07-17 [dispositivo→registro]**: owner fixou o critério
> como **equivalência de FLUXO** — *"dataset→encode→json→transmite→recebe→json→decode→dataset; basta
> o tcf ter comportamento similar"*. Formalizado e MEDIDO: **∀D: J-RT-TX(D) ⟹ T-RT(D)** (com a etapa
> TRANSMITE medida em **bytes UTF-8**, não no str em memória — sem ela o lone surrogate falsearia a
> paridade). Lab [2026-07-17-0140](../experiments/lab/dirty/2026-07-17-0140-paridade-fluxo-json-vs-tcf/);
> pinos em `tests/test_json_flow_parity.py` (24 passed + **3 `xfail(strict)`** — lacuna não fecha em
> silêncio: implementar faz XPASS e obriga a promover o caso).
>
> **PLACAR: PARIDADE=14 · LACUNA=3 · LACUNA-RAIZ=7 (P4b) · TCF-ESTRITO=2 · AMBOS-RECUSAM=7.**
> A superfície inteira de implementação são **3 lacunas de dataset** (chave `""` · `\n` em valor ·
> chave com `\n`) **+ o eixo raiz**. Bônus medido: **TCF ⊃ I-JSON** em inteiros > 2^53 (RFC 7493 §2.2
> os proíbe; nós fazemos RT).
>
> **ESCALA (ROI)** → [escala-implementacao-paridade-json.md](../experiments/lab/dirty/notas/escala-implementacao-paridade-json.md):
> **E0 critério ✅ feito** → **E1 tipar 3 erros crus** (baixo, não toca wire) → **E3 canal SideOutputs
> no `.8H`** (destrava o *warning* + profiler) → **E2 chave `""`** (1 lacuna; "nome vazio" hoje é
> sentinela de corrupção → estudo-primeiro) → **E5 P4b raiz** (**7 lacunas de uma vez** = maior ROI)
> → avaliar E4 (chave com `\n`) → **E6 `\n` em valor SEGURAR** (toca o **L1**: re-pina D1-D9/D17a/
> real-world; é o T-FMT-ESCAPE-COMBINATORIAL-STUDY) → E7 além-do-json (formato/versão).
>
> **"É problema do Python ou do JSON?"** (pergunta do owner) — provado por **compilação** (`rustc
> 1.82`): chave int+str no mesmo mapa → **erro E0308**; lone surrogate → **erro de compilação**
> (`char::from_u32(0xD800)`=`None`). **2 dos 5 defeitos são inexprimíveis em Rust** → somem de graça
> no port do 1.0. NaN é físico (IEEE 754: `f64::NAN == f64::NAN` é `false`; o rustc avisa) → só se
> resolve REPRESENTANDO (E7), nunca tolerando.

# T-CODE-TCF8H-JSON-PARITY — fechar "hierarquia" com critério REALISTA (JSON) + algo além

**[dispositivo→roadmap]** Owner (2026-07-15): *"veja o que falta pra fecharmos bem a questão de
'hierarquia' (aqui falando de forma ampla — estruturas com ligações diversas). Pra um critério mais
realista, pode se basear na capacidade de JSON que as pessoas já usam — isso dá fundamento. Mas é
interessante dar uma capacidade extra exclusiva pro TCF, algo mais avançado."*

Critério de fechamento = **RT lossless de qualquer JSON que as pessoas transmitem** (fundamento
realista, não sintético). O weld atual (ADR-0033) cobre a ESPINHA; faltam os construtos JSON abaixo.

## Onde estamos vs a capacidade do JSON (RFC 8259) — o gap concreto

| construto JSON (o que as pessoas usam) | `.8H` hoje | falta |
|---|---|---|
| `{}` objeto (1:1), aninhado | ✅ coberto | — |
| `[]` array de objetos/escalares (1:N) + `#count` | ✅ coberto | — |
| string (incl. unicode, separadores) | ✅ coberto | — |
| nome de chave c/ char do meta | ✅ **escaping welded** (`40a7e10`) | **congelar** contrato |
| aninhamento arbitrário (contenção) | ✅ classe coberta | — |
| **chave OPCIONAL / objeto ragged** | ✅ **WELDED** (P1, 2026-07-15) | — (`nome?:msize`, máscara 3-estados; ADR-0033 §Update P1) |
| **number (int/float) preservado** | ✅ **WELDED** (P2, 2026-07-16) | — (tag `n`, json.dumps/loads; ADR-0033 §Update P2) |
| **`true`/`false`** | ✅ **WELDED** (P2, 2026-07-16) | — (tag `b`, true/false) |
| **`null` em campo** (≠ ausente ≠ `"null"`) | ✅ **WELDED** (P3a, 2026-07-15) | — (máscara `0`=None; ADR-0033 §Update P3a) |
| **`null` em elemento de array** | ✅ **WELDED** (P3b, 2026-07-15) | — (element-mask 2-estados; ADR-0033 §Update P3b) |
| **`null` na raiz** | ❌ fora do contrato `list[dict]` | decisão junto de **P4/N-raízes** |
| **array-em-array** (profundidade arbitrária) | ✅ **WELDED** (P4a, 2026-07-16) | — (count recursivo por nível; ADR-0033 §Update P4a) |
| **array no topo / raiz generalizada** | ❌ fail-loud | **P4b — contrato de raiz** (ato separado, muda API) |
| **array polimórfico** (elementos de schema variável) | ❌ fail-loud | P5 — union/def-level (a fronteira mais afiada) |
| `\n` em valor | ❌ fail-loud (core), **`ValueError` CRU** (medido 2026-07-17) | **congelar** contrato (boundary) + re-tipar |
| **chave vazia `{"": "x"}`** | ❌ `HierarchicalError: nome de campo vazio` (medido 2026-07-17) | **lacuna de CAPACIDADE**: é JSON válido e comum; json faz RT-OK. A mais barata das 4 lacunas A ([perfil-json-like](../experiments/lab/dirty/notas/perfil-json-like-condicoes-parametro.md) §1) |
| **chave contendo `\n`** | ❌ fail-loud tipado (medido 2026-07-17) | implementar OU declarar fronteira (json faz RT-OK) |
| ✅ paridade JÁ medida (2026-07-17) | `\t` · `\x00` em valor · int gigante `10**30` · `-0.0` · `0.1+0.2` (precisão) — **idênticos ao json** | — |
| ⭐ TCF **mais seguro** que o json (medido 2026-07-17) | `NaN`/`Infinity` (json emite — **inválido RFC 8259**, `allow_nan` default; NaN quebra RT) · `tuple`→`list` (json perde tipo) · chave não-str (json **emite duplicata**) · lone surrogate (json faz RT mas não é UTF-8 transmissível) — `.8H` fail-loud nos 4 | NÃO afrouxar: estrito é feature. Evoluir por REPRESENTAÇÃO ([[H-HIER-SCALAR-01]]), não por tolerância |
| **ordem de chaves por-registro em ragged** | ⚠️ semântica preservada; ORDEM vira a do schema (chave que estreia tarde volta ao fim) — achado 2026-07-17 da suíte de controle, pinado em `test_hierarchical_control_synthetics.py` | decisão de contrato (S6/P4b): schema-order canônica OU por-registro; contrato S0 preserva por-registro ([T-API-BOUNDARY-CONTRACTS](T-API-BOUNDARY-CONTRACTS.md)) |

Fonte da taxonomia: [hierarquia-inventario-hipoteses.md](../experiments/lab/dirty/notas/hierarquia-inventario-hipoteses.md)
(presença→repetição→normalização, SETTLED). Tipos = camada ortogonal (item 11 do inventário).

## Ordem proposta (incrementos funcionais, um de cada vez — "soldar em etapas")

Gate de cada um: RT-exato + non-regressão flat byte-idêntica + aprovação `src/tcf` + fuzz/probes
adversariais (a lição do escape: testar nome/valor/borda, não só o caminho feliz).

1. ~~**P1 · Presença/ragged** (chave opcional)~~ **✅ WELDED 2026-07-15** — `nome?:msize`, máscara
   3-estados; endureceu tipo/null/frame junto (auditoria); probe real-world amostral fechado; suíte
   vigente 685 passed, 2 skipped, 1 xfailed (bug L1 separado e pinado).
2. ~~**P3 · null (campo + elemento)**~~ **✅ WELDED 2026-07-15** — P3a usa estado `0` na máscara
   de campo; P3b usa element-mask alinhada aos elementos. Índices de substituição permanecem hipótese
   física futura, não representação semântica canônica. Fonte da decisão e do histórico comparativo:
   [substituicao-indices-especiais-plano.md](../experiments/lab/dirty/notas/substituicao-indices-especiais-plano.md).
3. ~~**P2 · Tipos** (number/bool preservados)~~ **✅ WELDED 2026-07-16** — tags por-coluna `n`/`b`,
   identidade Python-tipado, string default; decode tipado endurecido em `268608d`. **Hardening de tag
   desconhecida FECHADO** (revisão do owner): `stag()` rejeita char não-n/b/delimitador após size
   (`x:<size>x` era `[]` calado → agora `HierarchicalError`); teste `test_p2_tag_desconhecida_fail_loud`.
4. ~~**P4a · Repetição estrutural** (array-em-array)~~ **✅ WELDED 2026-07-16** — count recursivo por
   nível (gramática `#:c?:e[...]` recursiva, inspecionada/aprovada pelo owner); estudo lab
   2026-07-16-0213 (gate 12/12 + fuzz 4000) + weld com suíte 748; null-entre-arrays = P3b∘P4a firmado.
   Preocupação do owner ("colunas com buracos"/reuso entre níveis) → H-REPLEVEL-FLAT-VS-PORNIVEL-01 (`.9`).
5. **P4b · Raiz generalizada** (array no topo, objeto/escalar/null na raiz) — contrato público e
   envelope/discriminador explícito; preservar ordem e tipo-raiz exatamente.
   **LEVANTAMENTO 2026-07-16** → [notas/p4b-levantamento.md](../experiments/lab/dirty/notas/p4b-levantamento.md).
   Medido: **14/14 formas de raiz fail-loud hoje** (0 wire, 0 corrupção silenciosa — funcionalidade
   ausente e declarada, não dívida escondida). **Ambiguidade byte-confirmada**: `encode([{"a":"1"}])`
   e a raiz-objeto `{"a":"1"}` embrulhada dão wire **idêntico** (`#TCF.8Ha\n\1\n`) → raiz sintética
   sem discriminador é **provadamente lossy**. Achado do levantamento: o gate de 8 formas **decompõe
   em 3 problemas distintos** — (A) discriminação de raiz, (B) **contagem irrepresentável** (`[]`,
   `[{}]`, `[{},{}]`: o count vem de `len(1ª coluna)`, sem colunas não há onde contar → é
   [T-FMT-OMIT-OR-DECLARE](T-FMT-OMIT-OR-DECLARE.md)/registro-'0', **não** se resolve com `root_kind`),
   (C) raiz não-objeto. Recomendação: **P4b = A + C**; B fica no ticket de vazios.
   **Nada decidido** — 5 decisões abertas do owner em §5 do levantamento (escopo no `.8`; separar B;
   discriminador (1) char sempre presente vs (2) só quando ≠ dataset; contrato de API; terminologia).
6. **P5 · Array polimórfico** (union) — a fronteira; pode ficar por último ou virar fail-loud honesto.
7. **Congelar contratos de borda** — `\n`-em-valor + gramática-de-nome (escaping) →
   [T-API-BOUNDARY-CONTRACTS](T-API-BOUNDARY-CONTRACTS.md), antes do freeze pré-1.0.

Com P1, P3a/P3b, P2, P4 + contratos, o `.8H` se aproxima da paridade JSON de transmissão real. P5
continua sendo a fronteira explícita; portanto o fechamento deve reportar a fração in-class, não usar
“qualquer JSON” enquanto arrays polimórficos permanecerem fora.

## A capacidade EXCLUSIVA (além do JSON) — o "algo mais avançado"

**H-HIER-SHARED-REF-01 · normalização / referência compartilhada no HEADER (grafo, não árvore).**
JSON só faz ÁRVORE: um filho compartilhado por dois pais é **duplicado** (blow-up) ou exige `$ref`/
`$id` manual (não-padrão, JSON-Schema). O TCF pode expressar a **junção/FK no HEADER** (camada L2) —
o filho compartilhado é armazenado **UMA vez** e referenciado → representa **N:N / snowflake / grafo
SEM duplicação**. É a super-hierarquia ([H-HIER-MULTITABELA-01](../experiments/lab/dirty/notas/tcf-camadas-arquitetura.md))
e responde ao "ligações diversas" recorrente do owner. Hoje N:N é **inexpressável** no contrato
`list[dict]` (a auditoria 2026-07-15 corrigiu: não é "fail-loud", é fora do modelo) — esta capacidade
é o que o abre. Bônus que só o TCF tem: **explicabilidade comprimida** (grupos `*N|` visíveis) e
**lazy/queryable nested** (o `view()` estendido à árvore — ler estrutura sem materializar).

`aberta`, confiança: Baixa (design). É a diferenciação, não a paridade — vem DEPOIS de P1–P4
(primeiro alcançar o JSON, depois passar dele).

## Critério de aceite

- [x] P1 presença, P3 null e P2 tipos weldados incrementalmente com gates próprios.
- [ ] P4a estrutura e P4b raiz decididos/weldados separadamente, com non-regressão e adversarial.
- [ ] Metadata P2 rejeita tag desconhecida após size sem reinterpretar como novo campo.
- [ ] Suíte de paridade: RT de um corpus de JSONs reais de transmissão (API, logs, catálogos) —
  fração in-class vs fronteira reportada (fundamentar no JSON que as pessoas usam).
- [ ] Contratos de borda (`\n`, nome) congelados antes do freeze pré-1.0.
- [ ] Capacidade exclusiva (shared-ref/grafo) prototipada em lab e decidida (weld ou research-track).
