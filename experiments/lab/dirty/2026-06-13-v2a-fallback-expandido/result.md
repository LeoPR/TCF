# Result — V2-A fallback caracterizacao expandida + bug de RT no core [probatório]

**Data**: 2026-06-13
**Objetivo**: Stage 1 da abertura da v2.0 (owner decidiu perseguir bytes).
Estender a caracterizacao de V2-A (fallback identity, ADR-0018 prioridade #1)
de 3 datasets (proto 2026-05-27) para N>=5 fontes reais, cumprindo o checklist
"antes de declarar confirmada-empirica" (CLAUDE.md).

## 1. V2-A generaliza — 9 fontes, 7.85% weighted

`characterize_v2a.py` — min(tcf, raw) por coluna, marcador `!name`, amostra 20k
linhas por tabela. Lido de `Z:/tcf-data/external/`.

| dataset | rows | cols | M10 B | fallback B | ganho | →raw | RT |
|---|---|---|---|---|---|---|---|
| adult-census | 20000 | 15 | 759426 | 717622 | 5.50% | 4/15 | OK |
| beijing-pm25 | 20000 | 13 | 457733 | 413719 | 9.62% | 3/13 | OK |
| wine-quality | 6497 | 13 | 300483 | 298006 | 0.82% | 1/13 | OK |
| ibge-municipios | 5571 | 8 | 159908 | 159592 | 0.20% | 1/8 | OK |
| online-retail | 20000 | 8 | 413648 | 405542 | 1.96% | 1/8 | OK |
| tpch-lineitem | 20000 | 16 | 1896538 | 1694709 | 10.64% | 5/16 | OK |
| tpch-orders | 15000 | 9 | 1264534 | 1218744 | 3.62% | 4/9 | OK |
| br-empresas | 20000 | 6 | 1131468 | 990205 | 12.48% | 3/6 | OK |
| receita-estab | 20000 | 8 | 1011065 | 916439 | 9.36% | 4/8 | **ver §2** |
| **WEIGHTED** | | | 7394803 | 6814578 | **7.85%** | | |

Checklist confirmada-empirica:
1. Real-world testado? **Sim** (Adult, TPC-H, + 7 outros).
2. N>=5 fontes distintas? **Sim** (9 tabelas, 6+ familias).
3. Sintetico vs real? N/A (so' real-world aqui).
4. Vies declarado? Datasets canonicos, nao construidos pra V2-A.
5. Bytes weighted >= 5%? **Sim, 7.85%.**

Ganho sempre positivo (0.20%–12.48%) — a propriedade "nunca pior que raw" se
sustenta (min por coluna + 1 byte de marcador `!`). V2-A **generaliza**.
Onde morde: colunas numericas curtas baixa-card (hour, Quantity, l_linenumber,
custkey) e free-text que o HCC nao comprime bem (l_comment, nome_fantasia).

## 2. Achado mais importante: bug de RT no core M10 (NAO e' do V2-A)

`receita-estab` deu RT FAIL. Diagnostico (`diag_receita.py`, `minimize_bug.py`,
`verify_bug.py`): **NAO e' falha do fallback** — e' o baseline all-TCF (m10_rt).
Na verdade V2-A **contorna** o bug: nome_fantasia cai pra raw (158KB < 178KB),
e o raw path RT-passa. O FAIL veio de `m10_rt and fb_rt` com m10_rt=False.

### Reproducer minimo (standalone, API publica, sem Z:)

```python
from tcf import encode, decode
decode(encode(['', 'AAAB', 'AAAC']))   # -> ['', 'AAAB', 'BC']   (corrompe)
decode(encode(['', 'RES', 'RESID']))   # -> KeyError: 2          (crash)
```

### Fronteira do bug

| input | output | verdict |
|---|---|---|
| `['', 'RESTAURANTE AR DE MINAS', 'RESIDENCIAL NOVA BATALHA']` | splice | FAIL |
| `['RESTAURANTE…', 'RESIDENCIAL…']` (sem empty) | igual | OK |
| `['RESTAURANTE…', '', 'RESIDENCIAL…']` (empty meio) | igual | OK |
| `['RESTAURANTE…', 'RESIDENCIAL…', '']` (empty fim) | len 3→2 (valor some) | FAIL |
| `['', 'AAAB', 'AAAC']` | `['', 'AAAB', 'BC']` | FAIL |
| `['', 'PREFIXOxxx', 'PREFIXOyyy']` | `['', 'PREFIXOxxx', 'xxxyyy']` | FAIL |
| `['', 'ABCDEF', 'GHIJKL']` (sem prefixo) | igual | OK |
| `['', 'RES', 'RESID']` | KeyError: 2 | FAIL (crash) |

**Padrao**: string vazia em posicao que desloca o index de fragmento +
valor(es) posterior(es) com prefixo compartilhado (que viram back-ref HCC).
Sintomas escalam: corrupcao silenciosa → valor perdido → crash.

### Root cause (localizado, read-only — fix exige aprovacao)

`src/tcf/composicional/syntax.py`, `decode`/`_parse_decl`. Dois espacos de index:
- `nos_decl` (refs de linha inteira `^N`) — empty linha **conta** (`nos_decl.append('')`).
- `frags`/`prox_idx` (refs de fragmento `~ , digito` em `_parse_decl`) — empty
  linha **nao conta**: `_parse_decl('')` retorna `''` sem `prox_idx[0]+=1`.

O encoder conta o valor vazio no espaco de fragmentos; o decoder nao reserva o
index → todas as back-refs posteriores deslocam em 1. O fix de 2026-05-18
(linhas 758-763) consertou a SAIDA (nao pular linha vazia) mas nao o INDEX de
fragmentos. Familia do ADR-0006, caso distinto e nao coberto.

### Por que os gates nao pegaram

- `test_core_rt.py::test_empty` so' cobre `encode([])` (xfail). Nada cobre
  empty-value + prefixo-compartilhado.
- `test_real_world_snapshots.py` usa retail Description + lineitem l_comment;
  receita-cnpj nao esta nas fixtures, e o padrao gatilho nao aparece nas
  colunas pinadas. Valida a recomendacao de corpus free-text real no gate.

Severidade ALTA: viola o contrato fundamental `decode(encode(x)) == x` em dado
trivial-real (celula vazia + texto com prefixo comum, comum em qualquer tabela),
com corrupcao silenciosa E crash. **Ticket**: T-BUG-1.

## 3. Conclusao + proximo passo

- **V2-A**: confirmada-empirica (7.85% weighted, 9 fontes, RT do path raw OK).
  Pronta pra weld quando v2.0 abrir — mas o weld precisa do bug do §2 resolvido
  (o all-TCF que V2-A escolhe-ou-nao precisa estar correto).
- **Bug §2 tem prioridade sobre bytes** (correcao > otimizacao). Recomendado:
  consertar + pinar o reproducer ANTES de qualquer welding v2.0. Fix toca
  `src/tcf` → exige aprovacao explicita do owner + re-validar D1-D9=1523B +
  gate real-world.

## 4. Bug CORRIGIDO (aprovado pelo owner, 2026-06-13)

Eram DOIS modos, fix byte-canonical-safe:

**Root cause refinado** (probe_obat.py): OBAT (`processar`) e' inconsistente
por design frozen — `''` PRIMEIRA unica -> `[L('')]` (1 frag); `''` apos outra
-> `[]` (0 frag). O decode nunca reservava index pra linha vazia -> off-by-one
so' quando o empty era a 1a unica + havia back-ref posterior.

- **Modo 1** (`syntax.py::_parse_decl`): reservar frag vazio SO' quando
  `prox_idx==0` (espelha o OBAT). 1a tentativa incondicional regrediu retail
  (empty nao-primeiro) — corrigida pela condicao.
- **Modo 2** (`hcc_seqrle.py::encode`): `rstrip('\n')` -> `[:-1]` (vazio final
  era comido). Identico pra body sem vazios finais.

**Verificacao**: fronteira 0/9 falham; suite 332 passed + 1 xfailed; D1-D9=1523B
+ D17a=322B + real-world snapshots verdes (bytes M10 identicos -> decode-only
confirmado); receita-estab RT FAIL -> OK; V2-A 9/9 RT, 7.85% weighted.

Ticket: T-CODE-EMPTY-FRAG-INDEX-RT (CLOSED). Reproducers pinados em
`tests/test_core_rt.py::TestEmptyValueFragIndex` (12 casos).

## Artefatos
- `characterize_v2a.py` — caracterizacao 9 datasets
- `diag_receita.py` — isola m10_rt vs fb_rt, acha coluna/linha
- `minimize_bug.py` — ddmin -> reproducer de 3 valores
- `verify_bug.py` — fronteira via API publica (standalone)
- `probe_bodies.py` — dump dos bodies (sintetico vs retail)
- `probe_obat.py` — regra do OBAT pra '' por posicao (root cause)
