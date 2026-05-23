# Sub-exp 02 — prototype counter incremental + byte-canonical

## Implementacao

`IncrementalSyntax(M8AVirtualRefsSyntax)`:
- Counter mantido entre iters (delta apply pos-substituicao)
- sub_first_line + alias_first_line rebuilt full a cada iter
  (simplifica edge cases sem perder muito ganho)

## Validacao byte-canonical

37/41 datasets/colunas MATCH exato. 4 divergencias:

| Source | Col | n_rows | canonical | incremental | delta |
|---|---|---:|---:|---:|---:|
| lineitem-1k | l_commitdate | 1000 | 8,635 | 8,634 | **-1** |
| lineitem-5k | l_shipdate | 5000 | 36,201 | 36,233 | **+32** |
| lineitem-5k | l_commitdate | 5000 | 35,779 | 35,787 | **+8** |
| lineitem-5k | l_receiptdate | 5000 | 36,139 | 36,162 | **+23** |

**Net divergencia**: +62 bytes (sobre ~80kB nessas 4 colunas) = ~0.08%.

## Diagnostico

Divergencia concentrada em colunas DATETIME (l_shipdate/commitdate/
receiptdate) onde:
- 99 iters cap (worst-case)
- Many substitutions (subs com virtual_id criadas dinamicamente)
- Ordem de iteracao do Counter incremental difere do canonical
  rebuild — novas subs entram NO FINAL do dict em vez de na posicao
  original

Pick best (`if net > best_net`) tem tie-break = primeiro inserido.
Quando 2 candidatos tem mesmo net, ordem importa.

Counter incremental: novas subs (criadas via delta) entram no fim.
Canonical rebuild: novas subs entram na ordem em que aparecem nas
linhas (potencialmente no meio).

Em colunas com muitos iters + muitos empates, divergencia acumula.

## Tentativas de fix

1. ✗ Manter keys mesmo com count=0 (preserva ordem inicial). Nao
   resolveu — novas subs ainda entram no fim.
2. ✗ Simplificar mantendo so' Counter incremental (sub_first_line
   rebuild). Nao resolveu — bug nao era em sub_first_line.

## Decisao

**Fase 2 encerrada como "validated-with-byte-divergence"**.

Counter incremental e' viavel estruturalmente (RT 100% provavel, nao
medido) mas **NAO byte-canonical** com M10 atual.

Welding canonical requereria:
- (a) FIX byte-canonical: garantir mesma ordem de iteracao do Counter
  como rebuild faria. Complexidade alta — talvez requeira reinsert
  ordering custom.
- (b) Aceitar como M11 baseline (divergencia minima 0.08%): mas
  invariant M10 quebrado.

Ambos sao decisoes maiores. Adiar como candidato futuro.

## Fase 3 nao executada

Medir speedup real (Fase 3) so' faria sentido se Fase 2 fosse byte-
canonical. Sem isso, comparacao perde valor.

Profile teorico (Fase 1) ja' mostra ganho POTENCIAL ~10-20% em encode
TPC-H 5k. Welding traria ganho real, mas trade-off complexidade-vs-
ganho desfavoravel sem fix byte-canonical.

## Recomendacoes

1. **Adiar T-EXP-H-PERF-05d** pra phase 3 dedicada com:
   - Fix byte-canonical (ordering custom)
   - OU aceitacao M11 (com ADR-0012 nova baseline)
2. **Considerar alternativas**:
   - Cython/Rust port `_detect_compositions` (H-PERF-06, ja' adiado)
   - Otimizacao build_candidates (28% do _dc, segunda maior secao)
3. **Pacote 4 fica fechado-parcial**: OBAT (ADR-0009) e' o win principal
   ja' welded. HCC perf ganhos adicionais sao marginais sem refactor
   maior.
