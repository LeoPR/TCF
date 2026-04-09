# 4. Metodologia

## 4.1 Dataset de Referencia

Dataset relacional pequeno representando um cenario de e-commerce:

| Tabela | Colunas | Linhas | Descricao |
|--------|---------|--------|-----------|
| pessoas | id, nome | 30 | Clientes |
| produtos | id, nome | 12 | Catalogo |
| vendas | id_pessoa, id_produto, vl | 41 | Transacoes |

Escolha justificada:
- Pequeno o suficiente para caber no contexto de todos os modelos
- Relacional (FKs) para testar resolucao de nomes
- Valores numericos (vl) para testar raciocinio matematico
- Distribuicao realista (algumas pessoas compram mais que outras)

## 4.2 Banco de Perguntas (3 Camadas Diagnosticas)

### Layer 0: math_control (capacidade aritmetica)
Aritmetica pura sem formato. Isola se o modelo sabe fazer contas.

| Pergunta | Tipo | Ground Truth |
|----------|------|-------------|
| math_control_sum | Somar lista de numeros | sum(vl) = 217.55 |
| math_control_count | Contar numeros na lista | count = 41 |

### Layer 1: decode_only (compreensao de formato)
Ler o formato e listar valores. Isola se o modelo entende a estrutura.

| Pergunta | Tipo | Ground Truth |
|----------|------|-------------|
| decode_vl | Listar todos os valores de vl | 41 floats em ordem |

### Layer 2: compute (pipeline completo)
Formato + operacao. Testa a capacidade combinada.

| Pergunta | Tipo | Complexidade | Ground Truth |
|----------|------|-------------|-------------|
| q1_sum_vl | Soma | Dificil | 217.55 |
| q2_avg_vl | Media | Dificil | 5.3061 |
| q3_max_vl | Maximo | Facil | 12.4 |
| q4_min_vl | Minimo | Facil | 1.0 |
| q5_count_rows | Contagem | Dificil* | 41 |
| q6_count_ana | FK + contagem | Media | 3 |
| q7_sum_ana | FK + soma | Dificil | 8.7 |
| q8_top_product | Lookup nome | Facil | Caneta |
| q9_distinct_pessoa | Count distinct | Media | 30 |
| q10_top_spender | FK + argmax | Media | Isabela |

*q5 surpreendentemente dificil em TCF multi-tabela (gpt-oss respondeu 83=30+12+41)

## 4.3 Ground Truth Programatico

Ground truth NUNCA e hardcoded. Derivado de `ground_truth.compute(data_dir)`:
- Le CSVs fonte
- Calcula todas as respostas esperadas
- Se o dataset mudar, ground truth se ajusta automaticamente

## 4.4 Metricas

### Accuracy
- Numerico: tolerancia de 1% ou 0.1 (o que for maior)
- Contagem: exact match (inteiro)
- Nome: substring match (case-insensitive)

### Classificacao de Erro (7 categorias)
```
correct | list_instead_of_agg | wrong_count |
hallucinated | arithmetic_error | refusal | parse_failure
```

### Telemetria
- `latency_s`: tempo wall-clock (inclui rede)
- `total_duration_s`: tempo Ollama total
- `load_duration_s`: tempo de carga do modelo
- `prompt_eval_s`: tempo de processar prompt (prefill)
- `eval_s`: tempo de gerar resposta (decode)
- `prompt_tokens`: tokens do prompt
- `response_tokens`: tokens gerados

## 4.5 Design Experimental em Fases (Ablacao Progressiva)

```
Phase 0 (gate)     →  Encode/decode reversivel? (sem LLM, 0 calls)
Phase 1 (formato)  →  CSV vs JSONL vs TCF × N modelos (~210 calls)
                       Filtra modelos: accuracy >= 30% → survivors
Phase 2 (ablacao)  →  24 variantes TCF × survivors (~720 calls)
                       Seleciona top configs → top_configs.json
Phase 3+ (avancado)→  Supertable, deduction, decode reverso, CoT/PoT
```

Cada fase **reduz** o espaco da proxima. Estimativa total: ~1.600-2.000 calls
(vs 7.000-9.000 de um design flat sem ablacao).

## 4.6 Formatos Comparados

| Formato | Tipo | Dados enviados |
|---------|------|---------------|
| CSV | Row, desnormalizado | pessoa,produto,vl (JOIN pronto) |
| JSONL | Row, desnormalizado | {"pessoa":"Ana","produto":"Caneta","vl":2.5} |
| TCF (id_raw) | Column, normalizado | 3 tabelas com IDs numericos |
| TCF (inline) | Column, desnormalizado | 1+ tabelas com nomes resolvidos |
| TCF (supertable) | Column, desnormalizado | 1 tabela unica (planejado) |

**Nota metodologica (F7):** Phase 1 compara CSV/JSONL desnormalizados vs TCF
normalizado. Isso e um vies documentado. Phase 2 inline corrige.

## 4.7 Configuracao Experimental

- **temperature=0, seed=42** para reproducibilidade
- **stream=False** para timing preciso
- **Warmup:** 1 chamada trivial por modelo antes dos testes
- **Idempotencia:** manifest tracking permite interromper e retomar
- **Modelos:** auto-discovery via Ollama, ordenados por tamanho (menores primeiro)
