# Dicas de limpeza — dead code (candidatos, NÃO auto-deletar) [registro vivo]

**Origem**: foco 2 (limpeza/modularizacao). Owner pediu ferramentas de obsolescencia
(2026-06-24). **vulture** (dead-code) tem alto falso-positivo numa biblioteca → suas
saidas viram **dica de limpeza**, aplicadas SO' apos inspecao manual. **ruff** (continuo,
`[tool.ruff]` no pyproject) cuida do dia-a-dia (F-rules confiaveis + sugestoes a avaliar).

> **Regra**: nada aqui se deleta sem confirmar caller=0 em TODO o repo (src+tests+scripts)
> E que nao e' API publica/documentada/dinamica. Re-rodar `python -m vulture src/tcf` apos
> mudancas. GATE byte-canonical sempre.

## Candidatos a remover — RESOLVIDOS (inspecao 2026-06-24)

Todos os "verdadeiro-positivo" do vulture foram inspecionados; nenhum sobrou pendente.
Ver "Ja' aplicado" (removidos) e "NAO TOCAR" (falso-positivos confirmados na inspecao).

## NÃO TOCAR (falso-positivo do vulture — usado externamente / build / abstract)

- `linhas_originais` (`core/syntax_base.py:42`) — **PARAMETRO do metodo abstrato `encode`**,
  nao variavel morta. As implementacoes concretas usam (M8A usa `linhas`). vulture deu 100%
  de confianca e ERROU (nao entende metodo abstrato) — o caso-escola do "nao confiar cego".
- `_detect_compositions_accelerated` (`syntax.py`) — **hook do Cython** (flag de build,
  `_core/detect.pyx`). Deletar quebra o acelerador.
- API publica do lazy (`view.py`): `where`, `group_count`, `agg_by`, `report`,
  `column_bytes`, `group_ranges`, `select` — chamadas por terceiros (`tcf.view`).
- Campos de `SideOutputs` (`hcc_trace`, `hcc_rede`, `obat_used_hint`, `seq_rle_runs`,
  `natures`, etc.) — populados no encode, lidos por consumidores (debug/schema).
- `to_json` / `seq_rle_runs_count` / `natures` (`schema.py`) — API/serializacao publica.

## Ja' aplicado / removido (byte-safe, suite verde)

- `multi/core.py` F401 `_worker_encode_column` (artefato P1) — removido (ruff).
- `schema.py` F821 annotation `SideOutputs` — import sob TYPE_CHECKING (ruff).
- `_trace.py` `k_idx` no enumerate (codigo P2) — enumerate superfluo removido (ruff).
- `hcc_seqrle.py` `find_escape_digit_positions` — DEAD (0 caller; superado por
  `find_escape_digit_runs`) — **removido** apos inspecao 2026-06-24.
- `core/online.py` `reconstroi` — DEAD (docstring dizia "usado em processar()", mas
  processar() nao chama mais; 0 caller) — **removido** + linha da docstring do modulo.

## Workflow recomendado (vulture NAO e' dep)

- **Continuo / confiavel**: `python -m ruff check src/tcf` (F-rules; E = estilo, avaliar depois).
  `[tool.ruff]` no pyproject.
- **Dead-code AD-HOC** (varredura pontual, nao em CI/dep): `pipx run vulture src/tcf` ou
  `pip install vulture && python -m vulture src/tcf --min-confidence 60`. Alto falso-positivo
  numa lib (API publica, build-hooks, params abstratos) → **so' agir apos inspecao manual**
  (caller=0 em src+tests+scripts E nao-publico/dinamico). Esta nota e' o registro curado.
