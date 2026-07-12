---
title: T-CODE-CORE-CONSOLIDATE — simplificar o core: fonte única de lógica, menos funções, naming HCC (adeus M8A)
status: open
priority: P1
created: 2026-07-12
updated: 2026-07-12
blocked-by: []
related:
  - tickets/T-REL-08-CLOSEOUT.md
  - tickets/T-QA-8-material-comprobatorio.md
  - src/tcf/composicional/syntax.py
  - src/tcf/composicional/hcc_seqrle.py
  - docs/adr/0020-cython-optional-accelerator.md
---

# T-CODE-CORE-CONSOLIDATE — o core precisa encolher pra avançar

**[dispositivo→registro]** Diretriz do owner (2026-07-12): o código do core está "muito espalhado,
mesmo que funcional — preciso refazer". Exemplo dado: **o mesmo tratamento do BUG-14 no decode em
duas partes** (hcc_seqrle e syntax) — "isso aumenta absurdamente a chance de problemas de
sincronismo de lógica de negócios" — além do número grande de funções; e o **M8A era nome de
PROTÓTIPO** (a tecnologia foi fixada, mas o nome vivo é HCC) — o código ainda carrega o codinome.
"Precisamos simplificar o código para poder avançar mais."

## Inventário medido (2026-07-12)

### Duplicações de lógica de negócio (CONFIRMADAS — cada uma é um BUG-14 esperando)

| # | lógica | cópias | risco |
|---|---|---|---|
| D1 | **split LF-only do decode** (fix do BUG-14) | `composicional/syntax.py:755` E `composicional/hcc_seqrle.py:297` — blocos IDÊNTICOS | o exemplo do owner: o fix teve que ser aplicado 2× no mesmo commit `a08bd6b`; a próxima mudança pode pegar só 1 |
| D2 | **check `\n`/`\r` pós-stringify** (BUG-06/10a) | `encoder.py:~226` (ramo list) E `multi/core.py:~334` (ramo dict) — loops gêmeos | mesma origem (lotes F0 2/3): mensagem e regra podem divergir |
| D3 | **split do body raw** no decode | `multi/core.py:558` E `view.py:134` | paridade por CONVENÇÃO, não por fonte única — a mesma classe do BUG-02 pré-fix (o meta já foi unificado em `_parse_meta`; o body não) |
| D4 | **arquitetura wrapper de 2 passadas**: `HCCSeqRLE.decode` itera as linhas (expande seq-RLE) e DELEGA pra `M8AVirtualRefsSyntax.decode` que RE-itera | camada dupla inteira | é a RAIZ do D1: enquanto houver dois decodes varrendo o mesmo texto, toda regra de linha se duplica |

### Espalhamento (defs/linhas por módulo)

`view.py` **35 defs**/419 · `composicional/syntax.py` **21 defs**/813 · `core/online.py` 14/210 ·
`multi/core.py` 12/611 · `hcc_seqrle.py` 12/321 · `encoder.py` 3/392 — total ~131 defs em src/tcf.

### Naming de protótipo vivo no código

`M8AVirtualRefsSyntax` + codinomes `M8.A`/`M10` em **8 arquivos** de src (`composicional/syntax.py`,
`hcc_seqrle.py`, `_trace.py`, `__init__.py`s, `encoder.py`, `pipeline.py`) + `_core/detect.pyx`/`.c`
(Cython!) + `tests/test_pyx_byte_equivalence.py` + `scripts/bench_evidencia_probes.py`. META-NAMING
(2026-05-17) fixou HCC como nome oficial; o código nunca acompanhou.

## Fases propostas (cada uma = lote com gate próprio; NUNCA refactor + comportamento no mesmo commit)

- [ ] **C0 — dedup cirúrgico (cabe no tail do .8; byte-neutro por construção, ~1 sessão)**:
  fonte única das 3 lógicas duplicadas — (1) helper `split_lf_body(text)` no lugar dos 2 blocos
  BUG-14 (D1); (2) stringify-com-check único (D2: `multi/core` exporta, `encoder` importa);
  (3) split de body raw único decode+view (D3, mesmo padrão do `_parse_meta`). Gate: suíte 600 +
  pins byte-canônicos + byte-neutralidade (a mudança não pode tocar 1 byte de output).
- [ ] **C1 — rename M8A→HCC (pós-release 0.8.0; mecânico mas toca o `.pyx`)**: classe/refs/docstrings
  saem do codinome de protótipo (M8A/M8.A/M10 viram nota histórica no docstring, não identificador);
  inclui `_core/detect.pyx` + regen `.c` + tests + scripts. Gate: byte-equivalence Cython
  (test_pyx_byte_equivalence) + suíte completa.
- [ ] **C2 — achatar a camada dupla do decode (a raiz do D1/D4)**: seq-RLE deixa de ser wrapper
  que re-varre o texto — decode vira UMA passada com expansão inline (ou pipeline explícito de
  estágios sobre linhas JÁ separadas uma vez). Redução de defs onde houver fragmentação sem coesão
  (view 35 defs; syntax 21). Gate COMPLETO: pins + real-world + Cython + fuzz RT (o harness de
  cortes/flips da verificação F0 vira propriedade).
- [ ] **C3 — re-medição pós-consolidação**: bytes DEVEM ser idênticos (re-pin proibido salvo decisão);
  latências mudam → re-rodar f1-smoke/f2 do material e anotar delta.

## Sequenciamento (proposta pro owner — ver "nova ordem feliz" no CLOSEOUT quando decidida)

C0 é pequeno e REDUZ risco do tail do .8 (menos cópias pra manter em sincronia durante F4/F6).
C1+C2 são a abertura do ciclo pós-release (0.8.x): refatorar ANTES de publicar invalidaria a
evidência de latência já medida e adiaria o release; refatorar DEPOIS herda a suíte inteira +
material como rede de segurança. Specs clássicos-BR (CEP/telefone/RG...) entram DEPOIS do C2:
adicionar 5 specs na máquina atual = mais código pra migrar depois.

## Critérios de aceite

- [ ] Zero lógica de negócio com 2 cópias em src/tcf (D1-D3 eliminadas; D4 desfeita no C2).
- [ ] Nenhum identificador `M8A`/codinome de protótipo em código vivo (só notas históricas).
- [ ] Bytes idênticos fase a fase (pins + real-world); Cython byte-equivalente.
- [ ] Contagem de defs por módulo REDUZIDA e registrada (antes/depois medido).
