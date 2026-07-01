# B2 prototype (read-only) — group-dict híbrido V2 com round-trip [probatório]

**Data**: 2026-06-27. Valida o [design-b2.md](../2026-06-21-gdict-caracterizacao/design-b2.md)
(pós-revisão A-D) construindo o formato `&<G>` **de verdade** e provando **RT lossless** — vai além
do B1, que só modelou bytes. `src/tcf` INTOCADO (reusa os internos V2-B como biblioteca; o weld é B3).

## Fluxo (com rastreabilidade)
```
input → particionamento greedy (decide por BYTES REAIS) → encode V0/V1/B2 → RT → medida 3-vias
```
- **V0** = baseline REAL do pipeline: `@dict` V2-B (low-card) OU OBAT/HCC (high-card, K>1024).
- **V1** = per-column dict SEM o cap 1024 (dict-mas-não-compartilhado) → isola dict-vs-OBAT/HCC.
- **B2** = group-dict compartilhado (prelúdio + colunas `&<G>` stream-only).
- **Decomposição**: `total (B2 vs V0) = (a) dict-vs-OBAT/HCC [V1 vs V0] + (b) cross-dict share [B2 vs V1]`.
  **(b) é o valor real do B2**; (a) é achado separado.

## Arquivos
- [`b2proto.py`](b2proto.py) — core: `partition` (greedy custo-modelado por bytes reais),
  `encode_v0/encode_b2/decode` (formato `&<G>` com prelúdio length-prefixed), codec V2-B reusado.
- [`run.py`](run.py) — driver: ilustrativo + reais (SNAP/OpenFlights de Z:) + escala/borda; emite artefatos.
- [`artifacts/`](artifacts/) — rastreabilidade do caso ilustrativo:
  - `01-input.txt` — colunas + únicos + Jaccard
  - `02-partition-decisao.txt` — a dobradiça (v0_body vs b2_body → pool?)
  - `03-obat-hcc-uniao.txt` — **OBAT log + HCC trace da tabela de união** (mostra dedup não-linear)
  - `04-blob-v0.tcf.txt` / `05-blob-b2.tcf.txt` — os blobs byte-a-byte (inspecionáveis)
  - `06-roundtrip-medida.txt` — RT + decomposição 3-vias
- Dados reais: `Z:/tcf-data/external/` (SNAP, OpenFlights) — ver [B1 provenance](../2026-06-21-gdict-caracterizacao/datasets-provenance.md).

## Rodar
```bash
python experiments/lab/dirty/2026-06-27-gdict-b2-prototype/run.py
```
Resultados e veredito: [result.md](result.md).
