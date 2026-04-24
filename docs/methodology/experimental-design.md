# TCF -- Design Experimental em Fases (Ablacao Progressiva)

> **Nota:** Este documento descreve a metodologia geral de ablacao progressiva.
> As fases originais (Phase 0-3) foram executadas com o encoder v0.1.
> O encoder v0.2 usa M-series (M0..M8+) com a mesma logica de ablacao.
> Achados consolidados: [F-findings.md](F-findings.md).
> Sintese para paper: [article/07-results.md](../article/07-results.md).

## Status M-series (2026-04-22)

| Experimento | Status | Achados | Manifests |
|-------------|--------|---------|-----------|
| M0 (qualificacao) | DONE | F-Q10..F-Q12 | m0_qualification |
| M1 (stats fewshot baseline) | DONE | F-Q7..F-Q9 | m1_stats_fs |
| M2 (fewshot ablation) | DONE | F-Q6 (fewshot obrigatorio) | m2_fewshot_ablation |
| M3 (cross-domain) | DONE | F-Q16 (generalizacao 3 dominios) | m3_cross_domain |
| M4 (CSV vs JSON vs TCF) | DONE | F-Q17 (TCF~=JSON>CSV; FK topology) | m4_baseline |
| M5 (SQL vs Pandas vs Polars vs CoT) | DONE | F-Q18 (SQL>Pandas>Polars; CoT nao ganha) | m5_intermediate |
| M6 (WHERE/HAVING/GROUP-SUM) | DONE | F-Q19 (HAVING 7%; filtros 100%) | m6_filter |
| M6b (HAVING+subquery fewshot) | DONE | F-Q19b: 7%→88.9% (+81.9pp) | m6b_having_fix |
| M7 (subquery/CTE/COUNT DISTINCT) | DONE | F-Q20: 86.4%; CTE=100%, nested=78% | m7_complex |
| M_inv (invariant classification) | DONE | F-Q21: 21% Type A, 79% Type B silent | (análise post-hoc) |
| M8 (safe-sql flags isolados) | DONE | F-Q22: safe_having +70pp; off-target interference | m8_safe_sql |
| M8b (safe-sql combinações) | DONE | F-Q23: 11/12 combinações regridem vs aditivo | m8b_safe_sql_combos |
| M8 (modelos comerciais) | PENDENTE | — | — |
| M_perf (benchmark timing) | PENDENTE | pre-publicacao | — |

## Principio

O pipeline experimental segue uma logica de **ablacao progressiva**:
cada fase filtra modelos e configuracoes com base nos resultados da fase
anterior, reduzindo o espaco de busca antes de investir em combinacoes
mais caras. Isso e inspirado em praticas de NAS (Neural Architecture Search)
e ablation studies comuns em papers de ML.

```
Phase 0: Gate (encode/decode funciona?)
    │ pass
    v
Phase 1: Formatos basicos x todos os modelos
    │ filtro: accuracy >= threshold
    v
Phase 2: Variantes TCF x modelos sobreviventes
    │ filtro: melhores configs
    v
Phase 3: Escala + interacoes (top modelos x top configs)
    │
    v
Analise: testes estatisticos, figuras, paper
```

---

## Phase 0 -- Reversibility Gate (H01)

**Objetivo:** Verificar que encode -> decode preserva os dados.

**O que roda:**
- Para cada variante do EncoderConfig:
  - `encode(meta, data_dir, config)` -> TCF text
  - `decode(tcf_text)` -> tables
  - Compara com CSV original (tolerancia por variante)

**Criterio de passagem:**
- raw_float: diff == 0 (lossless)
- int_scaled: diff <= 1/scale (lossless em inteiros)
- bins_16: diff <= half bin width

**Chamadas LLM:** 0  
**Tempo estimado:** < 5 segundos  
**Bloqueado por:** P04 (encoder variants)

**Saida:** `experiments/results/phase0/reversibility.json`

---

## Phase 1 -- Formato Principal x Modelos (H02 + H03)

**Objetivo:** Determinar quais modelos entendem dados tabulares e qual
formato (CSV, JSONL, TCF baseline) performa melhor em cada camada.

### 1.1 Auto-discovery de Modelos

```bash
python -m experiments.eval phase1 --models auto
```

