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
  - experiments/lab/dirty/2026-07-13-dataseth-json-bridge/
  - experiments/lab/dirty/notas/dataseth-hierarquia-completa-plano.md
  - tests/test_real_world_snapshots.py
  - src/tcf/decoder.py
---

# T-CODE-TCF8H-WELD — promover o codec hierárquico para o core

**[dispositivo→exec]** Decisão do owner (2026-07-13, reescopo `.8` = feature-complete "1.0"): a
**hierarquia / DatasetH (`#TCF.8H`)** entra no `.8` como a expansão de capacidade do 1.0.
Este ticket é o **weld** do codec — promover o protótipo validado para `src/tcf`, sob aprovação
explícita e o gate de CAPACIDADE (não o gate de compressão).

JSON é a primeira fonte do caminho de pesquisa, não a API do core. O codec deve receber o DatasetH
definido no estudo e não deve criar `encode_json` nem importar parser JSON em `src/tcf`.

## Ponto de partida (o que já está pronto)

- **Char `H` reservado** no discriminador `#TCF.8` (ADR-0031, `accepted`): `H` = multi-col hierárquico,
  especialização de `M`, **sem-espaço** (`#TCF.8H<meta>`), dispatch O(1) no decode.
- **Regras de header decididas** (T-FMT-TCF8H-HEADER, `closed-decided`): `M` implícito, **omit-closes**
  (o `\n` do header auto-fecha grupos abertos → dropa `}`/`]` final, RT-exato, −1B), última-folha-sem-size,
  colchetes `{}`=objeto / `[]`=array, cardinalidade/multiplicidade **deduzidas** (não escritas).
- **Codec protótipo limitado**: `experiments/lab/clean/EXP-015-tcf-hierarquico-csv-json/codec.py`
  (self-contained, **não toca `src/`**) tem RT exato apenas nas amostras all-string S4/S6 e C1.
  Ele prova a notação inicial, não o contrato de um JSON total nem a independência da fonte. O guarda-chuva
  de pesquisa é T-STUDY-HIERARCHICAL-TCF (P1–P9, `confirmada-conceitual`).
- **Produção hoje**: `src/tcf/decoder.py` só **reserva + fail-loud** o `H` (não decoda). Zero codec no core.

## Gate de CAPACIDADE (não é ≥15% de compressão)

Hierarquia **não** é otimização de bytes — é **representar dado que a tabela plana não representa**
(1:N, objeto-em-objeto, arrays). Logo o gate ≥15%/2-reais (que rege weld de nature/otimização) **não se
aplica**. O gate de aceite deste weld é:

1. **RT-exato do DatasetH**: o gate do core é `decode(encode(dataset_h)) == dataset_h`, sem importar JSON
  nem depender da origem. O primeiro adaptador de prova é JSON: `json -> DatasetH -> TCF.H -> DatasetH -> json`,
  com ≥3 documentos aninhados reais/realistas (pessoa⊃endereço⊃geo + telefones[]; pedido⊃itens[];
  org⊃deptos[]⊃membros[]). A comparação deve preservar a semântica definida pelo DatasetH, incluindo
  ordem, tipos, presença, `null`, vazios e repetição.
2. **Non-regressão do flat**: `test_core_rt` + `test_regression_v1_baseline` + `test_real_world_snapshots`
   **inalterados** (D1-D9=1523B, D17a=300B, real-world=89616B). O caminho `#TCF.8M`/single/órfão não muda
   **1 byte**. Hierarquia é aditiva (dispatch por `H`).
3. **Aprovação explícita de `src/tcf`** (invariante do projeto) para cada arquivo tocado.

## Plano (fases)

- [ ] **W0 — contrato do DatasetH**: definir a estrutura intermediária e o significado de folhas,
  objetos, arrays, tipos, presença, `null`, ordem, repetição e raízes. Não criar `encode_json` e não
  auto-detectar a origem; `encode` continua sendo a única entrada do core.
- [ ] **W1 — pesquisa de adaptadores**: implementar fora do core o caminho `JSON -> DatasetH` com stdlib
  `json` e comparar `json_normalize`, Arrow nested e `ijson`. Construir também um DatasetH sem JSON para
  provar que a hierarquia não está acoplada à fonte.
- [ ] **W2 — codec externo** (regra dirty-lab: extrai a ideia, não copia `codec.py`): implementar
  `DatasetH -> TCF.H -> DatasetH`, incluindo framing de folhas e side-channel de topologia. Alinhar ao
  sem-espaço do ADR-0031; o protótipo usa espaço.
- [ ] **W3 — dispatch no core**: somente após W0-W2, `decoder.py` troca o fail-loud de `H` por rota real
  e `encode` passa a aceitar a estrutura hierárquica definida. `M`/single/órfão permanecem intactos.
- [ ] **W4 — gate de capacidade**: RT do DatasetH, adaptador JSON em ida e volta, segunda origem,
  determinismo, malformed input, limites e não regressão flat. Fixtures ficam fora de `src/tcf`.
- [ ] **W5 — docs e weld**: README, referência do formato, ADR de weld e aprovação arquivo-a-arquivo de
  `src/tcf`; o codec só entra no core depois do gate.

## Riscos

- **Codec novo no core** = maior risco desde os welds de formato. Mitigar: aditivo (dispatch por `H`),
  flat 100% intacto, gate de non-regressão duro.
- **Topologia e bordas** (array-in-array, N-raízes, link posicional / Dremel rep-level): pertencem ao
  contrato do DatasetH e ao codec, não ao adaptador JSON isoladamente. Devem ser classificadas em W0-W2;
  o que ficar fora do domínio entra como fail-loud explícito.
- **Tipos**: o H não herda a coerção do flat. A representação tipada, `null` e presença devem ser
  definidos no DatasetH antes de escolher tags ou deduções no header.

## Critério de aceite

- [ ] DatasetH definido e independente de JSON; adaptador JSON e segunda origem comprovam o caminho de entrada.
- [ ] `decode(encode(dataset_h)) == dataset_h`, com fixtures reais committadas e RT/non-regressão pinados.
- [ ] `src/tcf` aprovado arquivo-a-arquivo pelo owner; flat byte-idêntico.
- [ ] Fronteira de API (W0) e de tipos/bordas (W0-W2) decididas e documentadas (cruzam T-API-BOUNDARY-CONTRACTS).
- [ ] ADR de weld (formato final do meta-árvore) se a gramática divergir do T-FMT-TCF8H-HEADER decidido.
