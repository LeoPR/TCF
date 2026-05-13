# H01 — Reversibilidade: encode → decode = original

**Status:** CLOSED (Phase 0 gate: 7/7 configs reversiveis, 151 testes unitarios passando)  
**Tipo:** Correctness Gate — pré-condição para todos os outros experimentos  
**Deps:** T05 (encoder), P04 (variantes de encoding)  
**LLM calls:** 0 (determinístico)

## Hipótese

`decode(encode(csv)) == csv` para toda célula de toda tabela.

**H1_0 (nula):** Existe ao menos uma célula onde o valor decodificado difere do original.

## Por que importa

Qualquer diferença de accuracy entre TCF e baseline seria confundida se a compressão introduzisse perda de dados. Esta é a pré-condição lógica do paper.

## Design

```
Para cada variante de encoding (raw_float, int_scaled, bins_16):
    encode(pessoas, produtos, vendas) → TCF
    decode(TCF) → tabelas restauradas
    Para cada (tabela, coluna, linha):
        assert valor_restaurado == valor_original  (tolerância float: 1e-4)
```

**Exceções permitidas:**
- `raw_float`: `2.50` → `2.5` (normalização de zeros trailing) — OK
- `int_scaled`: `2.50` × 100 = `250` → `250 / 100 = 2.5` — OK com tolerância
- `bins_16`: perda de precisão por definição — registrar erro médio, não falha binária

## Métricas

| Variante | Células com erro | Erro médio (float) | Status |
|----------|-----------------|-------------------|--------|
| raw_float | 0 | 0.0 | ✅ já passa |
| int_scaled | — | — | pendente P04 |
| bins_16 | n/a (lossy) | medir RMSE | pendente P04 |

## Output

`experiments/results/H01_reversibility.json`
```json
{
  "raw_float":  {"errors": 0, "float_rmse": 0.0},
  "int_scaled": {"errors": 0, "float_rmse": 0.0},
  "bins_16":    {"errors": 41, "float_rmse": 0.42, "note": "lossy by design"}
}
```
