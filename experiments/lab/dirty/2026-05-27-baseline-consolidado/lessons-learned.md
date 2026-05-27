# lessons-learned — sintese dos 17 labs welded/refuted

Padroes que emergiram apos consolidar `old/welded/` + `old/refuted/`.

## Padroes que sustentaram (10 welded)

### 1. **Pre-pass barato + decisao por features**
Lab origem: `2026-05-22-h-da-11c-features-unificadas`.
Pattern: `analyze_column` retorna `ColumnFeatures` (1 pass O(n)),
e' chamado **uma vez** e consumido por `detect_cadence`,
`detect_min_len`, `obat_shape_preserve`. Eliminou re-scan.

### 2. **Strategy/Protocol em vez de `isinstance`**
Lab origem: discussao apos `2026-05-23-multi-column-scaling`.
Pattern: `TemplatedCheckedSpec`, `TemplatedPaddedSpec` definem
metodos `classify_value/encode_value/decode_value`. Zero
`isinstance` no encoder; novo spec adicionado registrando spec.

### 3. **Byte-canonical preservado via default config**
Lab origem: `2026-05-22-pacote1-weld-canonical`.
Pattern: features novas (PipelineConfig, layers, natures) **default
= comportamento M10 byte-identico**. Testes parametrized em D1-D9
sao linha de defesa.

### 4. **Real-world ANTES de welding**
Lab origem: criterio `confirmada-empirica` (2026-05-21).
Pattern: cada hipotese roda em **Adult Census + TPC-H** alem dos
sinteticos. Sub-exp em real-world e' parte do welding, nao opcional.

### 5. **Outputs visiveis pra auditoria**
Lab origem: feedback owner 2026-05-24.
Pattern: cada dirty lab salva `.tcf`s em `outputs/` (NAO gitignored).
Decoder roda em CI pra garantir RT. Inspecao manual = primeira
defesa.

## Padroes que cairam (7 refutados)

### 1. **Otimizacao perf sem ganho mensuravel**
Labs: `2026-05-20-hcc-perf`, `2026-05-20-obat-perf-phase2`,
`2026-05-22-h-perf-05d`.
Padrao: micro-opt (cache, trigrama, counter incremental) adiciona
complexidade > ganho. **Heuristica**: medir profile real ANTES de
otimizar.

### 2. **Hipotese sintetica que nao generaliza pra real-world**
Lab: `2026-05-21-escape-deduction` (15.7% sint -> 0.13% real-world).
Padrao: dataset construido pra testar hipotese **tende a confirmar
hipotese**. Real-world distri diferente.
Mitigacao: criterio `confirmada-empirica` (CLAUDE.md, 5 perguntas).

### 3. **Naturezas raras com baixo ROI**
Lab: `2026-05-23-naturezas-raras-exploracao` (UUID, hash, base64).
Padrao: tipos raros = poucos casos por dataset; complexidade nao
compensa. Focar em CPF/CNPJ/IP (volumes altos em dados brasileiros).

### 4. **Refinos de heuristica com trade-off ambiguo**
Lab: `2026-05-23-h-da-09c-d-e-refinos-cadence`.
Padrao: refino X melhora dataset A mas regride B. Sem clareza ROI.
Mitigacao: snapshot bytes per-dataset antes de welding.

### 5. **Estruturas pre-existentes subsumidas**
Lab: `2026-05-23-pacote5-t03-enumerated` (dict enumerated).
Padrao: hipotese reinventa o que ja' existe (HCC seq-RLE). Verificar
se canonical ja' captura padrao ANTES de novo sub-exp.

## Anti-patterns observados (e' mitigacao formal)

| Anti-pattern | Lab onde apareceu | Mitigacao welded |
|---|---|---|
| Compressao reportada sem RT verificado | varios pre-2026-05-24 | NUNCA confiar so' em bytes; decode obrigatorio (CLAUDE.md) |
| Sub-exp em dataset enviesado | escape-deduction | Checklist 5-perguntas `confirmada-empirica` |
| `.tcf` em pasta gitignored | varios | outputs visiveis padrao (feedback 2026-05-24) |
| Modificacao direta em `src/tcf/` | tentativa pre-Pacote1 | NUNCA list em CLAUDE.md |
| Mock de db em test integracao | nao aconteceu em TCF | (princpio geral preservado em memoria) |
| `if isinstance(...)` no encoder | tentado em natures | Strategy/Protocol pattern (ADR-0015) |

## Heuristicas pra decidir sub-exp novo

1. **Real-world ja' testou?** Se nao, primeiro adicionar dataset
   real-world ao plano
2. **Hipotese pode ser subsumida?** Grep no codigo + ADRs antes
3. **Ganho min projetado?** Se < 5% real-world, baixo ROI
4. **Complexidade comprovavel?** Toggle adicional, ADR novo,
   doc novo. Vale o esforco?
5. **Anti-pattern conhecido?** Cross-check com tabela acima

## Continuidade

- Hipoteses futuras em [`../notas/roadmap-hipoteses.md`](../notas/roadmap-hipoteses.md)
- Tickets ativos em [`../../../../tickets/`](../../../../tickets/)
- Checkpoint mais recente: [`../notas/checkpoints/2026-05-24-sessao-maxima-natures-multi-delta.md`](../notas/checkpoints/2026-05-24-sessao-maxima-natures-multi-delta.md)
