# Fluxo de experimentos TCF v0.4 — passos pequenos com critério de pivot

Crítica autoinflingida ao fluxo inicial (EXP-003..006) e refinamento
em passos isolados, cada um com critério de decisão e pivot.

## Por que o fluxo inicial era ruim

| # | Problema |
|---|----------|
| 1 | EXP-003 misturava 3 hipóteses ortogonais (T1, T2, T3) num lab só |
| 2 | Faltava calibração baseline (CSV+gzip puro) — sem referência |
| 3 | HP-T2 depende de chunks implementados — bloqueada |
| 4 | EXP-004 (stratified STATS) é escopo LLM — fora do bloco |
| 5 | Sem critério de pivot: o que fazer se resultado for inesperado? |

## Passos refinados

### PASSO 1 — EXP-003a — Calibração CSV+gzip

**Hipótese**: nenhuma direta. Estabelece **referência** de quanto
gzip/brotli/zstd ganham sozinhos sobre CSV em datasets variados.

**Datasets**: 5 diferentes (TPC-H supplier, Adult Census, e 3 outros).

**Saída**: tabela `dataset × compressor → bytes finais e ratio`.

**Custo**: ~30min código + dataset access.

**Bloqueia**: tudo. Sem referência, nada se interpreta.

### PASSO 2 — EXP-003b — HP-T1 (decisor principal)

**Hipótese**: TCF L0+sort+gzip eh competitivo com TCF smart+gzip.

**Compara**: naive+gzip vs compact+gzip vs smart+gzip nos mesmos
5 datasets do passo 1.

**Decisão em cascata**:

| Resultado | Caminho |
|-----------|---------|
| smart >> compact (>15% adicional) | caminho A: implementar E/H/I no Sprint 1+2 |
| smart ≈ compact (±5%) | caminho B: compact é o default; E/H/I viram opt-in v0.4.x |
| smart < compact | revisar — algo está errado nas propostas |

**Critério de pivot**: se cluster de datasets der resultado misto,
investigar se há classes de dados onde caminho A vence e outras
onde B basta — pode levar a default híbrido.

### PASSO 3 — EXP-005 + EXP-006 (rodam em paralelo, independente do passo 2)

#### EXP-005 — HP-B1 (type-preserving)

**Hipótese**: roundtrip exato preserva int/float/bool/None.

**Custo**: pequeno. Não depende do resultado do passo 2.

**Decide**: se mexer no decoder atual ou criar opt-in.

#### EXP-006 — HP-F1 (auto-detect sortedness)

**Hipótese**: heurística `count_runs(sorted) - count_runs(unsorted)`
escolhe coluna correta em datasets variados.

**Custo**: médio. Independente.

**Decide**: se default `sort_by="auto"` é seguro.

### PASSO 4 — EXP-007 — HP-T2 (chunks × batch × gzip)

**Bloqueado até**: implementação do M-chunks-v04 Bloco 1 (Plan +
chunk format + encoder/decoder chunked sincrono).

**Hipótese**: chunks pequenos prejudicam compressao do canal;
existe sweet spot ~32-64KB.

**Custo**: depende de quanto demora implementar chunks.

### PASSO 5 — EXP-008 — HP-T3 (síntese end-to-end)

**Bloqueado até**: T1 e T2 ambos resolvidos.

**Hipótese**: caminho feliz saturou compressao; mínimo + transporte
basta.

**Saída**: configuração default recomendada para v0.4.

### ADIADOS

- **EXP-004 (stratified STATS HP-A1)**: escopo LLM ⚫ separado.
  Roda apenas quando reabrirmos M-llm-integration-future.

## Critério de pivot por passo (resumo)

| Passo | Resultado inesperado | Pivot |
|-------|---------------------|-------|
| 1 | gzip nao comprime CSV (<5%) | revisar datasets — talvez muito pequenos |
| 2 | smart >> compact (>15% adicional) | confirmar implementando E ou I isolada antes de tudo |
| 2 | smart < compact | bug — pausar e revisar |
| 3 (B) | type-preserving complica decoder demais | manter so opt-in |
| 3 (F) | auto-sortedness escolhe errado em >20% datasets | tornar opt-in, nao default |
| 4 | chunks SEMPRE piores que monolitico em qualquer batch | revisar D2 (rebreak) — aceitar atravessar boundary? |

## Princípio operacional

**Um passo por vez**:
1. Rodar
2. Olhar resultado com calma
3. Discutir
4. Decidir próximo passo
5. Apenas então código novo

**Nada definitivo**: cada passo pode pivotar com base nos resultados.
Hipóteses são para refutar; o que sobrevive vira default.

## Estado atual (2026-05-05)

- Bancada arquivada
- Hipoteses listadas (10)
- Fluxo refinado
- Pendente: rodar EXP-003a (proximo passo)

Quando rodar EXP-003a, criar pasta `experiments/lab/clean/EXP-003a-calibration/`
com README, run.py usando framework, e results/ reproduzivel.
