# llm-benchmark — Benchmark LLM v0.5 (ACESSÓRIO, não TCF-core)

> **Fronteira de separação de concerns** (reorg 2026-06-02). Todo o material
> do ciclo **v0.5 LLM benchmark** (Phase 1, Q01–Q38, Linha A/B, M-series)
> vive aqui, separado do TCF-core v0.6 (`src/tcf/`). Candidato a spin-off
> para repo próprio (`tcf-llm-tools`) no futuro — ver
> [tickets/T-RECOVER-LLM-SCHEMA-MODE.md](../tickets/T-RECOVER-LLM-SCHEMA-MODE.md).

## O que é

Benchmark de **compreensão de tabelas por LLMs**: mede quão bem modelos
comerciais e locais respondem perguntas sobre dados formatados (CSV / JSONL /
TOON / TCF), em duas linhas — **Linha A** (LLM lê e computa) e **Linha B**
(LLM gera SQL, SQLite executa). 2256 registros, 38 findings (F-Q01..Q38).

**NÃO é o algoritmo TCF v0.6.** O core (`src/tcf/`: OBAT + HCC, `encode`/
`decode`, formato `#TCF.6` congelado) é independente e não importa nada daqui.
Este benchmark usava o **motor de níveis v0.5** (`old/tcf/`,
`EncodeConfig(level=N)`) — ver [`old/tcf/LEVELS-REVIEW.md`](../old/tcf/LEVELS-REVIEW.md).

## Estrutura

```
llm-benchmark/
├── eval/              ← harness: 34 run_*.py + llm_eval/ (CommercialClient,
│                        OllamaClient, prompts, metrics, ground_truth, ...)
│   ├── llm_eval/      ← biblioteca de suporte do benchmark
│   ├── probes/        ← probes de budget/diagnostico
│   ├── data_sources.py, analyze_results.py
├── scripts/          ← 3 benchmark_*.py (LLM accuracy / diagnostic / stats).
│                        QUEBRADOS contra v0.6 (importam old/tcf) — historico.
├── results/          ← (gitignored) manifests/logs das rodadas LLM
└── scratch/          ← (gitignored) scratch v0.5
```

## Estado (2026-06-02)

- **Acessório, parado.** Nenhum trabalho ativo. Mantido para contexto
  histórico e eventual Phase 2 / spin-off.
- Os 3 `scripts/benchmark_*.py` e o `eval/` importam `encode_columns`/
  `EncodeConfig` do **motor v0.5** (`old/tcf/`), não de `src/tcf/`. Não rodam
  contra o v0.6 sem repointar para `old.tcf`.
- `results/` e `scratch/` são **gitignored** (output regenerável) — ficaram
  fisicamente em `experiments/` (não versionados); este README documenta o
  destino lógico.

## Achados

Catálogo F-Q01..Q38 em [docs/findings/](../docs/findings/) (ainda em `docs/`;
movimento para cá é a Fase 6 da reorg, gated). Sumário paper-ready em
[docs/FINDINGS_SUMMARY.md](../docs/FINDINGS_SUMMARY.md).

## Reproduzir (histórico — requer Ollama / chaves de API)

```bash
pip install -e ".[eval]"          # requests, p/ Ollama client
# runners individuais (entrypoints reais; nao ha' 'python -m'):
python llm-benchmark/eval/run_m9_adult.py --naturalness all
python llm-benchmark/eval/run_m_acomm.py --naturalness all   # comercial ($)
```
