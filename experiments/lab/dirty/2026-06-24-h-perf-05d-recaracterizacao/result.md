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

## MEDIÇÃO REAL (incremental_v2.py, 2026-06-24) — corrige o ceiling estimado

Construído um incremental fiel ao código ATUAL (Counter delta + `alias_first_line` incremental +
`sub_first_line` lazy), monkey-patch read-only, medido vs canonical:

| coluna (5k) | canonical | incremental | **speedup** | Δbytes | RT |
|---|---|---|---|---|---|
| l_comment (free-text) | 6,07s / 133426B | 3,53s | **1,72×** | +0 (0,00%) | OK |
| l_shipdate (datetime) | 4,04s | 3,33s | 1,21× | +19 (+0,05%) | OK |
| l_commitdate (datetime) | 3,96s | 3,02s | 1,31× | +12 (+0,03%) | OK |

(1k: ~1,6× em todas; divergência ~0.)

**CORREÇÃO do ceiling**: o speedup REAL é **~1,2–1,7×**, NÃO os ~4–5× estimados acima. O erro da
estimativa: confundir "`_detect_compositions` = 92% do encode" com "rebuild = 92%". O rebuild do
Counter é **~46% do encode** (bate com o profile antigo); removê-lo dá ~1,7×. O **loop de candidatos
sobre o `Counter`** (iterar todas as keys + prune + `_estimate_baseline_chars`) e a **substituição**
NÃO são removidos pelo incremental → limitam o ganho. Maior em free-text (1,72×), menor em datetime
(1,2–1,3×, mais empates/candidatos).

**Divergência REAL (M11)**: +0,03–0,05% só em datetime (l_comment free-text byte-idêntico), RT 100%.
Consistente com o lab antigo (+62B distribuído em colunas datetime).

**Caveat Cython** (reforço): tudo no caminho pure-Python (ativo aqui). Com `_core/detect.pyx`
compilado, `_detect_compositions` já roda nativo (~2,67×) e o incremental só ajudaria via port
Cython-incremental. O ~1,7× é pure-Python.

**Veredito honesto**: ganho **modesto** (~1,5× pure-Python, diluído em tabela multi-col) por
**+0,03–0,05% bytes em datetime** + complexidade de weld (state entre iters) + re-pin M11. A decisão
de weld (b) deve ser re-pesada com ESTES números medidos, não com o ceiling otimista.

## Conexões
- Lab original (fechado): [`old/refuted/2026-05-22-h-perf-05d-counter-incremental/`](../old/refuted/2026-05-22-h-perf-05d-counter-incremental/).
- Ticket: [T-EXP-H-PERF-05d](../../../../tickets/T-EXP-H-PERF-05d.md) (closed-with-byte-divergence).
- Versão (re-pin permitido): [ADR-0028](../../../../docs/adr/0028-pre-1.0-versioning-minor-format-coupling-release-cadence.md).
- `_detect_compositions`: [`src/tcf/composicional/syntax.py`](../../../../src/tcf/composicional/syntax.py) L231.
