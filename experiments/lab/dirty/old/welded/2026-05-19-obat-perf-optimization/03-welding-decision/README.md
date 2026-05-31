# Sub-exp 03 — welding decision (v3 → src/tcf)

**Objetivo**: validar v3 no pipeline COMPLETO (encode/decode end-to-end)
em D1-D9 + reals, garantir byte-canonical preservado, depois weldir
em `src/tcf/core/online.py`.

## Plano

1. **Validacao isolada** (`validate.py` com monkey-patch):
   - D1-D9: total deve ser exatamente **1615 bytes** (M9 invariante)
   - lineitem 5000: bytes IDENTICOS ao baseline EXP-014 (498,271)
   - Tempo: esperar ~14s (vs 71s baseline)
2. **Welding** (se 1 passar): editar `src/tcf/core/online.py` em
   place, manter API publica e codigo bem comentado
3. **Re-validacao post-welding**:
   - EXP-007 re-run → 1615B preservado
   - EXP-010 re-run → 20/20 RT OK
   - EXP-011 re-run → RT OK
   - EXP-012 re-run → 4/4 RT OK
   - EXP-013 re-run → 8/8 RT OK
4. **Re-run EXP-014** → caracterizar novo alpha (esperado <1.5)
5. **ADR-0009** documentando

## Restricoes

- src/tcf intocado ate validacao isolada 100% OK
- Welding so' apos confirmar byte-canonical preservado
- Re-validacao multi-camada apos welding
- Rollback trivial via git se algo quebrar

## Aceite

- D1-D9 = 1615B exato
- lineitem 5k bytes = baseline
- Encode lineitem 5k <30s (vs 71s)
- Re-validacao multi-camada: zero regressao
- ADR-0009 accepted
