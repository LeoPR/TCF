---
title: T-CODE-EMPTY-FRAG-INDEX-RT — Bug de RT no core M10 (string vazia desloca index de fragmento HCC)
status: open
priority: P1
created: 2026-06-13
updated: 2026-06-13
blocked-by: []
related:
  - experiments/lab/dirty/2026-06-13-v2a-fallback-expandido/result.md
  - src/tcf/composicional/syntax.py
  - docs/adr/0006-empty-string-decode-fix.md
  - docs/adr/0007-comma-in-literals-bug.md
  - tests/test_core_rt.py
---

# T-CODE-EMPTY-FRAG-INDEX-RT — Bug de RT no core M10

**[probatório]** Registra um defeito de correcao verificado. Severidade ALTA:
viola o contrato fundamental `decode(encode(x)) == x` em dado trivial-real,
com corrupcao silenciosa E crash.

## Contexto / descoberta

Achado durante a caracterizacao expandida de V2-A (Stage 1 da v2.0,
[lab 2026-06-13-v2a-fallback-expandido](../experiments/lab/dirty/2026-06-13-v2a-fallback-expandido/result.md)):
`receita-cnpj/estabelecimentos.csv` coluna `nome_fantasia` (free-text real)
deu RT FAIL no baseline all-TCF. Minimizado a um reproducer standalone.

## O bug

Contrato violado: `decode(encode(x)) == x`.

```python
from tcf import encode, decode
decode(encode(['', 'AAAB', 'AAAC']))   # -> ['', 'AAAB', 'BC']   corrompe
decode(encode(['', 'RES', 'RESID']))   # -> KeyError: 2          crash
```

### Fronteira (verify_bug.py, API publica)

| input | output | verdict |
|---|---|---|
| `['', 'RESTAURANTE AR DE MINAS', 'RESIDENCIAL NOVA BATALHA']` | splice | FAIL |
| `['RESTAURANTE…', 'RESIDENCIAL…']` (sem empty) | igual | OK |
| `['RESTAURANTE…', '', 'RESIDENCIAL…']` (empty no meio) | igual | OK |
| `['RESTAURANTE…', 'RESIDENCIAL…', '']` (empty no fim) | len 3→2 (valor some) | FAIL |
| `['', 'AAAB', 'AAAC']` | `['', 'AAAB', 'BC']` | FAIL |
| `['', 'PREFIXOxxx', 'PREFIXOyyy']` | `['', 'PREFIXOxxx', 'xxxyyy']` | FAIL |
| `['', 'ABCDEF', 'GHIJKL']` (sem prefixo compartilhado) | igual | OK |
| `['', 'RES', 'RESID']` | KeyError: 2 | FAIL (crash) |

**Padrao gatilho**: string vazia em posicao que desloca o index de fragmento +
valor(es) posterior(es) com prefixo compartilhado (que o HCC codifica como
back-reference). Sintomas escalam: corrupcao silenciosa → valor perdido → crash.

## Root cause (hipotese, localizada read-only)

`src/tcf/composicional/syntax.py`, `decode` (~L752) + `_parse_decl` (~L660-750).
Dois espacos de index distintos:
- `nos_decl` (refs de linha inteira `^N`): linha vazia **conta** (`nos_decl.append('')`).
- `frags`/`prox_idx` (refs de fragmento `~ , digito` em `_parse_decl`): linha vazia
  **nao conta** — `_parse_decl('')` retorna `''` sem `prox_idx[0] += 1` (o while
  loop sobre `resto` vazio nunca roda o branch que registra fragmento).

O encoder conta o valor vazio no espaco de fragmentos; o decoder nao reserva o
index → toda back-ref posterior desloca em 1 (e quando aponta alem do fim,
`KeyError`). O fix de 2026-05-18 (syntax.py L758-763, EXP-012/013) consertou a
SAIDA (parar de pular linha vazia) mas nao o INDEX de fragmentos. Familia do
ADR-0006 (empty string decode), caso distinto e nao coberto.

## Por que os gates nao pegaram

- `tests/test_core_rt.py::test_empty` so' cobre `encode([])` (xfail). Nenhum
  caso com empty-value + prefixo-compartilhado.
- `tests/test_real_world_snapshots.py` usa retail Description + lineitem
  l_comment; receita-cnpj nao esta nas fixtures e o padrao gatilho nao aparece
  nas colunas pinadas.

## Criterio de aceite (KR)

- [ ] Reproducers do quadro acima passam `decode(encode(x)) == x` (sem crash).
- [ ] Casos pinados em `tests/test_core_rt.py` (incl. empty-no-fim, empty+prefixo,
      crash-case, 2-emptys).
- [ ] Byte-canonical preservado EXATO: D1-D9 = 1523B, D17a = 322B
      (`test_regression_v1_baseline.py`, `test_core_rt.py`, `test_multi_col_rt.py`).
- [ ] Gate real-world verde (`test_real_world_snapshots.py`).
- [ ] Idealmente: fix decode-only (encode output inalterado) → byte-canonical-safe
      por construcao. Se exigir tocar encode, re-pinar baselines com justificativa.
- [ ] Considerar adicionar fixture free-text com empty+prefixo ao gate real-world
      (receita nome_fantasia ou sintetico) — fecha a lacuna de cobertura.

## Riscos

1. **Byte-canonical**: o index de fragmento faz parte do formato. Se o fix mexer
   na NUMERACAO de encode, muda bytes → quebra D1-D9. Mitigacao: preferir fix
   decode-side (reservar index pra linha vazia) que nao toca encode output.
2. **Regressao em outros caminhos**: empty no meio hoje passa (OK) — o fix nao
   pode quebrar esse. Cobrir ambos.
3. Toca `src/tcf` (canonical) → exige **aprovacao explicita do owner** (CLAUDE.md
   NUNCA). Gate dos DOIS suites (D1-D9 + real-world) antes de qualquer weld.

## Conexoes

- Lab: `experiments/lab/dirty/2026-06-13-v2a-fallback-expandido/` (repro + ddmin)
- ADR-0006 (empty string decode fix — fix anterior, escopo distinto)
- ADR-0007 (comma in literals — familia de bugs de parsing de body)
- V2-A (ADR-0018): o fallback contorna este bug (nome_fantasia cai pra raw),
  mas o weld de V2-A pressupoe o all-TCF correto → este bug e' pre-requisito.
