---
title: Metodologia de medição de tempo — limitações e protocolo correto
date: 2026-04-22
type: research-note
status: ALERTA — não bloqueia experimentos atuais
---

# Medições de tempo nos experimentos M1-M5: o que vale e o que não vale

## TL;DR

`total_ms` gravado em M1-M5 é **indicativo de ordem de grandeza**, não benchmark
publicável. Para citar latência em paper, é necessária uma fase M_perf dedicada.
Não requer refazer M1-M5 — só requer fase adicional de timing antes de publicar.

---

## O que temos agora

O campo `total_ms` em todos os manifests vem de:
```python
total_ms = result.get("total_duration_ns", 0) // 1_000_000
```

`total_duration_ns` é o **wall-clock server-side do Ollama** desde recebimento
do request até envio da resposta. Inclui:
- `load_duration_ns` — carregamento do modelo (0 se já em memória, pode ser
  vários segundos se houve eviction da VRAM)
- `prompt_eval_ns` — prefill (processamento do prompt)
- `eval_ns` — decoding (geração de tokens)

**O que NÃO está sendo gravado:** `load_duration_ns`, `prompt_eval_ns`, `eval_ns`
separados. O `GenerateResult` do ollama_client.py tem todos os quatro campos,
mas os runners (M1-M5) só persistem `total_ms`.

## Problemas para uso como benchmark

### 1. Medição única — sem réplicas
Cada combo tem exatamente 1 medição de tempo. Sem réplicas, é impossível:
- Detectar outlier (OS preemption, cache miss, thermal throttling)
- Calcular CV (coefficient of variation) como indicador de estabilidade
- Descartar medida ruim e repetir

**Analogia:** medir uma amostra numa balança científica uma vez. Qualquer
vibração, vento ou nivelamento incorreto contamina o resultado.

### 2. `load_duration` contamina o sinal
Se o warmup não manteve o modelo em memória (timeout do Ollama < tempo entre
chamadas), uma chamada que "carregou o modelo" vai ter `total_ms` 10-50x maior
que as demais do mesmo combo. Sem separar `load_duration`, isso parece
"essa query foi mais lenta" quando na verdade foi "modelo tinha sido descarregado".

### 3. Ruído de OS scheduling (single-machine, sem isolamento)
O experimento roda no mesmo OS que outros processos. Uma única medição de 
timing pode ser inflacionada por:
- Antivírus/indexação rodando em background
- GC do Python
- Flush de disco
- Outros processos usando CPU/GPU

### 4. Ordem das chamadas afeta KV cache state
Ollama mantém KV cache. Chamadas sequenciais com prompts similares (ex:
mesma payload, perguntas diferentes) se beneficiam de reutilização. A ordem
dos combos nos runners pode criar viés sistemático.

---

## O que vale hoje (order of magnitude)

Apesar das limitações, algumas comparações são robustas **por magnitude**:

| Comparação | Ratio M5 | Robusto? |
|------------|----------|---------|
| CoT-SQL vs SQL (4726ms vs 1931ms) | 2.4× | **Sim** — gap grande demais para ser ruído |
| Pandas vs SQL (2113ms vs 1931ms) | 1.1× | **Não** — dentro da margem de ruído |
| Polars vs Pandas (2127ms vs 2113ms) | ~1× | **Não** |

**Regra prática:** ratio > 1.5× com N > 100 pode ser reportado como "indicativo".
Ratio < 1.3× requer benchmark dedicado.

---

## Protocolo correto para M_perf (fase futura)

### Estrutura
- **3 réplicas por (model, variant, question_type)** — não por seed de dados
  (o tempo não depende dos dados, só do tamanho do prompt e do schema)
- **Warmup obrigatório:** 2 chamadas descartadas antes de medir
- **Intervalo fixo entre réplicas:** 5s de sleep para garantir que KV cache
  expire e o sistema esteja em estado estável

### O que gravar (tudo disponível em GenerateResult)
```python
{
    "total_ms": total_duration_ns // 1_000_000,
    "load_ms": load_duration_ns // 1_000_000,
    "prefill_ms": prompt_eval_ns // 1_000_000,
    "decode_ms": eval_ns // 1_000_000,
    "prompt_tokens": prompt_tokens,
    "response_tokens": response_tokens,
    "tokens_per_sec": response_tokens / (eval_ns / 1e9)
}
```

### Métrica de interesse: `decode_ms / response_tokens` = ms por token
Esta é a métrica canônica de throughput de inferência — independe do tamanho
do prompt, compara modelos justos.

### Detecção de outlier
Para cada trio de réplicas:
```python
vals = sorted([t1, t2, t3])
if vals[2] / vals[0] > 1.5:   # outlier: máximo é 50%+ maior que mínimo
    flag_for_repeat = True
    use = (vals[0] + vals[1]) / 2  # usar dois menores se não repetir
else:
    use = median(vals)
```

### Condições a cobrir (mínimo)
- 3 modelos × 4 variantes × 2 question types (simples=q_count, complexo=q_lookup)
- = 24 combos × 3 réplicas = 72 chamadas
- Estimativa: ~30-45 min de execução

---

## Impacto nos experimentos atuais

**M1-M4:** `total_ms` presente mas sem `load_ms` separado. **Não re-fazer.**
Mencionar como "indicativo" se citado.

**M5:** Mesma situação. Os números de latência no `analyze_results.py --perf`
são válidos para discussão qualitativa, não para tabela de benchmarks.

**Paper:** Seção de performance deve referenciar M_perf quando feita, não M1-M5
diretamente. Alternativa: notar explicitamente que são "single-run, não-isolado,
wall-clock server-side" e reportar como "ordem de grandeza".

---

## Status

- [ ] M_perf — benchmark dedicado (pré-publicação, baixa urgência)
- [x] Alerta registrado — não bloqueia M5, M6, M8
