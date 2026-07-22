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

## Medicao 2 (en masse N=20000, no-obat + brotli + repeticao) — 2026-06-25
| eixo | raw | base94 | nota |
|---|---|---|---|
| bytes textual | 372966 | 136413 | ganho 63.4% |
| sob brotli | 125757 | 88173 | ganho 29.9% (SOBREVIVE — dropar DV + densificar vence brotli) |
| com repeticao (25% unicos) | 186393 | 119743 | base94 + dedup compoem |

**no-obat (MEDIDO)**: OBAT acha afixo espurio em **1472/20000 (7.36%)** dos base94
aleatorios (~1% de bytes). Logo no-obat NAO e' byte-neutro pro CPF — perde ~1% pra
economizar tempo de OBAT (que nao e' o gargalo, hotspot=HCC). **CPF e' candidato FRACO a
no-obat** (derrubou o palpite "no-obat limpo").

**Martelo CPF**: base94 (validar+dropar DV) = o mais barato e ROBUSTO (sobrevive brotli
29.9%, repeticao OK). A preocupacao "natures somem sob brotli" NAO vale pro CPF.
Falta pro martelo 100%: dado real (br-identidades/Receita), delta de TEMPO do no-obat
(precisa prototipo), mix invalido.
