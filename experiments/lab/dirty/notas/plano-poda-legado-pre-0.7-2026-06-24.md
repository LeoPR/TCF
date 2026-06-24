# Plano — podar fallbacks/legado pré-0.7 do core (rumo a 1.0) [plano]

**Data**: 2026-06-24 · plano (NÃO implementa; aprovar antes de tocar `src/tcf`). Origem: owner —
"tirar os fallbacks de versões pré-0.7; se for pra testar, isolar em estrutura de comparação OU
aposentar; ao chegar no 1.0 o código todo fica na versão de formato final (#TCF.8/.9)". Cuidado
declarado: **não atropelar o sincronismo entre versão de FORMATO e versão de DESENVOLVIMENTO**.

## 1. Modelo de versão — 3 EIXOS distintos (a causa do "atropelo")

O projeto mistura três coisas que NÃO são a mesma:

| eixo | o que é | valores hoje | natureza |
|---|---|---|---|
| **A. Formato** | shebang `#TCF.N` (contrato on-disk) | `#TCF.7` (default), `#TCF.6` (legado) | só muda com weld de formato |
| **B. Geração do encoder** | marco do algoritmo (bytes diferentes, MESMA família de formato) | M8A (base HCC) → M9 → **M10** (atual) | interno; M9 é **subset** de M10 (mesmo decoder) |
| **C. Pacote (semver)** | contador de release | `0.7.1` → `0.7.2` (poda = formato #TCF.7 inalterado) | dev marker; minor=formato, patch=release (ADR-0024/0028) |

**Regra para não atropelar** (a fixar como dispositivo):
- "pré-0.7" = **eixo A** (`#TCF.6`) + a **API v0.6** (`encode_table`/`decode_table`). É isto que se poda.
- **M9 (eixo B) NÃO é legado-pra-remover**: `M8AVirtualRefsSyntax` é a CLASSE-BASE do HCC (HCCSeqRLE
  herda dela). O `hcc_seq_rle=False` é **ablação científica**, não compat. Fica (isolado como knob de
  comparação, não como "fallback de versão").
- **ADR-0024 (git-as-compat)** autoriza **dropar leitura de `#TCF.6`**: não precisamos ler formatos
  antigos porque `git checkout <tag>` reproduz o encoder antigo. Decisão de timing abaixo.
- **Alvo 1.0**: o código converge para UM formato final (#TCF.8 quando o cross-dict weldar, ou #TCF.9
  se mudar mais). A poda pré-0.7 é o passo que limpa o terreno pra essa convergência.

## 2. Inventário (verificado no código + testes, 2026-06-24)

### A — Formato #TCF.6 (ler + produzir) — o legado central
- **Ler**: `decoder.py` (`_MULTI_MAGIC_STR="#TCF.6 M"` + dispatch nos dois); `multi.py` (`MAGIC_MULTI`,
  `META_PREFIX="# "`, ramo de parse com prefixo `# `, L465/476/485); `view.py` (lê os dois, L61-72).
- **Produzir**: `multi.py._encode_multi(fallback=False, min_header=False)` → emite `#TCF.6 M` + `# `+sizes
  (L285-322); exposto via knobs públicos `fallback=False`+`min_header=False` (encoder.py L76,103).
- **Testes que pinam**: `test_multi_col_rt.py` (helper `_legacy_v6`, **322B INVARIANT**, `startswith
  "#TCF.6 M"`, decode-compat); `conftest.py`/`test_natures.py`/`test_parallel.py` (comentário 322B).

### C — API v0.6 deprecated
- `multi.py`: `encode_table`/`decode_table` (DeprecationWarning desde ADR-0014); `__init__.py` exporta
  (em `__all__` + `EXPECTED_PUBLIC_API`). Testes: deprecation-warning + legacy_info-keys.

### B — M9 (NÃO é alvo de remoção; reclassificar)
- `encoder.py` (ramo `if cfg.hcc_seq_rle`: HCCSeqRLE senão M8AVirtualRefsSyntax); `pipeline.py`
  (`hcc_seq_rle` toggle); `hcc_seqrle.py` (subclass de M8A). → **manter como ablação**; só renomear a
  intenção nos docstrings (de "M9 puro/legado" → "ablação seq-RLE").

### D — Ruído cosmético (comentários/docstrings)
- Refs a "M9 baseline 1615B", "v0.6", "#TCF.6 default" em docstrings (`__init__.py`, `auto_min_len.py`,
  `core/__init__.py`, `encoder.py` L18). Já houve um pass (CW-4); sobram restos.

## 3. Classificação + ação proposta (por artefato)

| artefato | ação | porquê | impacto GATE/teste |
|---|---|---|---|
| `encode_table`/`decode_table` | **APOSENTAR** (remover) | deprecated desde ADR-0014; git-as-compat | tirar de `__all__`+`EXPECTED_PUBLIC_API`; remover 4 testes deprecation/legacy_info |
| Produção `#TCF.6` (`fallback=False,min_header=False` → magic+`# `) | **ISOLAR como comparação** | só serve de baseline histórico (322B = ganho do V2) | mover os testes 322B p/ um módulo `tests/legacy/` de comparação; tirar do gate principal |
| Leitura `#TCF.6` (decoder + multi + view) | **DECISÃO** (ver §4) | ADR-0024 permite dropar; mas quebra read de blobs antigos | se dropar: simplifica decoder/multi/view; se manter: isolar num `_legacy_read` marcado |
| Knobs `fallback`/`min_header` (os `=True` default) | **MANTER** | são os toggles V2 vivos (não são legado) | nenhum |
| M9 / `hcc_seq_rle=False` | **MANTER (reclassificar p/ ablação)** | M8A é base do HCC; toggle é ciência | nenhum; só docstring |
| Comentários M9/v0.6/#TCF.6-default | **LIMPAR** | ruído de superfície | nenhum (só doc) |

## DECISÕES DO OWNER (2026-06-24) — plano aprovado

1. **Leitura #TCF.6** → **isolar em `_legacy_read`** (caminho marcado), dropar no 1.0. (§4.1 opção b)
2. **Produção #TCF.6 + 322B + aliases v0.6** → **aposentar `encode_table`/`decode_table`** + **isolar
   o 322B em `tests/legacy/`** (comparação V2-vs-legado, fora do gate). 303B = único baseline vivo. (§4.2-3)
3. **Sequência** → **podar agora, fundido no release `0.7.2`** (lazy + enxugar legado; formato #TCF.7
   inalterado → patch, não 0.8.0 — ADR-0028). (§4.4)
Ticket de execução: **T-CODE-LEGACY-PRUNE-PRE-07**.

## 4. Decisões do owner (forks reais)

1. **Leitura de `#TCF.6`**: (a) **dropar agora** (decoder só lê `#TCF.7`; git reproduz o resto —
   ADR-0024) → simplifica decoder/multi/view; (b) **isolar** num caminho `_legacy_read` claramente
   marcado, dropar no 1.0; (c) **manter** como está. *Recomendo (b)*: limpa o caminho principal sem
   perder a leitura, e o 1.0 remove. (a) é o mais limpo mas é decisão de compat.
2. **Produção `#TCF.6` + baseline 322B**: confirmar **isolar em `tests/legacy/`** (comparação V2 vs
   legado) e tirar do gate principal — concorda? Ou **aposentar** o 322B de vez (só 303B fica)?
3. **`encode_table`/`decode_table`**: aposentar agora (pré-1.0, já deprecated)? *Recomendo sim.*
4. **Sequência vs release 0.8**: a poda é refactor sob GATE. Fazer **antes** do release 0.8 (0.8 já
   sai enxuto) ou como track 1.0 separado **depois** do 0.8? *Recomendo: poda agora como passo
   próprio, com bump pro release 0.7.2 incluindo a limpeza* (faz sentido: 0.7.2 = lazy + enxugar legado).

## 5. Sequência proposta (cada passo mantém a suíte verde)

1. **S1 — API**: aposentar `encode_table`/`decode_table` (remover + `__all__`/`EXPECTED_PUBLIC_API` +
   testes). Menor risco, zero efeito de bytes.
2. **S2 — Produção #TCF.6**: mover os testes 322B p/ `tests/legacy/` (comparação); manter o caminho
   interno `_encode_multi(fallback=False,min_header=False)` só se o owner quiser a comparação, senão
   remover. Gate principal passa a afirmar só `#TCF.7`/303B.
3. **S3 — Leitura #TCF.6** (conforme decisão §4.1): isolar ou dropar. Re-rodar D1-D9/D17a/real-world.
4. **S4 — Limpeza cosmética**: docstrings M9/v0.6/#TCF.6-default → linguagem atual (eixos A/B/C).
5. **S5 — Doc do modelo de versão**: gravar os 3 eixos (§1) num lugar canônico (ADR ou
   `docs/algorithms/TCF-format.md` §Versionamento) pra não reatropelar.

**Invariantes**: cada passo roda `test_core_rt` + `test_regression_v1_baseline` + `test_multi_col_rt`
+ `test_real_world_snapshots` verdes. Mudança em `src/tcf` só com aprovação. D1-D9=1523B / D17a=303B
intactos (303B vira o único baseline vivo; 322B vira comparação ou aposentado).

## Conexões
- Versionamento: [ADR-0024](../../../../docs/adr/0024-pre-1.0-versioning-git-as-compat.md) (git-as-compat) +
  [ADR-0017](../../../../docs/adr/0017-format-spec-v1-frozen.md) (superseded, mas referência do freeze antigo).
- Header V2: ADR-0022/0023/0025/0026. Higiene anterior: T-CLEAN-2 (defrag), CW-4 (docstrings).
- Decisão de escopo: [`filtros-graus-de-entrega-2026-06-24.md`](filtros-graus-de-entrega-2026-06-24.md)
  (0.8=lazy+release; #TCF.8/cross-dict→0.9). A poda pré-0.7 prepara a convergência de formato do 1.0.
