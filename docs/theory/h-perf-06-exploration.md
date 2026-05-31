# H-PERF-06 — Estudo do nucleo compilado (Cython/Rust/etc)

> **Doc de estudo** (gerado 2026-05-27 via workflow 5 dimensoes: profile real,
> opcoes de compilacao, API surface, build/packaging, prototype empirico).
> **Achado critico**: a hipotese H-PERF-06 como originalmente registrada
> (compilar lcp/lcs) e' DESCONFIRMADA por profiling real. Real bottleneck e'
> HCC `_detect_compositions`. Status: **REFRAMED** (alvo certo identificado,
> evidencia empirica).

## TL;DR

| Pergunta | Resposta empirica |
|---|---|
| Cython funciona localmente? | **SIM** — 6.23x speedup em lcp_len isolado (microbench) |
| Tool right pra TCF? | **Cython** (Tier 1) vs Rust+maturin (Tier 2) |
| Devo compilar lcp/lcs como H-PERF-06 propos? | **NAO** — Amdahl blocked (lcp/lcs = 1.8% do tempo real) |
| Qual o real bottleneck? | HCC `_detect_compositions` em syntax.py:246-251 (88% / 17s de 19s em 20k retail) |
| Qual o alvo certo? | (a) algoritmico: prune O(L^2) tuple enum + early termination. (b) Cython em `_detect_compositions` inner loop |
| Cabe em v1.x (sem reabrir freeze)? | **SIM** — interno, nao muda formato. Pure-Python fallback obrigatorio |

## Por que a hipotese original estava errada

H-PERF-06 foi registrada citando "29M chamadas a lcp_len/lcs_len, ~1.7us cada,
estimativa 50%+ speedup". Numero original vinha de profile em lineitem 5k via
META-PERF-PHASE2.md.

Profile NOVO (workflow agente, 2026-05-27) em online-retail 20k rows / 8 cols:

| Funcao | Cumulative time | % total | Chamadas |
|---|---|---|---|
| `_detect_compositions` (HCC) | **17.06s** | **88%** | iterativo |
| `_estimate_baseline_chars` (HCC helper) | 1.86s | 9.6% | 291.183 |
| `len()` (builtin) | 1.91s | 9.9% | — |
| `list.append()` (builtin) | 1.18s | 6.1% | — |
| `lcp_len_capped` | **0.097s** | **0.4%** | 111.516 @ 0.87us |
| `lcs_len_capped` | **0.058s** | **0.3%** | 51.935 @ 1.14us |

**lcp/lcs juntas: 1.8% do tempo**. Amdahl: 5x speedup nelas → 1.018x total.

A inflacao "29M calls" provavelmente veio de:
- Dataset diferente (lineitem 5k tem 16 cols, varias com strings longas)
- ADR-0009 (trigrama hash, welded 2026-05-19) ja reduziu chamadas redundantes
- ADR-0010/11 (auto-min_len + delta-aware) reduziram trabalho de OBAT em muitos casos

## O real bottleneck — HCC `_detect_compositions`

Lines 246-251 de [composicional/syntax.py](../../src/tcf/composicional/syntax.py):
gera **todas** as sub-tuplas O(L^2) candidatas por iteracao, em loop com
Counter.update. Com 8 cols x 20k rows + ~1-3 refs por celula, conta gigante.

Pseudocodigo simplificado:
```
for col:
  for line in cells:
    for a, b in pairs(refs, k=range(L^2)):
      sub = tuple(refs[a:b])   # O(L) por tuple, alloc
      counter[sub] += 1         # hash + update
```

**3 estrategias possiveis** (em ordem de ROI):

