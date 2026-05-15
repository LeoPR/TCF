# 4. Metodologia

## 4.1 Dataset de Referencia — retail_sales v2

Dataset sintetico relacional inspirado em TPC-H, gerado por
`tests/fixtures/synthetic_v2.py`:

| Tabela | Colunas | Descricao |
|--------|---------|-----------|
| clientes | id, nome | Clientes (nomes pt-BR) |
| produtos | id, nome | Catalogo (20 produtos) |
| vendas | id, id_cliente, id_produto, dt, qtd, preco_unit, total | Transacoes |

**Parametros ajustaveis:**
- `n_orders`: numero de pedidos (20, 50, 100, 200, 500, 1000, 5000)
- `n_customers`: default = n_orders/10 (ratio 1:10 cliente:pedido, Zipf s=1.0)
- `n_products`: 20 (frequencia Zipf)
- `seed`: 42 (reproducibilidade determinista)
- `null_rate`: 5% (simula dados reais com missing values)

**Por que este dataset:**
- **Zipf s=1.0:** reproduz distribuicao realista de frequencia (Pareto 80/20)
- **Ratio 1:10:** cada cliente faz em media 10 pedidos (realista em retail)
- **FKs reais:** id_cliente e id_produto referenciam tabelas separadas
- **Tipos mistos:** datetime, int, float, string
- **Nullable:** preco_unit pode ser null (5%)
- **Expansao por pedido:** cada order gera 1-5 line items (Poisson λ=2.5)

Uma chamada `retail_sales(200)` gera ~509 linhas de vendas, 20 clientes,
20 produtos. Tamanhos tipicos:

| Formato | 50 orders | 200 orders | 1000 orders | 5000 orders |
|---------|-----------|------------|-------------|-------------|
| CSV | 5K | 21K | 104K | 545K |
| JSONL | 14K | 60K | 295K | 1.5M |
| TCF L0 | 5K | 22K | 104K | 545K |
| TCF L2 | 3.5K | 19K | 93K | 486K |
| TCF L3 | 3K | 12K | 55K | 265K |

## 4.2 Banco de Perguntas

### Layer 2: compute (8 questoes, usado em todos os experimentos)

| ID | Pergunta | Tipo | Categoria |
|----|----------|------|-----------|
| q1_sum | Soma de 'total' | numeric | aggregate |
| q2_avg | Media de 'total' | numeric | aggregate |
| q3_max | Maximo de 'total' | numeric | lookup |
| q4_min | Minimo de 'total' | numeric | lookup |
| q5_count | Numero de linhas | count | aggregate |
| q6_top_product | Produto mais frequente | string | argmax freq |
| q7_top_spender | Cliente que mais gastou | string | argmax agg |
| q8_distinct | Clientes distintos | count | aggregate |

### Layer 0 e 1 (diagnostico 3-layer)

**Layer 0 (math_control):** aritmetica pura sem formato
- "Some estes valores: 2.5 11 1 3.75 ..." (sem header, sem formato)

**Layer 1 (decode_only):** ler formato sem calcular
- "Liste todos os valores da coluna 'total', separados por espaco"

### Questoes pendentes (P-question-bank-review)

- q11_filter (filter por valor especifico: "total de vendas de Caneta")
- q12_threshold (condicional: "quantos pedidos acima de R$50?")

## 4.3 Ground Truth Programatico

Ground truth NUNCA e hardcoded. Derivado dinamicamente de cada chamada
`retail_sales(seed=42)`:

```python
def compute_ground_truth(tables):
    clientes = {c["id"]: c["nome"] for c in tables["clientes"]}
    produtos = {p["id"]: p["nome"] for p in tables["produtos"]}
    vendas = tables["vendas"]
    totals = [float(v["total"]) for v in vendas if v["total"]]
    return {
        "sum_total": round(sum(totals), 2),
        "avg_total": round(sum(totals) / len(vendas), 2),
        "max_total": max(totals),
        "min_total": min(totals),
        "count": len(vendas),
        "top_product": produtos[Counter(v["id_produto"] for v in vendas).most_common(1)[0][0]],
        "top_spender": max(person_totals, key=person_totals.get),
        "distinct_customers": len(set(v["id_cliente"] for v in vendas)),
    }
```

Se o dataset mudar (nova seed, mais rows), ground truth ajusta automaticamente.

## 4.4 Metricas e Scoring

### Accuracy
- **Numerico (sum, avg, max, min):** tolerancia 2% ou 0.5 (o que for maior)
- **Count:** exact match (inteiro)
- **String (top_product, top_spender):** substring match (case-insensitive)

