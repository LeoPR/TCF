# Sub-exp 03 — cap K + cap iter (resultado)

## Benchmark

| variant | cap_K | cap_iter | D1-D9 bytes | diff | li5k bytes | loss | encode | speedup | RT |
|---|---|---|---:|---:|---:|---:|---:|---:|---|
| v0 | - | - | 1,615 | +0 | 498,271 | +0.00% | 37.17s | 1.00x | OK |
| v3-K8 | 8 | - | 1,615 | +0 | 498,271 | +0.00% | 38.93s | 0.95x | OK |
| v3-K6 | 6 | - | 1,615 | +0 | 498,271 | +0.00% | 39.02s | 0.95x | OK |
| v3-K4 | 4 | - | 1,615 | +0 | 498,543 | +0.05% | 33.54s | 1.11x | OK |
| v4-i50 | - | 50 | 1,615 | +0 | 515,389 | +3.44% | 27.18s | 1.37x | OK |
| v4-i30 | - | 30 | 1,615 | +0 | 526,051 | +5.58% | 21.67s | 1.71x | OK |
| v5-K6-i50 | 6 | 50 | 1,615 | +0 | 515,389 | +3.44% | 25.78s | 1.44x | OK |
| v5-K8-i50 | 8 | 50 | 1,615 | +0 | 515,389 | +3.44% | 26.77s | 1.39x | OK |

## Analise

### Achados-chave

1. **Cap K (4/6/8) tem efeito quase nulo**: K=6, K=8 ate' PIORARAM
   tempo (overhead do check). K=4 deu 1.11x com +0.05% loss.
   - **Interpretacao**: subs picked tipicamente sao K=2-3. Caps maiores
     nao filtram efetivamente. K=4 corta apenas raramente.
2. **Cap iter (50/30) traz ganho real MAS COM BYTE LOSS significativo**:
   - i=50: 1.37x speed / **+3.44% bytes**
   - i=30: 1.71x speed / **+5.58% bytes**
   - Cada iter outer adicional traz compressao real
3. **Combinado v5-K6-i50**: bytes = v4-i50 (K=6 nao adicionou loss)
   mas levemente mais rapido (25.8s vs 27.2s)
4. **D1-D9 nunca afetado** (1615 preservado em TODAS variantes) —
   datasets pequenos nao batem caps

### Conclusao

**Nao ha' variante zero-risk com speedup significativo** em HCC.
Caminhos possiveis:

| Caminho | Speedup | Byte loss | Risco welding |
|---|---|---|---|
| Welding v1+v2 (sub-exp 02) | 1.04x | 0% | baixo |
| Welding v4-i50 (cap iter=50) | 1.37x | +3.44% real-world | viola regra invariante |
| Implementar counter incremental (H-PERF-05d) | desconhecido (potencial alto) | 0% | complexidade alta |
| Nao weldar agora, adiar HCC opt | — | — | zero (mantem canonical) |

### Recomendacao

**Opcao A — minimal welding**: weld v1+v2 (1.04x, zero risk). Ganho
marginal mas "clean". H-PERF-05d (incremental counter) abre como
sub-pacote futuro.

**Opcao B (recomendada) — adiar inteiro**: nao weld HCC. Pacote 4
fecha com OBAT (ADR-0009, 2.70x em 20k, alpha 1.42) como ganho
principal. HCC opt fica como hipoteses abertas pra phase 3.

**Opcao C — flag de compression_level**: adicionar parametro
`max_iter` na API publica permitindo trade-off explicito (default=99
preserva canonical, valores menores = faster/maior).

**Recomendacao final: B** — ganho de 1.04x nao justifica modificar
`src/tcf/composicional/syntax.py` (ja' modificado por ADR-0006 e
ADR-0007; risco de regressao em re-validacao multi-camada). Documentar
achados, fechar Pacote 4 com OBAT como sucesso principal.