O runner consulta `GET /api/tags` no Ollama e seleciona modelos:
- Diversidade de familia (llama, gemma, qwen, phi, mistral, ...)
- Diversidade de tamanho (tiny < 4B, small < 8B, medium < 14B, large)
- Exclui modelos de visao (mllama, qwen-vl) por default

### 1.2 Matriz Phase 1

| Dimensao     | Valores                           | Count |
|-------------|-----------------------------------|-------|
| Modelos     | auto-discovered (tipico 5-8)      | ~6    |
| Formatos    | csv, jsonl, tcf (raw_float+id_raw)| 3     |
| Camadas     | math_control, decode_only, compute| 3     |
| Perguntas   | 2 + 1 + 10 = 13 por camada       | 13    |

**Chamadas LLM por modelo:** ~13 perguntas x 3 formatos = ~39
(math_control roda 1x, sem formato; decode e compute rodam por formato)

**Total estimado:** 6 modelos x 39 = ~234 chamadas

### 1.3 Metricas Coletadas

Para cada (modelo, formato, camada, pergunta):
- `correct` (bool)
- `response` (texto bruto)
- `error_type` (7 categorias)
- `latency_s` (segundos)
- `prompt_tokens` (contagem do Ollama)
- `response_tokens` (contagem do Ollama)

### 1.4 Criterio de Filtragem

Apos Phase 1, classificar modelos por accuracy media no `compute` layer:

```
accuracy_compute = correct_compute / total_compute
```

**Filtro para Phase 2:**
- `accuracy_compute >= 0.3` (pelo menos 30% das perguntas compute corretas)
- OU top-5 modelos por accuracy (o que vier primeiro)

**Justificativa:** Modelos que nao conseguem nem 30% em compute nao vao
melhorar com variantes TCF. Economizamos chamadas.

### 1.5 Saidas

```
experiments/results/phase1/
├── manifest.jsonl          Tracking idempotente
├── results/
│   ├── gemma2_9b.jsonl     Resultados por modelo
│   ├── llama3.1_8b.jsonl
│   └── ...
├── summary.json            Accuracy por (modelo, formato, camada)
└── survivors.json          Lista de modelos que passam para Phase 2
```

---

## Phase 2 -- Variantes TCF (H04 + H05 + H06)

**Objetivo:** Testar qual combinacao de numeric encoding x FK mode x sorted
maximiza accuracy em TCF.

### 2.1 Matriz Phase 2

Somente modelos **survivors** da Phase 1.

| Dimensao     | Valores                                | Count |
|-------------|----------------------------------------|-------|
| Modelos     | survivors (tipico 3-5)                 | ~4    |
| Numeric     | raw_float, int_scaled, bins_16         | 3     |
| FK mode     | id_raw, dict, hint, inline             | 4     |
| Sorted      | True, False                            | 2     |
| Perguntas   | compute layer (10 perguntas)           | 10    |

**Variantes TCF:** 3 x 4 x 2 = 24

**Chamadas LLM por modelo:** 24 variantes x 10 perguntas = 240
**Total estimado:** 4 modelos x 240 = ~960 chamadas

### 2.2 Analise de Ablacao

Para cada fator (numeric, fk_mode, sorted), calcular:

```
delta_accuracy = accuracy(com_fator) - accuracy(sem_fator)
```

Isso permite isolar a contribuicao de cada componente:
- RLE (sorted) ajuda ou atrapalha?
- Inline FK e melhor que ID numerico?
- Quantizacao (bins) perde muita informacao?

### 2.3 Criterio de Filtragem

Selecionar as **top-3 configuracoes TCF** por accuracy media:

```python
configs_ranked = sorted(configs, key=lambda c: mean_accuracy[c], reverse=True)
top_configs = configs_ranked[:3]
```

### 2.4 Saidas

```
experiments/results/phase2/
├── manifest.jsonl
├── results/
│   └── {model}_{numeric}_{fk}_{sorted}.jsonl
├── ablation.json           Delta accuracy por fator
├── summary.json            Ranking de configs
└── top_configs.json        Top-3 configs para Phase 3
```

---

## Phase 3 -- Escala e Interacoes (H07 + H08 + H10)

**Objetivo:** Testar se os resultados se mantem com dados maiores e
analisar interacoes modelo-formato.

### 3.1 Dados Maiores

O dataset atual tem 41 linhas. Para testar escala:
- Gerar datasets sinteticos com 100, 500, 1000 linhas
- Manter mesma distribuicao estatistica (bootstrap ou geracao parametrica)
- Ou usar datasets publicos abertos com estrutura similar

