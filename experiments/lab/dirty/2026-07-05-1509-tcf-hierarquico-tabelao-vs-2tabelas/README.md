# 2026-07-05 15:09 — TCF hierárquico: tabelão (A) vs duas tabelas (B) [probatório]

**Auto-contido** (dirty-lab): usa só `hierlib.py` (local) + `tcf` (biblioteca; **não toca `src/`**).
`python run.py` regenera **todos** os artefatos. Ticket: [T-STUDY-HIERARCHICAL-TCF](../../../../tickets/T-STUDY-HIERARCHICAL-TCF.md).

> Repete — organizado e rastreado — o estudo antes espalhado em `2026-07-05-json-input-estudo/`
> (removido; nome sem hora não dava ordem). Nome agora = **dia + hora-minuto + descrição** (ordenável).

## Pergunta

Como o TCF (tabular) representa uma resposta **aninhada** de API (`{equipment:{...}, day:[{...}]}`)?
- **A · tabelão (cross)**: desnormaliza (contexto repetido por linha) → 1 TCF. O RLE colapsa a repetição.
- **B · duas tabelas**: normaliza (T0 contexto 1× + T1 série + fk) + manifest → 2 TCFs ligados por cabeçalho.

## Rastreio em 4 estágios (= a ordem em `artifacts/`)

```
01 ENTRADA        inputs/S3.json → artifacts/01-entrada-S3.json
02 TRADUÇÃO       JSON aninhado → tabela(s): 02-traducao-A-tabelao.csv | 02-traducao-B-{T0,T1}.csv
                  + o mapa que preserva a hierarquia: 02-traducao-A-schema.txt | 02-traducao-B-manifest.txt
03 TCF ADAPTADO   encode real → 03-tcf-adaptado-{A,B-T0,B-T1}.tcf.txt
                  + como foi construído → 03-trace-{A,B}-obat-hcc.txt (OBAT log + HCC trace por coluna)
04 DECODE         decode → reconstrói o JSON → compara com a ENTRADA → 04-decode-roundtrip.txt (OK/MISMATCH
                  + o JSON reconstruído impresso, pra VER que voltou idêntico)
05 BYTES          medida A vs B, regime plano vs reconstrução, M=1/M=3 → 05-bytes-medida.txt
```

## Arquivos

- [`run.py`](run.py) — driver dos 5 estágios (escreve `artifacts/`). Reproduzível.
- [`hierlib.py`](hierlib.py) — engenhoca descartável: `to_tabelao`/`from_tabelao`, `to_two`/`from_two`,
  schema/manifest, síntese de escala. RT de volta ao JSON. **Não copiar pro proto formal.**
- [`inputs/`](inputs/) — fixtures (S1 request, S2 série, **S3 equipamento⊃série** = worked example). Anonimizadas.
- [`artifacts/`](artifacts/) — os 5 estágios, numerados.
- [`result.md`](result.md) — conclusão. [`datasets-provenance.md`](datasets-provenance.md) — origem/anonimização.

## Estado (era / foi / é / será)

- **É**: pipeline S3 → A/B → TCF → decode → bytes, rastreado nos 5 estágios; decode reconstrói o JSON (OK).
- **Foi**: `2026-07-05-json-input-estudo` (mesmo estudo, nome sem ordem) — **substituído** por este.
- **Será** (progressão pendente): realista (>1k linhas, contexto pesado) → bordas (M=1, 1 ponto, colunas
  100% const/distintas) → extrapolação (M grande, crossover fora do ruído) → gate real-world.

## Conclusão (andamento próprio)

Ver [result.md](result.md). Em uma linha: **reconstrução do JSON → B vence nos dois M** (medido,
reproduzível); **plano → empate no ruído** (<1KB). Princípio: a multiplicidade ×N é conservada — **RLE e
referência são duais**; o schema não compra compressão, compra reconstrução. Segue as
[convenções do dirty-lab](../notas/dirty-lab-convencoes.md).
