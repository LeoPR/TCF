# H-PERF-06-v2 Fase B — porte Cython de _detect_compositions

> **WELDED 2026-05-31 (ADR-0020)** como acelerador OPCIONAL. Prototype deste
> lab portado p/ `src/tcf/_core/detect.pyx` + fallback pure-Python silencioso
> em `composicional/syntax.py` + hook de build best-effort. Owner escolheu
> "acelerador opcional + fallback silencioso". src/tcf intocado além do
> acelerador (com aprovação).

## Re-profile pós-weld (decisivo) — `00-reprofile-postweld/`

O weld #15 mudou o profile. Re-medido (online-retail 20k×8col, cProfile):

| Função | tottime | % | obs |
|---|---|---|---|
| `_detect_compositions` (corpo) | 9.53s | **64.5%** | hotspot real |
| `len()` builtin | 1.40s | 9.4% | 7.2M chamadas (de dentro do detect) |
| `list.append` | 1.04s | 7.0% | 3.6M chamadas |
| `_estimate_baseline_chars` | **0.21s** | 1.4% | **morto** (era 3.59s pré-weld) |

Conclusão: `_estimate_baseline_chars` deixou de ser alvo (o #15 cortou 87%
das chamadas). O alvo é o **corpo do `_detect_compositions`** (loops de
enumeração de sub-tuplas, Counter, substituição) + os `len()`/`append()`
que disparam de dentro dele.

## Porte Cython — `01-cython-detect/`

Estratégia byte-safe por construção: lógica IDÊNTICA ao
`src/tcf/composicional/syntax.py` (pós-weld), **todas as estruturas
continuam Python** (Counter/dict/tuple/list → ordem de inserção e
tie-break first-wins preservados). Só adiciona:
- `cdef Py_ssize_t` em contadores e comprimentos
- `cdef list` nas listas quentes (refs/new_refs/novos)
- genexprs renomeadas (j/y) p/ evitar clash de escopo com os cdef

Build: Cython 3.2.5 + MSVC 14.50, Python 3.13 (`python setup.py build_ext
--inplace`).

## Resultados — `validate_bench.py` / `full_bench.py`

**Byte-canonical: PASS** (Cython produz output byte-idêntico):
- D1-D9 = 1523B, D17a = 322B
- 3 fixtures real-world: 27581B / 11437B / 50598B (todas exatas, RT OK)

**Speedup** (tempo real, sem cProfile):

| Workload | Python-welded | Cython | speedup |
|---|---|---|---|
| Description 8k (detect-dominado) | 1.588s | 0.687s | **2.31×** |
| encode completo 20k×8col | 6.43s | 2.99s | **2.15×** |
| (referência vs pré-weld total) | 7.99s | 2.99s | 2.67× |

Rompe o teto Amdahl puro-Python (~1.8×) como esperado, sem mudar bytes.

## Pendente — decisão de packaging (weld)

O porte funciona e é byte-safe, mas weldar em `src/tcf` exige decisão de
distribuição (lib v1.x sob freeze ADR-0017):

1. **Pure-Python fallback obrigatório**: `try: from tcf._core import
   _detect_compositions; except ImportError: <pure-python>`. `pip install`
   sem compilador deve continuar funcionando idêntico (só mais lento).
2. **Build system**: hatch-cython ou setuptools no pyproject; opcional vs
   obrigatório.
3. **Wheels multi-plataforma**: cibuildwheel (Linux/macOS/Windows ×
   Python 3.10-3.13) — manutenção de release.
4. **Onde vive**: `src/tcf/_core/detect.pyx` (+ a versão Python como
   fallback no mesmo módulo).
5. **Filosofia**: alinhado a ADR-0018 (core compilado é interno; output
   permanece textual). Não compete com gzip — só acelera.

Recomendação: weld com fallback puro-Python como **acelerador opcional**
(extra `pip install tcf[fast]` OU build best-effort com fallback
silencioso), preservando install puro-Python por padrão. Decisão do owner.

## Arquivos

- `00-reprofile-postweld/reprofile.py` — re-profile pós-weld
- `01-cython-detect/detect_cy.pyx` — porte Cython (fonte)
- `01-cython-detect/setup.py` — build
- `01-cython-detect/validate_bench.py` — gate byte-canonical + speedup coluna
- `01-cython-detect/full_bench.py` — speedup overall encode completo
