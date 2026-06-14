# 0023 — Header v2 minimo welded (#TCF.7, opt-in `min_header`)

**Status**: accepted
**Date**: 2026-06-14
**Deciders**: project owner
**Tags**: v2.0, format, header, multi-column, #TCF.7, byte-level

## Context and Problem Statement

Diretriz do owner (2026-06-14): foco em compressao byte-a-byte — "cada byte
importa, principalmente se o TCF for substituir transmissoes MINUSCULAS". Em
payload pequeno o header de tamanho fixo domina o total, entao economias
O(1)-por-tabela no header deixam de ser ruido.

Duas redundancias no header multi-col (`#TCF.6 M\n# <s1>=<n1>,...,<sN>=<nN>\n`),
registradas em [O-FMT-15 e O-FMT-16](../../experiments/lab/dirty/notas/futuras-otimizacoes-formato.md):
- **O-FMT-16**: o ESPACO apos o `#` no meta line e' dispensavel.
- **O-FMT-15**: o size da ULTIMA coluna e' redundante — o corpo dela vai ate' o
  EOF (mesma logica do single-col, que ja' nao tem header nem size).

## Decision Outcome

**Weld do "header v2 minimo" como capacidade OPT-IN** (`encode(table, min_header=True)`),
multi-col, emitindo `#TCF.7 M`.

Formato minimo (dispensa o prefixo do meta + omite o size da ultima coluna):

    #TCF.7 M
    <s1>=<n1>,<s2>=<n2>,...,<nN>
    <body1><body2>...<bodyN>

- **Default `min_header=False`** -> header v1 (`# <s>=<n>,...`), `#TCF.6`,
  byte-identico (invariantes D1-D9=1523B, D17a=322B preservados). Segue o
  padrao do codebase (opt-in; default preserva byte-canonical).
- **Dispensa o prefixo `#` do meta** (revisao do header v0.6 pelo owner,
  2026-06-14): o flag `M` no shebang `#TCF.7 M` ja' declara que a proxima linha
  e' o meta de colunas, entao o `# ` e' redundante. Vale pra TODO `#TCF.7`
  (fallback inclusive), nao so' min_header — `#TCF.6` mantem o `# ` (congelado).
- **Decoder self-describing**: distingue pelo MAGIC (v6 exige `# `; v7 dispensa
  o prefixo, tolerante a `# `/`#`/nenhum); par sem `=` = ultima coluna (size
  omitido -> corpo ate' EOF).
- **Compoe com V2-A** (`fallback`): par raw vira `!<s>=<n>`, e a ultima coluna
  raw vira `!<n>` (raw, sem size). Emite `#TCF.7 M` se min_header OU fallback;
  o `#TCF.7` ja' dispensa o prefixo do meta independente de qual feature ativou.

## Pros and Cons

**Pros**:
- Economia direta no overhead fixo do header (ex: cadastro do README, 4 colunas:
  −5 B / 182 B = `# `(2) + `20=`(3); proporcionalmente maior em payload menor)
  — alinhado ao foco "transmissoes minusculas".
- Coerencia: a ultima-coluna-sem-size e' a generalizacao multi-col do single-col
  (que ja' e' EOF-bounded, [ADR-0001](0001-tcf-format-shebang.md)).
- Zero risco pro v1: default preserva byte-canonical; backward-compat total.

**Cons / limites**:
- Ganho O(1) por tabela — em tabela grande e' ruido (justificado pelo alvo
  payload-pequeno, nao pelo agregado real-world).
- Perde um cross-check potencial de integridade (soma de sizes), mas o decoder
  ja' nao validava sizes e integridade e' do transporte (analise em O-FMT-15).
- Single-col fora de escopo (ja' e' minimo: sem header).

## Relation to other ADRs

- **ADR-0017** (format frozen v1.0): `#TCF.6` permanece congelado; este e'
  aditivo e opt-in (#TCF.7).
- **ADR-0022** (V2-A fallback): mesmo `#TCF.7`, ortogonal; compoem. `min_header`
  e `fallback` sao flags independentes. **Este ADR tambem revisa o header do
  `#TCF.7` de V2-A**: o meta de qualquer `#TCF.7` passa a dispensar o prefixo
  `# ` (era `# !<s>=<n>` em ADR-0022; agora `!<s>=<n>`). `#TCF.7` e' pre-release,
  sem invariante congelado, entao a mudanca e' segura.
- **ADR-0004** (header compacto): nao considerou estas reducoes; este ADR
  as adiciona pro #TCF.7.

## Verification

- `tests/test_multi_col_rt.py::TestMinHeaderV2` (11 casos: opt-in, #TCF.7, forma
  do meta, menor que v1, compoe com fallback, ultima-coluna-raw-bare, 1-col,
  single-col ignora, RT com vazios).
- Suite: **351 passed, 1 xfailed**. Byte-canonical preservado no default
  (D1-D9=1523B, D17a=322B, snapshots real-world).
- Medido: cadastro README 182 B -> **177 B** com `min_header=True` (−5 B:
  `# `=2 do prefixo + `20=`=3 da ultima coluna). `fallback` sozinho: 182->180
  (so' o `# ` cai + a coluna raw).

## Links

- [O-FMT-15/16 + bundle "header v2 minimo"](../../experiments/lab/dirty/notas/futuras-otimizacoes-formato.md)
- [ADR-0022 V2-A fallback](0022-v2a-fallback-identity-weld.md)
- [ADR-0018 roadmap v2.0](0018-v2-format-roadmap.md)
- Diretriz: memoria user `project-byte-level-compression-focus`
