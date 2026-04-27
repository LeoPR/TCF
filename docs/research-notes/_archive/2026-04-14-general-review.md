# Revisao Geral do Projeto — 2026-04-14

Revisao solicitada pelo usuario apos introducao de conceitos intermediarios
(metricas multi-nivel, progressive diagnostic, TOON reality check).

---

## 1. Estado geral

- **32 tickets DONE** (Fases 1, 1.5, 2a) — fundacao solida
- **4 tickets ativos** (23, 24, 29, 30) — prioridades claras
- **34 tickets frozen** — futuro trabalho
- **195 testes** passando
- **2 datasets canonicos** (TPC-H 60K + Adult 48K)
- **7 formatos** comparados (CSV, JSONL, TOON, TCF L0-L3)
- **Benchmark LLM** rodando (489/600)

## 2. Resultados que NAO precisam refazer

| Resultado | Valido | Razao |
|-----------|--------|-------|
| Compression benchmark (Etapa B+C) | Sim | Dados canonicos, persistido em JSON |
| Encoder roundtrip (195 tests) | Sim | 60K rows L2 roundtrip ok |
| Shaper (50 tests) | Sim | Funcional, testado |
| src/tcf/timing.py | Sim | Independente de dados |

## 3. Resultados que precisam COMPLEMENTAR (nao refazer)

| Resultado | O que falta | Acao |
|-----------|-------------|------|
| F80-F84 (diagnostic) | Feito em retail_sales | Ticket 30 refaz em canonicos |
| F90-F94 (stats ablation) | Feito em retail_sales | Refazer em canonicos |
| TOON comparison | Comparamos tamanho mas nao metodologia | Reavaliar com rigor |

## 4. Conceitos novos que podem mudar resultados

### Metricas multi-nivel (docs/research-notes/2026-04-14-evaluation-metrics.md)

O benchmark D esta gravando dados suficientes (prompt_tokens, response,
latency, error_type) para aplicar as novas metricas **pos-hoc**. NAO
precisa re-rodar os combos — so re-analisar.

### Progressive diagnostic (ticket 30)

Pode revelar que modelos que pareciam "0%" na verdade acertam com
poucos dados. Isso muda a narrativa mas nao invalida os benchmarks
de escala.

### TOON reality check

Precisamos de revisao mais rigorosa antes de concluir que "TOON nao
comprime". Eles medem coisas diferentes (tiktoken vs prompt_eval_count,
datasets diferentes, modelos diferentes). Comparacao apples-to-apples
requer normalizar metricas.

## 5. Limpeza pendente

13 tickets DONE em `open/` precisam ir para `closed/`. Isso nao muda
nada tecnicamente mas reduz confusao visual.

## 6. Ordem de execucao revisada

### Imediato
1. ✅ Benchmark D termina (~110 combos restantes)
2. analyze_llm_results.py com metricas multi-nivel
3. Mover tickets DONE para closed/

### Curto prazo
4. Ticket 30 (progressive diagnostic) — validacao limpa
5. Reavaliar TOON com rigor metodologico
6. Stats ablation em dados canonicos

### Medio prazo
7. Reescrever article/07-results.md com dados canonicos
8. Gerar figuras (compression + accuracy + tokens)
9. Ticket 29 (decoder freetext fix)

### Futuro
10. Numeric precision (ticket 23)
11. Descongelar tickets frozen conforme necessario

## 7. Conclusao

O projeto esta em bom estado. A fundacao (Fase 1 + 1.5) e solida.
O encoder refatorado (Fase 2a) e limpo. Os benchmarks (B, C, D) sao
sobre dados canonicos reais.

O que falta e **analise e interpretacao** — nao mais infraestrutura.
Os dados estao sendo coletados. As metricas estao definidas. O proximo
passo e entender o que os dados dizem.
