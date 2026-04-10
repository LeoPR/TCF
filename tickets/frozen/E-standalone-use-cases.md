---
title: TCF sem LLM — caracterizacao de uso autonomo
type: experiment
status: OPEN
priority: MEDIUM
created: 2026-04-10
origin: TCF deve ser util mesmo sem LLM (transmissao, storage, dumps legiveis)
---

# TCF sem LLM — Uso Autonomo

## Motivacao

Todos os experimentos ate agora avaliam TCF **para LLMs**. Mas TCF
pode ter valor mesmo sem LLM algum:

1. **Transmissao HTTP:** TCF+gzip < CSV+gzip (F70-F73)
2. **Storage:** arquivos menores em disco
3. **Dumps legiveis:** analista abre .tcf num editor e entende
4. **Diff entre versoes:** mudancas em uma coluna aparecem em um bloco
5. **Dados incrementais:** enviar so colunas novas

Este ticket caracteriza **quando TCF standalone vale a pena**, independente
de LLM.

## Pergunta 1: Escala minima — a partir de quantas linhas TCF comeca a ganhar?

**Dados existentes (P-transport-compression):**

| Scale | csv+gz | L3+gz | Delta |
|-------|--------|-------|-------|
| 50 | 1479 | 1467 | -0.8% (marginal) |
| 200 | 5626 | 4752 | -15.5% |
| 500 | 12681 | 10440 | -17.7% |
| 1000 | 25209 | 19859 | -21.2% |
| 5000 | 125948 | 89472 | **-29.0%** |

**Crossover:** ~100-200 linhas e onde o ganho comeca a ser significativo (>10%).

**Abaixo de 50 linhas:** TCF e equivalente a CSV — overhead de header come o ganho.

## Pergunta 2: Transmissao incremental — faz sentido?

Cenario: um cliente ja tem snapshot v1 dos dados. Server quer enviar
delta (linhas novas + linhas modificadas).

**Com JSON:** envia JSON patch (RFC 6902) ou array de diffs.
**Com CSV:** envia CSV so das linhas novas.
**Com TCF:** envia TCF so das colunas alteradas? Ou das linhas novas?

TCF columnar tem uma propriedade interessante: **se uma coluna nao mudou,
nao precisa reenvia-la**. Ja JSONL envia a linha inteira.

Exemplo: tabela vendas com 6 colunas, so o `total` foi recalculado.
- CSV: reenvia todas as 509 linhas × 6 colunas
- JSONL: reenvia 509 objetos com todas as chaves
- **TCF:** reenvia so o bloco `total:` (1/6 do tamanho)

**Hipotese:** TCF pode ter ganho ~5x em cenarios de atualizacao parcial.

## Pergunta 3: Comparacao com formatos binarios

TCF e textual. Alternativas binarias (Parquet, Arrow, MessagePack) sao
mais compactas no raw. Mas:

| Formato | Raw | Gzip | Legivel | Cross-lang | Embutivel em texto |
|---------|-----|------|---------|------------|---------------------|
| CSV | 100% | 20% | Sim | Sim | Sim |
| JSONL | 280% | 30% | Sim | Sim | Sim |
| **TCF L3** | 50% | 18% | Sim | Futuro | Sim |
| Parquet | 35% | 30% | Nao | Sim | Nao (binario) |
| Arrow | 30% | 28% | Nao | Sim | Nao |
| MessagePack | 70% | 25% | Nao | Sim | Sim (base64) |

**Nicho do TCF:** unico que e textual + compacto + legivel + cross-language.

## Pergunta 4: Edge cases — TCF em contextos minusculos

**Tabelas de 3-10 linhas:** TCF e overhead puro. Header (`# TCF v0.2 level=2`)
come a compressao.

Teste necessario: tabela 5 linhas × 3 colunas em CSV vs TCF. CSV vence?

Se sim, documentar: **TCF tem escala minima. Abaixo disso, CSV e melhor.**

## Pergunta 5: Contextos reais onde TCF brilha

Enumerar casos concretos onde TCF + gzip objetivamente ganha:

### A. APIs REST com dados tabulares
- GET /api/products → retorna 500 produtos
- **Ganho:** 20-30% menos bandwidth com TCF+brotli
- **Custo:** encode server-side + decode client-side
- **ROI:** APIs read-heavy com milhoes de requests/dia

### B. Dumps de analytics
- Export de dashboard para CSV (usuario baixa)
- **Ganho:** arquivo menor no email / disco
- **Custo:** ferramenta precisa saber abrir TCF
- **ROI:** se acompanhado de JS decoder browser, usuario abre online

### C. Logs estruturados
- Logs de servidor com muitas repeticoes (timestamp, user_id, endpoint)
- **Ganho:** RLE dominante, compressao drastica
- **Custo:** nao e append-friendly como JSONL (TCF e batch)
- **ROI:** para dumps periodicos (diario, horario), muito bom

### D. IoT / telemetria
- Sensor envia 1000 leituras agrupadas
- **Ganho:** colunas de timestamp, sensor_id, status sao repetitivas
- **Custo:** codificador precisa rodar no device (C bindings)
- **ROI:** alto em banda limitada (LTE, satelite)

### E. Data lake intermediate
- Ingestao de CSV → processamento → saida intermediate
- **Ganho:** arquivos intermediarios menores, leitura mais rapida
- **Custo:** Parquet ja faz isso
- **ROI:** baixo (Parquet vence)

## Quando TCF **nao** e melhor

- **Dados random/alta cardinalidade:** RLE falha, gzip sozinho iguala
- **Streams append:** TCF e batch, JSONL e melhor para append
- **Queries analiticas (OLAP):** Parquet e melhor (colunar binario otimizado)
- **Interchange com sistemas legados:** CSV e JSON sao universais, TCF nao e

## Tarefas

- [ ] Benchmark de escalas minimas (5, 10, 20, 30, 50 linhas)
- [ ] Simulacao de transmissao incremental (so coluna alterada)
- [ ] Comparacao com Parquet/Arrow em termos de pipeline real
- [ ] Mini-studies de casos reais (API, logs, IoT)
- [ ] Tabela "use TCF when... / don't use TCF when..."
- [ ] Documentar como apendice F do paper
