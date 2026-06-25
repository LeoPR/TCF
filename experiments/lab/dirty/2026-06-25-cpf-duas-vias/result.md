# Piloto CPF — fluxo de duas vias (H-NAT-SPEC), eixo compressao [probatorio]

**Data**: 2026-06-25. Read-only (`medir.py`). N=2000 CPFs/regime.

| regime | raw(mask) | base94(nat) | 9dig-OBAT | 11dig+DV |
|---|---|---|---|---|
| ALEATORIO | 37858 | **13682** | 23793 | 27793 |
| CADENCIADO | 25005 | 11328 | **74** | 12575 |

## Achados
1. **CPF real (aleatorio) -> base94 ganha** (13682 < 23793). Digitos aleatorios nao
   comprimem; modo-1 (hibrido) degrada pro base94. CPF NAO consome o fluxo (compressao).
2. **Cadenciado -> digitos+pipeline esmagam base94** (74 vs 11328, ~150x): seq-RLE pega a
   cadencia dos digitos; base94 de inteiros consecutivos nao cadencia.
3. **Dropar o DV e' critico** (cadenciado: 9dig=74 vs 11dig+DV=12575): o DV mod-11 quebra
   a cadencia.

## Conclusao (fecha H5)
O consumidor do modo-1 (normalizar+pipeline) NAO e' o CPF (aleatorio->base94) — e' o **ID
FORMATADO SEQUENCIAL** (NF-e, fatura, codigo sequencial), onde o formato ESCONDE a cadencia
e a normalizacao a expoe. Precedente vivo: nature de IP (normaliza->seq-RLE pra subnet).
"per-spec flow mode" e', na pratica, **"per-DATA-SHAPE"**: aleatorio->base94(no-obat/perf);
formatado-sequencial->normalizar(modo-1/compressao); bypass(modo-3)=streaming, ortogonal.