### Classificacao de Erro (7 categorias)

| Categoria | Descricao |
|-----------|-----------|
| `correct` | Resposta exata ou dentro da tolerancia |
| `arithmetic_error` | Numero parseavel mas fora da tolerancia |
| `wrong_count` | Inteiro plausivel mas errado |
| `wrong_name` | String sem substring esperada |
| `list_instead_of_agg` | Listou valores ao inves de agregar (>5 numeros na resposta) |
| `hallucinated` | Valor fora da ordem de grandeza |
| `parse_failure` / `refusal` | Nao conseguiu extrair resposta |
| `exception` | Erro de rede / timeout |

### Telemetria registrada

```json
{
  "model": "gemma3:12b",
  "format": "tcf_L0",
  "question": "q1_sum",
  "correct": true,
  "error_type": "correct",
  "response": "147445.47",
  "latency_s": 16.2,
  "prompt_chars": 21954
}
```

## 4.5 Design Experimental — Ablacao Progressiva

Cada experimento **elimina hipoteses** para o proximo:

```
[1] Encode/Decode roundtrip      → valida reversibilidade (sem LLM)
[2] Compression benchmark        → quantifica compressao (sem LLM)
[3] Etapa 1 (qwen3 + 5 formatos) → isola efeito do formato
[4] Etapa 2 (12 modelos + 3 formatos) → isola efeito do modelo
[5] G30 (hiperparametros)        → isola thinking e temperature
[6] 3-layer diagnostic            → ATRIBUI causalidade (formato vs calculo vs STATS)
[7] Stats ablation                → QUANTIFICA o papel dos STATS
[8] Scale progression             → caracteriza sweet spot de escala
[9] Transport compression         → valida ganho em gzip (sem LLM)
```

Cada etapa produz findings que reinterpretam etapas anteriores.
Exemplo: o diagnostic 3-layer (etapa 6) revelou que os altos scores
de gemma3 em Etapa 2 (etapa 4) vinham de leitura de STATS, nao de
compreensao real do formato.

## 4.6 Formatos Comparados

| Formato | Tipo | Descricao |
|---------|------|-----------|
| CSV | Row, flat | Desnormalizado (JOIN resolvido) |
| JSONL | Row, self-describing | Desnormalizado, chaves repetidas por linha |
| TCF L0 | Column, expanded | Supertable flat, STATS opcional, sem RLE |
| TCF L1 | Column, RLE | RLE em runs consecutivos naturais |
| TCF L2 | Column, sorted+RLE | Sort pela melhor coluna + RLE |
| TCF L3 | Column, dict+sorted+RLE | Dict encoding + sorted + RLE |

**Unificacao metodologica:** todos os formatos recebem **os mesmos
dados desnormalizados** (supertable). Nao ha vies de normalizacao —
TCF nao "ganha" por ter multiplas tabelas.

## 4.7 Modelos Avaliados

**Criterios de selecao:**
1. **Cobertura de tamanho:** 0.75B a 20.9B (log scale)
2. **Cobertura de familia:** qwen3, gemma3, gemma2, llama, phi, deepseek, gpt-oss, mistral
3. **Excluir obsoletos:** versoes superadas por novas (phi3 < phi4, qwen2.5 < qwen3)
4. **GPU constraint:** max ~14B Q4_K_M (RTX 3060 12GB), excecao gpt-oss 20B MXFP4
5. **Thinking coverage:** incluir modelos com e sem thinking

Ver [P-G35-modelos-llm](../../tickets/open/P-G35-modelos-llm.md) para catalogo completo.

## 4.8 Configuracao Ollama

```python
LLM_OPTIONS = {
    "temperature": 0,     # deterministic (confirmado ideal por G30)
    "seed": 42,           # reproducibility
}
```

- `stream=False` para timing preciso
- `num_ctx`: auto-expande (Ollama nao trunca)
- **Warmup:** 1 chamada trivial por modelo antes dos testes
- **Idempotencia:** manifest tracking permite interromper e retomar
  (cada combo identificado por `key=model|scale|format|question`)

## 4.9 Reproducibilidade

Todos os experimentos sao reproduziveis:
- Encoder deterministico (mesmo input = mesmo output byte-a-byte)
- Dataset deterministico (seed=42 fixo)
- Ollama com temperature=0 e seed=42
- Ground truth computado, nunca hardcoded
- Cada runner salva manifest JSONL — rerun pula combos completados

Versionamento via git (`.gitconfig`, `.gitignore`, commits com findings).
