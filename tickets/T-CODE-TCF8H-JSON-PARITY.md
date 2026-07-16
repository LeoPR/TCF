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

> **REVISÃO DE ESCOPO 2026-07-15 — opinião registrada; decisão pendente do owner.** P3 não é um
> único incremento mecânico. **P3a** = null em CAMPO de objeto (`{x:null}`), inclusive quando o campo
> não-nulo é escalar/objeto/array: reutiliza diretamente `0` na definition mask e não consome corpo nem
> descendentes. **P3b** = null em ELEMENTO de array (`["a",null,"b"]` ou `[{},null,{}]`): precisa de
> máscara alinhada aos elementos, pois a máscara P1 está alinhada às instâncias do campo. **Null na
> raiz** fica junto da decisão P4/N-raízes. Recomendação probatória: P3a → P3b, com gates separados;
> não declarar “família null fechada” após P3a. NaN/±Infinity ficam fora (não são JSON RFC 8259 e
> dependem da camada de tipos P2). Fonte do raciocínio e ordem de retomada: checkpoint
> [2026-07-15-revisao-null-pos-p1](../experiments/lab/dirty/notas/checkpoints/2026-07-15-revisao-null-pos-p1.md).

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
| **array-em-array / array no topo / raiz generalizada** | ❌ fail-loud | **P4a estrutura + P4b contrato de raiz** (caracterizados, não implementados) |
| **array polimórfico** (elementos de schema variável) | ❌ fail-loud | P5 — union/def-level (a fronteira mais afiada) |
| `\n` em valor | ❌ fail-loud (core) | **congelar** contrato (boundary) |

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
4. **P4a · Repetição estrutural** (array-em-array) — count recursivo como representação hierárquica
   da informação posicional; fechar gramática e adversarial em lab próprio.
5. **P4b · Raiz generalizada** (array no topo, objeto/escalar/null na raiz) — contrato público e
   envelope/discriminador explícito; preservar ordem e tipo-raiz exatamente.
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