1. **Algoritmica (alta)**: prune sub-tuplas antes da Counter
   - Filtrar por min length (so' tuplas K>=3)
   - Early termination se ganho < threshold
   - Skip iteracoes apos N rounds sem progresso
   - Estimativa: 2-3x overall, sem compilar nada
   - Risco: pode mudar bytes (cobertura HCC diferente) → quebra freeze v1.0

2. **Cython no inner loop (media)**: compilar `_detect_compositions` em .pyx
   - tuple() alloc fica C-level (mais rapido)
   - Counter pode virar dict cdef
   - Estimativa: 2x na funcao, 1.5-2x overall
   - Format-safe (mesmo output)

3. **V2-J streaming (futuro)**: bypassar HCC iterativo batch
   - Streaming nao precisa convergir composicoes globalmente
   - Detecta on-the-fly com janela
   - Naturalmente resolve HCC bottleneck, mas e' v2.0 (format change)

## Tools de compilacao — comparacao

Workflow avaliou 10 opcoes, ranking pra TCF:

| Tool | Status local | Speedup esperado | Build complex | Recomendacao |
|---|---|---|---|---|
| **Cython** | INSTALADO + MSVC 14.50 | **6.23x medido (lcp_len)** | Baixo (hatch-cython) | **TIER 1** |
| Rust + maturin/PyO3 | Cargo disponivel | 50-100x (overkill) | Alto | TIER 2 (se Cython insuficiente) |
| Numba | nao instalado | 10-20x JIT | Medio (JIT overhead) | dev local apenas |
| mypyc | nao instalado | 2-5x (preserva .py source) | Medio | elegante mas imaturo |
| cffi + C | nao instalado | 20-40x | Manual | overkill pra TCF |
| Pythran | nao instalado | 5-10x | Medio (INRIA) | menor adocao |
| torch.jit | overkill | n/a (tensors) | — | rejeitado |
| Mojo | nao no pip | — | — | rejeitado (imaturo) |
| PyPy | alt interpreter | 3-5x sem mudar codigo | — | nao e' "extension" |
| C extension manual | toolchain | 30-50x | Muito alto | rejeitado |

**Cython vence** pra TCF: mature, low friction, integra com hatchling
(via hatch-cython), pure-Python fallback simples, multi-platform via cibuildwheel.

## Prototipo empirico — lcp_len em Cython

Codigo (proto_lcp_cython.pyx):
```cython
cdef int lcp_len_c(str a, str b):
    cdef int n = min(len(a), len(b))
    cdef int i = 0
    while i < n and a[i] == b[i]:
        i += 1
    return i

def lcp_len(str a, str b):
    return lcp_len_c(a, b)
```

Benchmark (1000 pares 5-25 chars, 50% overlap, 10000 iter cada):
- Pure Python: 0.933 us/call
- Cython: 0.150 us/call
- **Speedup: 6.23x** (excede target 50% original)

Mas **na pipeline real isso e' 1.018x** por Amdahl. **Microbench valida o tool;
nao valida o alvo**.

## API surface — o que compilar

Workflow avaliou 3 niveis:

| Nivel | Funcoes | LOC | Speedup estimado |
|---|---|---|---|
| Minimo | lcp_len, lcs_len | ~20 | 6.23x microbench / **1.018x overall** ← descartar |
| Medio | + _melhor_pref/suf, trigram lookup | ~70 | 3-5x funcao / **~1.1x overall** ← marginal |
| Maximo | processar() inteiro | ~225 | 5-10x funcao / **~1.3x overall** + esforco grande |
| **NOVO ALVO** | _detect_compositions + _estimate_baseline_chars | ~140 | **2x funcao / ~1.5-2x overall** **FORMAT-SAFE** |

O alvo "novo" (_detect_compositions) e' o que faz sentido apos o profile.

## Build/packaging — design recomendado

**pyproject.toml** com hatch-cython:
```toml
[build-system]
requires = ["hatchling", "hatch-cython"]
build-backend = "hatchling.build"

[tool.hatch.build.hooks.cython]
src = "src/tcf/_core"
include_numpy = false
```

**Pure-Python fallback** (importante pra usuarios sem build):
```python
# src/tcf/core/online.py
try:
    from tcf._core import lcp_len, lcs_len  # compiled
except ImportError:
    def lcp_len(a: str, b: str) -> int:
        n = min(len(a), len(b)); i = 0
        while i < n and a[i] == b[i]: i += 1
        return i
    # ... idem lcs_len
```

**CI matrix** (cibuildwheel): Linux x86_64+arm64 / macOS arm64+x86_64 / Windows x86_64
x Python 3.10-3.13 = 16 wheels por release.

## Riscos identificados

1. **Amdahl blindness**: insistir em compilar lcp/lcs apesar do profile
   contradizer. Workflow ja' alertou.
2. **Build em Windows**: MSVC funcionou no dev (verificado), mas usuarios
   precisam VS Build Tools. Pure-Python fallback obrigatorio.
3. **Algorithmic fix vs Cython fix**: prune `_detect_compositions` pode
   mudar bytes (cobertura HCC). Format-safety exige byte-canonical exato
   D1-D9 = 1523B e D17a = 322B.
4. **Iteration count growing**: HCC e' iterativo ate' convergencia. Limit
   N iterations (proposed) afeta cobertura.
5. **Python version locking**: .pyd Win + .so Linux compilados por versao.
   3.13 → recompilar em 3.14.

## Recomendacao consolidada

**NAO atacar lcp/lcs como H-PERF-06 originalmente propos.** Amdahl mata.

**Atacar HCC `_detect_compositions` em 3 fases**:

1. **Fase A (algoritmica, alto ROI)**: prune sub-tuplas + early termination,
   medindo byte-canonical preservation. Estimativa 2-3x overall, sem
   ferramenta nova. Fork dirty lab obrigatorio antes de welding (mesmo
   protocolo Patricia).
2. **Fase B (Cython, ortogonal)**: compilar `_detect_compositions` loop +
   `_estimate_baseline_chars` em .pyx. Estimativa 1.5-2x overall apos Fase A.
   Format-safe garantido.
3. **Fase C (v2.0, futuro)**: V2-J streaming bypassa HCC iterativo
   completamente (online detection). Naturalmente resolve, mas exige
   format change.

**lcp/lcs Cython como spike investment**: feito o prototipo (6.23x), valida
ferramenta. Pode ficar em backlog "low-priority polish" — apos compilar
HCC, lcp/lcs ja' otimizadas seriam bonus +0.5%.

## Status e proximos passos

- **H-PERF-06 original**: status `refutada-real-world` (alvo lcp/lcs
  Amdahl-blocked).
- **H-PERF-06-v2 Fase A**: status `welded` (2026-05-31, ADR-0019).
  Candidato #15 (cheap upper-bound prune + running-max inline) weldado em
  `_detect_compositions`. Byte-canonical preservado (suite 269 verdes +
  gate real-world); `_estimate_baseline_chars` 87% menos chamadas; speedup
  1.22-1.35x. Lab: `experiments/lab/dirty/2026-05-27-h-perf-06-v2-fase-a`
  (geracao) + `2026-05-31-regression-real-world` (gate + re-validacao).
- **H-PERF-06-v2 Fase B (Cython)**: `aberta`. Alvo `_detect_compositions`
  + `_estimate_baseline_chars` pra romper o teto Amdahl puro-Python (~1.8x).
- **Cython infrastructure**: estabelecida (Cython 3.0+ + MSVC funciona;
  hatch-cython integra com pyproject atual; pure-Python fallback design
  conhecido). Reutilizavel pra Patricia (V2-C) e _detect_compositions
  (H-PERF-06-v2) quando priorizadas.

## Conexoes

- [ADR-0018](../adr/0018-v2-format-roadmap.md) V2-J streaming naturalmente
  bypassa HCC bottleneck — alternativa estrutural a otimizar batch atual.
- [docs/theory/strategies-map.md](strategies-map.md) — mapa completo das
  estrategias (HCC detector e' subsistema 3).
- [docs/theory/patricia-trie-exploration.md](patricia-trie-exploration.md) —
  outro estudo, ortogonal (indice OBAT, nao HCC).