### 3.2 Matriz Phase 3

Somente **survivors** da Phase 2 (top modelos x top configs):

| Dimensao     | Valores                         | Count |
|-------------|----------------------------------|-------|
| Modelos     | top-3 de Phase 2                 | 3     |
| Configs     | top-3 configs TCF + csv + jsonl  | 5     |
| Chunk sizes | 41, 100, 500                     | 3     |
| Perguntas   | compute (10)                     | 10    |

**Chamadas LLM:** 3 x 5 x 3 x 10 = 450

### 3.3 Saidas

```
experiments/results/phase3/
├── manifest.jsonl
├── results/
├── scaling_curves.json     Accuracy vs chunk_size
├── interaction.json        Modelo x formato x tamanho
└── pareto.json             Accuracy vs token count (H09)
```

---

## Resumo de Chamadas LLM

| Fase    | Estimativa | Acumulado | Descricao                    |
|---------|-----------|-----------|------------------------------|
| Phase 0 | 0         | 0         | Gate encode/decode           |
| Phase 1 | ~234      | ~234      | Formato principal x modelos  |
| Phase 2 | ~960      | ~1.194    | Variantes TCF (ablacao)      |
| Phase 3 | ~450      | ~1.644    | Escala + interacoes          |

**Total real: ~1.600-2.000 chamadas** (muito menos que 7.000-9.000 do
design flat original, gracas a ablacao progressiva)

---

## Invocacao do Pipeline

```bash
# Auto-discovery: descobre modelos disponiveis no Ollama
python -m experiments.eval discover

# Phase 0: gate encode/decode (sem LLM)
python -m experiments.eval phase0

# Phase 1: formatos basicos x todos os modelos
python -m experiments.eval phase1 --models auto
python -m experiments.eval phase1 --models gemma2:9b llama3.1:8b  # manual

# Phase 2: variantes TCF x survivors
python -m experiments.eval phase2

# Phase 3: escala (requer dados extras)
python -m experiments.eval phase3

# Status: ver progresso de todas as fases
python -m experiments.eval status

# Analise final
python -m experiments.eval analyze
```

### Idempotencia

Cada fase pode ser interrompida e retomada:

1. **Manifest** tracka cada (modelo, formato, config, pergunta) como key unica
2. Na retomada, combinacoes ja executadas sao saltadas
3. Resultados salvos imediatamente apos cada chamada LLM (nao em batch)
4. `survivors.json` e `top_configs.json` persistem entre fases

### Filtro Automatico entre Fases

```
Phase 1 ──> survivors.json ──> Phase 2
Phase 2 ──> top_configs.json ──> Phase 3
```

Se `survivors.json` nao existe, Phase 2 avisa e pede para rodar Phase 1 primeiro.
Se `--force` for passado, ignora filtro e roda tudo (debug mode).

---

## Relacao com Hipoteses do Paper

| Fase    | Hipoteses | O que Responde                              |
|---------|----------|----------------------------------------------|
| Phase 0 | H01      | O encoding e reversivel?                     |
| Phase 1 | H02, H03 | Formato afeta accuracy? Onde esta o gargalo? |
| Phase 2 | H04-H06  | Qual componente TCF mais importa?            |
| Phase 3 | H07-H10  | Resultados escalam? Interacoes modelo-formato|

---

## Consideracoes Metodologicas

### Repeticoes

LLMs sao estocasticos. Para resultados robustos:
- Phase 1: 1 repeticao (triagem rapida)
- Phase 2: 3 repeticoes (ablacao precisa desvio padrao)
- Phase 3: 3 repeticoes (confirmar resultados)

Isso multiplica chamadas de Phase 2 e 3 por 3.

### Temperatura

Usar `temperature=0` para reproducibilidade maxima.
Documentar se o modelo respeita `temperature=0` (nem todos respeitam).

### Randomizacao

Ordem das perguntas pode afetar resultado (efeito de priming).
Considerar aleatorizar ordem das perguntas por trial.

### Ameacas a Validade

1. **Interna:** Dataset pequeno (41 linhas), pode nao generalizar
2. **Externa:** Modelos locais (quantizados), resultados podem diferir de APIs
3. **Construto:** Perguntas em portugues, viés linguistico
4. **Estatistica:** Sem correcao de multiplas comparacoes (Bonferroni)
