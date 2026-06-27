---
title: T-CI-3 — Gate byte-canonical do caminho Cython COMPILADO (detect.pyx)
status: in-progress
priority: P2
created: 2026-06-24
updated: 2026-06-25
related:
  - docs/adr/0020-cython-optional-accelerator.md
  - tests/test_pyx_byte_equivalence.py
  - src/tcf/_core/detect.pyx
  - src/tcf/composicional/syntax.py
  - experiments/lab/dirty/2026-06-25-tci3-pyx-gate/
---

## Andamento (2026-06-25)

**GATE LOCAL FEITO.** `tests/test_pyx_byte_equivalence.py`: compara Cython (.pyd) vs
pure-Python no MESMO processo (enabler `M8AVirtualRefsSyntax._detect_compositions_py`
salvo em syntax.py antes do override) — sinteticos + real-world (datasets/samples) +
aleatorios. **Skip gracioso se accel=False** (so' roda onde a extensao compilou). Provado
neste ambiente (Cython 3.2.5 + MSVC): 42 checks passam com accel=True; 0-diff direto em
31 datasets. Inspecao: `experiments/lab/dirty/2026-06-25-tci3-pyx-gate/`.

**FALTA (follow-up)**: job de CI que COMPILE a extensao e rode este teste com accel=True
(matrix). Sem isso, o gate so' roda onde alguem compilou local. Atualizar ADR-0020 que a
byte-equivalencia passa a ser VERIFICADA por teste (nao so' convencao).

# T-CI-3 — Gate byte-canonical do caminho Cython compilado

## Contexto

Achado durante a caracterização do P4 (foco-2, workflow read-only, 2026-06-24):
**nenhum teste da suíte exercita o `detect.pyx` COMPILADO**. O ambiente de dev
roda `accel=False` (o monkeypatch `syntax.py:709-714` só troca
`_detect_compositions` quando `tcf._core.detect` importa com sucesso; sem `.pyd`
compilado, fica o fallback pure-Python). Grep em `tests/` por
`accelerated|detect_cy|_core|pyd|cython` → **0 hits**; `conftest.py` não tem
fixture que force `_detect_compositions_accelerated=True`.

**Tensão com ADR-0020**: o ADR exige que `_core/detect.pyx` e o fallback
pure-Python permaneçam **byte-equivalentes** ("mudança num exige a no outro").
Mas a suíte só valida o caminho pure-Python. Consequência: um espelho `.pyx`
incorreto (ou byte-divergente) passa TODOS os gates locais e quebraria
silenciosamente onde a extensão estiver compilada (wheel publicado, máquina com
toolchain C).

O `.pyx` já diverge **textualmente** do `.py` (cdef typed locals; renames de
escopo `x→y`, `i→j`, `a→ai`; `len()` hoistado em `n_refs`) — o critério é
byte-equivalência de OUTPUT, não igualdade de texto. Hoje isso só é verificável
por inspeção manual lado-a-lado, que erra em detalhe de prune/tie-break.

## Por que P2 (não bloqueia agora)

- O detector está estável (intocado desde o weld ADR-0019/0020); o risco é de
  REGRESSÃO futura, não de bug atual.
- A Onda 1 do P4 é EMIT-only e **não toca o detector nem o `.pyx`** — segue sem
  depender deste ticket.
- Vira bloqueante SE/QUANDO algum trabalho mexer em `_detect_compositions` ou
  `_estimate_baseline_chars` (ex: P4-S1/S8, deixados fora da Onda 1 justamente
  por isso).

## Dimensão de distribuição (diretriz owner, 2026-06-24)

O owner lembrou: **quando for feita a distribuição, a compilação Cython tem que
funcionar de fato — a otimização não pode ser só do ambiente de dev.** Hoje o
build hook (`hatch_build.py`) é best-effort e cai pra pure-Python **em silêncio**
se faltar compilador. Consequência: um usuário que faça `pip install tcf-format`
numa máquina sem toolchain C pega o caminho LENTO sem saber.

Isto é o **outro lado** deste ticket: além de *testar* a byte-equivalência do
caminho compilado (critério abaixo), é preciso *garantir que o caminho compilado
chegue ao usuário*. Opções a avaliar (na hora da distribuição, não agora):
- **Wheels pré-compilados por plataforma** (cibuildwheel) — o usuário baixa um
  `.whl` já com a extensão, sem precisar de compilador. É o caminho usual pra
  libs com C/Cython.
- Manter o fallback pure-Python como rede (máquinas exóticas), mas **sinalizar**
  (warning/log opt-in ou flag introspectável) quando o acelerador não está ativo,
  pra não ser otimização-fantasma.
- Decidir a política no momento do release (liga com a cadência de versão
  ADR-0028 / [T-DIST-RELEASE-0.8.0]). **"Vemos isso depois"** — registrado aqui
  pra não perder.

## Critério de aceite

1. Um caminho de teste que: (a) compile o `detect.pyx` (Cython + compilador C,
   via `hatch_build.py` ou direto); (b) confirme
   `M8AVirtualRefsSyntax._detect_compositions_accelerated is True`; (c) rode
   `tests/test_regression_v1_baseline.py` + `tests/test_real_world_snapshots.py`
   com o `.pyd` presente → mesmos **D1-D9=1523B, real-world=89616B**.
2. Idealmente no CI (matrix), marcado pra rodar só onde a extensão compila
   (skip gracioso se toolchain ausente — espelha a filosofia best-effort do
   build hook, ADR-0020).
3. Documentar no ADR-0020 (ou addendum) que a byte-equivalência passa a ser
   **verificada por teste**, não só por convenção.

## Notas

- Alternativa de baixo custo: um teste que, quando a extensão estiver disponível,
  rode encode pelos DOIS caminhos (`accelerated True` vs `False`) sobre os
  mesmos inputs e compare bytes diretamente — não precisa pinar baseline, só
  igualdade `.py == .pyx`.
- Caracterização completa do contexto (P4): [`p4-detect-emit-caracterizacao.md`](../experiments/lab/dirty/notas/p4-detect-emit-caracterizacao.md).
