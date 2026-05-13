# H03 — Decomposição Diagnóstica: Formato vs Aritmética

**Status:** ABERTO  
**Tipo:** Metodológico — contribuição central do paper  
**Deps:** P02, P05, P06  
**LLM calls:** ~900

## Hipótese

A diferença de accuracy entre TCF e JSONL em perguntas de compute (Layer 2) é explicada pela dificuldade de decodificação do formato (Layer 1), não pela capacidade aritmética do modelo (Layer 0).

**H3_0 (nula):** Não há interação entre formato e camada diagnóstica.

## As 3 Camadas

| Camada | Nome | O que testa | Exemplo |
|--------|------|-------------|---------|
| L0 | `math_control` | Aritmética pura, sem formato | "Some: 2.5 11.0 1.0 ..." |
| L1 | `decode_only` | Leitura do formato, sem conta | "Liste todos os valores de vl" |
| L2 | `compute` | Pipeline completo | "Qual é a soma de vl?" |

## Design

```
2 formatos (TCF vs JSONL) × 3 camadas × 10 modelos × 5 runs
= 300 calls por pergunta selecionada
```

**Pergunta de diagnóstico usada:** `sum_vl` (Q1) — mais simples e com ground truth exato.

**Leitura dos resultados:**

```
L0 ✗ → modelo não sabe somar. Formato irrelevante.
L1 ✗ → modelo não lê o formato. Formato é o gargalo.
L0 ✓ + L1 ✓ + L2 ✗ → interação complexa (contexto longo, atenção)
L0 ✓ + L1 ✓ + L2 ✓ → formato viável com este modelo
```

**Predição:** Se TCF > JSONL em L2 mas ambos iguais em L0, o ganho é atribuível ao formato.  
Se divergem em L1 (decode accuracy), a legibilidade do formato é o mecanismo.

## Métricas adicionais para L1

`decode_accuracy` = fração dos 41 valores de `vl` presentes na resposta (order-insensitive).  
Requer scorer de sequência — ver **P02**.

## Output esperado

```
modelo       | L0(aritmética) | L1(decode TCF) | L1(decode JSONL) | L2(compute TCF) | L2(compute JSONL)
tiny (<3B)   |     ?          |      ?         |       ?          |       ?         |       ?
small (3-7B) |     ?          |      ?         |       ?          |       ?         |       ?
medium (7-14B)|    ?          |      ?         |       ?          |       ?         |       ?
```
