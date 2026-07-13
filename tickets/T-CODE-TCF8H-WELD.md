---
title: T-CODE-TCF8H-WELD — weld do codec hierárquico #TCF.8H no src/tcf (feature do .8)
status: open
priority: P1
created: 2026-07-13
updated: 2026-07-13
gate: capability
blocked-by: []
related:
  - tickets/T-STUDY-HIERARCHICAL-TCF.md
  - tickets/T-FMT-TCF8H-HEADER.md
  - docs/adr/0031-hierarchical-discriminator-H.md
  - experiments/lab/clean/EXP-015-tcf-hierarquico-csv-json/
  - tests/test_real_world_snapshots.py
  - src/tcf/decoder.py
---

# T-CODE-TCF8H-WELD — promover o codec hierárquico para o core

**[dispositivo→exec]** Decisão do owner (2026-07-13, reescopo `.8` = feature-complete "1.0"): a
**hierarquia / JSON aninhado (`#TCF.8H`)** entra no `.8` como a expansão de capacidade do 1.0.
Este ticket é o **weld** do codec — promover o protótipo validado para `src/tcf`, sob aprovação
explícita e o gate de CAPACIDADE (não o gate de compressão).

## Ponto de partida (o que já está pronto)

- **Char `H` reservado** no discriminador `#TCF.8` (ADR-0031, `accepted`): `H` = multi-col hierárquico,
  especialização de `M`, **sem-espaço** (`#TCF.8H<meta>`), dispatch O(1) no decode.
- **Regras de header decididas** (T-FMT-TCF8H-HEADER, `closed-decided`): `M` implícito, **omit-closes**
  (o `\n` do header auto-fecha grupos abertos → dropa `}`/`]` final, RT-exato, −1B), última-folha-sem-size,
  colchetes `{}`=objeto / `[]`=array, cardinalidade/multiplicidade **deduzidas** (não escritas).
- **Codec protótipo validado**: `experiments/lab/clean/EXP-015-tcf-hierarquico-csv-json/codec.py`
  (self-contained, **não toca `src/`**). Round-trip **exato** em `JSON→TCF.8H→JSON` (S4 66B, S6 153B) e
  `CSV→TCF→CSV` (C1 107B). Guarda-chuva de feasibility: T-STUDY-HIERARCHICAL-TCF (P1–P9, `confirmada-conceitual`).
- **Produção hoje**: `src/tcf/decoder.py` só **reserva + fail-loud** o `H` (não decoda). Zero codec no core.

## Gate de CAPACIDADE (não é ≥15% de compressão)

Hierarquia **não** é otimização de bytes — é **representar dado que a tabela plana não representa**
(1:N, objeto-em-objeto, arrays). Logo o gate ≥15%/2-reais (que rege weld de nature/otimização) **não se
aplica**. O gate de aceite deste weld é:

1. **RT-exato em JSON aninhado REAL** (não só S4/S6 sintéticos): ≥3 documentos aninhados reais/realistas
   (ex.: resposta de API pessoa⊃endereço⊃geo + telefones[]; pedido⊃itens[]; org⊃deptos[]⊃membros[]).
   `decode(encode(json)) == json` exato, incluindo ordem, tipos preservados como string, e vazios.
2. **Non-regressão do flat**: `test_core_rt` + `test_regression_v1_baseline` + `test_real_world_snapshots`
   **inalterados** (D1-D9=1523B, D17a=300B, real-world=89616B). O caminho `#TCF.8M`/single/órfão não muda
   **1 byte**. Hierarquia é aditiva (dispatch por `H`).
3. **Aprovação explícita de `src/tcf`** (invariante do projeto) para cada arquivo tocado.

## Plano (fases)

- [ ] **W0 — decisão de API**: como o usuário pede hierarquia? `encode(nested_dict)` auto-detecta
  aninhamento e emite `#TCF.8H`? ou knob explícito (`encode(x, nested=True)`)? Definir a fronteira
  (cruza T-API-BOUNDARY-CONTRACTS). Default: **auto-detect** (dict/list aninhados → `H`; plano → `M`).
- [ ] **W1 — abrir ZERO no core** (regra dirty-lab: extrai a IDEIA, não copia `codec.py`): parser do
  meta-árvore (`{}`/`[]`, omit-closes, última-sem-size) + encoder/decoder que reusam OBAT/HCC por folha.
  Alinhar ao **sem-espaço** do ADR-0031 (o protótipo usa espaço — refinamento no weld).
- [ ] **W2 — dispatch**: `decoder.py` troca o fail-loud de `H` por rota real (O(1) por char); encoder
  roteia aninhado→`H`. `M`/single/órfão intactos.
- [ ] **W3 — gate de capacidade**: os 3 critérios acima verdes; fixtures de JSON aninhado real committadas
  (datasets/samples/nested/ ou similar); RT + non-regressão pinados em `tests/test_hierarchical_rt.py`.
- [ ] **W4 — tipos & bordas**: cruzar com T-API-BOUNDARY-CONTRACTS — como `#TCF.8H` trata null vs vazio,
  tipos escalares (number/bool preservados como string? ou `:tipo` no colchete, C-hybrid do header ticket?),
  array-in-array / objeto-em-array-element / N-raízes (o protótipo dá `NotImplementedError` nesses — decidir
  se entram no `.8` ou ficam fail-loud declarado). ADR do formato final se a gramática mudar.
- [ ] **W5 — docs**: README (a hierarquia fecha a maior lacuna vs JSON), reference do formato, ADR de weld.

## Riscos

- **Codec novo no core** = maior risco desde os welds de formato. Mitigar: aditivo (dispatch por `H`),
  flat 100% intacto, gate de non-regressão duro.
- **Frontier não-suportada** (array-in-array, N-raízes, link posicional / Dremel rep-level): decidir
  escopo do `.8` — suportar o comum (objeto⊃objeto, objeto⊃array-de-escalares/objetos) e **fail-loud
  declarado** no resto, ou puxar tudo. Owner decide em W4.
- **Tipos**: se o `.8` congelar "tudo string" (ver T-API-BOUNDARY-CONTRACTS), a hierarquia herda; se
  entrar `:tipo`, é mais superfície. Alinhar as duas decisões.

## Critério de aceite

- [ ] Os 3 critérios do gate de capacidade verdes, com fixtures reais committadas e RT/non-regressão pinados.
- [ ] `src/tcf` aprovado arquivo-a-arquivo pelo owner; flat byte-idêntico.
- [ ] Fronteira de API (W0) e de tipos/bordas (W4) decididas e documentadas (cruzam T-API-BOUNDARY-CONTRACTS).
- [ ] ADR de weld (formato final do meta-árvore) se a gramática divergir do T-FMT-TCF8H-HEADER decidido.
