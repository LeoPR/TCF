---
title: EXP-010 — Prototype TCF delta-aware (single-column)
type: clean-experiment
status: active
tags: [tcf, delta-aware, single-column, prototype, v0.6-candidate]
created: 2026-05-17
updated: 2026-05-18
welds: experiments/lab/dirty/2026-05-17-OBAT-delta-aware/
predecessor: EXP-007-prototipo-tcf-core
related:
  - docs/adr/0003-tripartite-pre-obat-hcc.md
  - experiments/lab/clean/EXP-011-multi-column-basic/
  - experiments/lab/dirty/notas/roadmap-hipoteses.md
---

# EXP-010 — Prototype TCF delta-aware (single-column)

**Data**: 2026-05-17
**Tipo**: experimento clean
**Ciclo**: v0.6 → v0.7 candidato
**Estado**: ativo
**Predecessor**: EXP-007 (prototipo canonical)
**Welds**: pacote 1 (Delta-aware) do lab
[`../../dirty/2026-05-17-OBAT-delta-aware/`](../../dirty/2026-05-17-OBAT-delta-aware/)

## Pergunta cientifica

Os achados do pacote 1 (dirty lab) integram-se em um pipeline clean
que:
1. Reproduz baseline canonical (D1-D9) sem regressao significativa
2. Captura ganhos delta-aware (D11a-h, D16a-c) sem regredir
3. Mantem invariantes do projeto: single-pass, low-memory, RT
   byte-canonical

E e' fact-checked contra os numeros do dirty lab?

## Hipotese

**H1**: Pipeline `Pre (auto-detect) → OBAT (canonical ou hint) →
HCC fork (seq-RLE)` em 20 datasets:
- Total bytes ~= 2272 (sub-exp 09 auto-detect)
- RT 20/20 OK
- Sem regressao vs canonical em D1-D9 EXCETO casos onde auto-detect
  decide habilitar hint (D8, D9 — ja' validados)

**H0** (rejeitada): se bytes != sub-exp 09 ou RT != 20/20, prototype
diverge do dirty lab e indica bug no welding clean.

## Metodo

1. Implementar `delta_aware.py`:
   - `encode_column(rows: list[str]) -> str` — pipeline completo
   - `decode_column(tcf_text: str) -> list[str]` — pipeline reverso
2. Modulos auxiliares (welded do dirty lab, codigo clean):
   - `auto_pre.py` — `detect_cadence(strings, threshold=0.7)`
   - `obat_shape.py` — `processar_with_hint(strings, prefer_shape_consistency)`
   - `hcc_seqrle.py` — `HCCForkSeqRLE` (subclass M8AVirtualRefsSyntax)
3. `run.py` valida em 20 datasets (D1-D9 + D11a-h + D16a-c)
4. Compara byte-a-byte com bodies do sub-exp 09 (`outputs/<ds>/body-auto.tcf`)
5. Verifica RT 20/20

## Escopo / Restricoes

- **Single-column**: aceita 1 coluna por vez. Multi-column = futuro.
- `src/tcf/core/online.py` e `src/tcf/composicional/syntax.py`
  **intocados** — fonte da verdade. Prototype IMPORTA e ESTENDE.
- Codigo welded do dirty lab — sem modificacoes algoritmicas, so'
  cleanup (remove logs verbosos, comentarios de debug).
- API publica: `from delta_aware import encode_column, decode_column`.

## Datasets

20 datasets de `datasets/synthetic/`:

| ID | Tipo | Cenario |
|---|---|---|
| D1-D9 | stress | M9 baseline (datasets validados originais) |
| D11a-h | datetime | cadencia regular (datas/datetimes) |
| D16a-c | numeric IDs | sequenciais (3-digit / 4-digit / prefixados) |

## Aceite

- **Welded OK** se: bytes ~= sub-exp 09 (delta < 5 bytes por dataset)
  E RT 20/20 OK
- **Diverge** se: bytes muito diferentes ou RT failures → bug no
  port → fix antes de continuar

## Limitacoes conceituais (lembrete)

- Datasets sao **sinteticos**. Generalizacao pra real-world
  (TPC-H, Adult Census) NAO testada nem aqui nem no dirty lab
- Threshold 0.7 da heuristica e' arbitrario; outros valores
  dariam resultados diferentes
- Pipeline ainda **single-column**; real-world tem multi-column

## Estrutura

```
EXP-010-tcf-delta-aware-prototype/
├── README.md
├── delta_aware.py      ← API publica (encode_column, decode_column)
├── auto_pre.py
├── obat_shape.py
├── hcc_seqrle.py
├── run.py
├── report.md           (gerado)
└── outputs/<ds>.tcf
```

## See also

- **Predecessor canonical**: [EXP-007 prototipo TCF-CORE](../EXP-007-prototipo-tcf-core/) — baseline single-column
- **Dirty lab origem**: [`obat-delta-aware`](../../dirty/2026-05-17-OBAT-delta-aware/) — 9 sub-exps que welded aqui
- **Multi-column extension**: [EXP-011 multi-column basic](../EXP-011-multi-column-basic/)
- **Decisao arquitetural**: [ADR-0003 tripartite Pre/OBAT/HCC](../../../../docs/adr/0003-tripartite-pre-obat-hcc.md)
- **Restricoes**: [ADR-0002 vertice triplice](../../../../docs/adr/0002-vertice-triplice-restricao.md)
- **Format**: [ADR-0001 shebang](../../../../docs/adr/0001-tcf-format-shebang.md)
- **Roadmap**: [hipoteses cross-lab](../../dirty/notas/roadmap-hipoteses.md)
- **Memoria projeto**: `project_pacote1_delta_aware_summary` (user memory)
