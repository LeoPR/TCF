# P06 — Matrix Runner Idempotente

**Status:** ABERTO  
**Tipo:** Infraestrutura Principal  
**Bloqueia:** H02–H10 (todos os experimentos em escala)  
**Arquivo:** `experiments/eval/run_matrix.py` (criar)

## Problema

~7.000–9.000 LLM calls não cabem numa única sessão. Precisamos de:
1. Runner idempotente — pula calls já feitos
2. Configuração declarativa — hipótese define o que rodar
3. Progresso visível — ETA, % completo
4. Checkpoint automático — retoma de onde parou

## Interface Proposta

```python
# experiment.json
{
  "hypothesis": "H02",
  "formats":  ["csv_expanded", "jsonl_expanded", "tcf_sorted_dict"],
  "models":   ["qwen3:8b", "llama3.1:8b", "gemma2:9b"],
  "questions": ["Q1", "Q2", "Q5", "Q8"],
  "runs":      5,
  "chunk_sizes": [41],
  "encoder_config": {"numeric": "raw_float", "fk_mode": "dict"}
}
```

```bash
python experiments/eval/run_matrix.py --experiment experiments/H02.json
python experiments/eval/run_matrix.py --experiment experiments/H02.json  # retoma
```

## Estrutura de Output

```
experiments/results/
└── H02/
    ├── manifest.json          ← config usada
    ├── qwen3_8b/
    │   ├── csv_expanded/
    │   │   ├── Q1_run1.json
    │   │   ├── Q1_run2.json
    │   │   └── ...
    │   └── tcf_sorted_dict/
    │       └── ...
    └── llama3.1_8b/
        └── ...
```

## Idempotência

Antes de cada call, verificar se `{model}/{format}/{question}_run{n}.json` existe.  
Se sim: pular. Se não: executar e salvar.

## Progresso

```
[H02] qwen3:8b × tcf_sorted_dict
Progress: 47/120 (39%)  ETA: ~18min
  ✓ Q1 run1-5  ✓ Q2 run1-3  ... Q2 run4 ...
```

## Pull Automático

Antes de cada modelo, chamar `client.ensure(model)`. Se modelo não instalado → pull automático.

## Critério de Aceitação

- Rodar com 3 calls → matar processo → rodar de novo → 0 calls repetidos, continua dos 3
- Output JSONL compatível com `metrics.score_results()`
