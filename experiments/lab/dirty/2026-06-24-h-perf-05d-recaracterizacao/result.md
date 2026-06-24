# H-PERF-05d — re-caracterização (2026-06-24) [probatório]

**Read-only** (`src/tcf` intocado). Decisão do owner: caracterizar antes de weldar. Continua o lab
fechado [`old/refuted/2026-05-22-h-perf-05d-counter-incremental/`](../old/refuted/2026-05-22-h-perf-05d-counter-incremental/)
(NÃO modificado), agora contra o código ATUAL (que ganhou prune ADR-0019 + Cython depois daquele lab).

## Pergunta

O counter-incremental ainda vale, dado que o prune (ADR-0019) já acelerou o `_detect_compositions`?

## Profile fresco (lineitem `l_comment`, 5000 linhas, pure-Python — Cython não compilado aqui)

`profile_current.py`. encode wall = **5,825s** (min de 3); bytes=133426; 4987 distintos/5000.

cProfile (tottime, top):

| função | tottime | nota |
|---|---|---|
| `_detect_compositions` | **9,42s** (cumtime 12,33 / total 13,38 = **~92% do encode**) | o loop |
| `builtins.len` (6,5M calls) | 1,32s | enumeração de sub-tuplas (rebuild) |
| `list.append` (3,28M) | 0,98s | rebuild |
| `_estimate_baseline_chars` | **0,38s (~3% do _dc)** | candidato-eval — **prune já minimizou** |
| `Counter.__missing__` (975k) | 0,15s | rebuild do Counter |

## Leitura

- **O prune (ADR-0019) já cortou a parte de candidatos** (`_estimate_baseline_chars` = ~3% do `_dc`).
  Sobrou o **rebuild do `Counter`** (re-enumeração de TODAS as sub-tuplas de TODAS as linhas a cada
  iter) como **quase todo o custo** do `_detect_compositions`. No lab antigo (pré-prune) o rebuild era
  46,5% do `_dc`; **pós-prune é a fração dominante**.
- O rebuild roda **99 iters × ~5000 linhas**; só **~16 linhas/iter (0,3%)** mudam (medido no lab
  antigo). O incremental-counter mantém o `Counter` entre iters e aplica delta só nas linhas alteradas
  → a re-enumeração cai de ~99×5000 pra ~5000 + 99×16 (**~75× menos trabalho de enumeração**).
- **Ceiling estimado**: como o rebuild é ~o `_dc` inteiro e o `_dc` é ~92% do encode, o encode desta
  coluna poderia cair de ~5,8s pra ~1–1,5s (**~4–5×**). É **estimativa** (ceiling), não medição de uma
  impl incremental fiel ao código atual — essa impl é a etapa de weld (ver decisão).
- **Caveat Cython**: este ganho é no **caminho pure-Python** (ativo aqui — Cython não compilado). Com
  o `_core/detect.pyx` compilado, `_detect_compositions` já roda nativo. O incremental é **algoritmo**
  (language-agnostic) → ajudaria o fallback agora + um futuro port Cython-incremental. Não substitui o
  Cython; compõe.

## Divergência byte (do lab antigo — a re-validar na impl atual)

Lab 2026-05-22, `IncrementalSyntax` vs canonical: **37/41 byte-IDÊNTICO**. As **4 divergências** foram
todas em colunas **datetime** TPC-H: net **+62 bytes em ~80kB (0,08%)**. **`l_comment` (free-text) era
byte-IDÊNTICO.** Causa: ordem de iteração do `Counter` muda o tie-break quando 2+ candidatos têm o
mesmo `net` (muitos empates em datetime). Mecanismo entendido; persiste no código atual (o prune
preserva a ordem do Counter, então a divergência é a mesma família).

## Decisão (a) vs (b) — para o owner

| caminho | o quê | custo | bytes |
|---|---|---|---|
| **(a) fix byte-canonical** | incremental + reordenação posicional pra empatar a ordem do 2-pass | alto (a parte que o lab antigo não fechou) | M10 intacto (0 divergência) |
| **(b) aceitar M11 re-pin** | incremental as-is; aceitar +0,08% em datetime como geração M11 | baixo | +62B/0,08% (datetime); re-pin de baseline |

**(b) ficou viável agora** (ADR-0024/0028: baselines re-pináveis; M10→M11 é eixo-B, geração interna).
Troca **~4–5× no encode (pure-Python)** por **+0,08% bytes só em datetime** (free-text intacto).

**Próximo passo (após escolha a/b)** = implementar o incremental fiel ao `_detect_compositions` ATUAL
(com prune) num fork do lab, medir o speedup REAL + re-validar a divergência, e só então weld em
`src/tcf` sob aprovação + GATE real-world. A caracterização (este doc) informa a escolha; o speedup é
estimativa até a impl.

## Conexões
- Lab original (fechado): [`old/refuted/2026-05-22-h-perf-05d-counter-incremental/`](../old/refuted/2026-05-22-h-perf-05d-counter-incremental/).
- Ticket: [T-EXP-H-PERF-05d](../../../../tickets/T-EXP-H-PERF-05d.md) (closed-with-byte-divergence).
- Versão (re-pin permitido): [ADR-0028](../../../../docs/adr/0028-pre-1.0-versioning-minor-format-coupling-release-cadence.md).
- `_detect_compositions`: [`src/tcf/composicional/syntax.py`](../../../../src/tcf/composicional/syntax.py) L231.
