# Dicas de limpeza — dead code (candidatos, NÃO auto-deletar) [registro vivo]

**Origem**: foco 2 (limpeza/modularizacao). Owner pediu ferramentas de obsolescencia
(2026-06-24). **vulture** (dead-code) tem alto falso-positivo numa biblioteca → suas
saidas viram **dica de limpeza**, aplicadas SO' apos inspecao manual. **ruff** (continuo,
`[tool.ruff]` no pyproject) cuida do dia-a-dia (F-rules confiaveis + sugestoes a avaliar).

> **Regra**: nada aqui se deleta sem confirmar caller=0 em TODO o repo (src+tests+scripts)
> E que nao e' API publica/documentada/dinamica. Re-rodar `python -m vulture src/tcf` apos
> mudancas. GATE byte-canonical sempre.

## Candidatos a remover (verdadeiro-positivo, pendente de inspecao+aprovacao)

| simbolo | local | status | nota |
|---|---|---|---|
| `find_escape_digit_positions` | `composicional/hcc_seqrle.py:36` | **dead** (0 caller no repo) | so' `find_escape_digit_runs` e' usado. Remover é byte-safe (nao esta' no caminho de encode). Confirmar antes. |
| `linhas_originais` | `core/syntax_base.py:42` | **dead** (var, vulture 100%) | variavel nao usada na classe-base. Trivial. |
| `reconstroi` | `core/online.py:165` | **judgment** (0 caller, mas API documentada) | listada na docstring do modulo OBAT (`reconstroi(tokens, ...)`). Pode ser API publica intencional do OBAT → **manter** salvo decisao explicita do owner. |

## NÃO TOCAR (falso-positivo do vulture — usado externamente / build)

- `_detect_compositions_accelerated` (`syntax.py`) — **hook do Cython** (flag de build,
  `_core/detect.pyx`). Deletar quebra o acelerador.
- API publica do lazy (`view.py`): `where`, `group_count`, `agg_by`, `report`,
  `column_bytes`, `group_ranges`, `select` — chamadas por terceiros (`tcf.view`).
- Campos de `SideOutputs` (`hcc_trace`, `hcc_rede`, `obat_used_hint`, `seq_rle_runs`,
  `natures`, etc.) — populados no encode, lidos por consumidores (debug/schema).
- `to_json` / `seq_rle_runs_count` / `natures` (`schema.py`) — API/serializacao publica.

## Ja' aplicado (ruff F, byte-safe)

- `multi/core.py` F401 `_worker_encode_column` (artefato P1) — removido (commit lint).
- `schema.py` F821 annotation `SideOutputs` — import sob TYPE_CHECKING.
- `_trace.py` `k_idx` no enumerate (codigo P2) — enumerate superfluo removido.

## Workflow recomendado

- **Continuo**: `python -m ruff check src/tcf` (F-rules confiaveis; E = estilo, avaliar).
- **On-demand** (inspecao): `python -m vulture src/tcf --min-confidence 60` → cruzar com
  esta tabela; so' agir apos confirmar caller=0 + nao-publico.
