---
title: Encodings avancados inspirados em SQL Server columnstore — delta, FOR, value encoding
type: hypothesis
status: OPEN
priority: HIGH
created: 2026-04-10
origin: Usuario apontou que RLE sozinho e generalista demais; SQL Server usa multiplas tecnicas
parent: H-compression-layers
---

# Encodings Avancados Inspirados em Columnstore

## Motivacao

TCF atual tem 4 niveis (L0-L3) que combinam: expanded → RLE → sort+RLE
→ dict+sort+RLE. Mas **SQL Server columnstore** (referencia do dominio)
usa um conjunto muito mais rico de tecnicas combinadas:

| Tecnica | SQL Server | TCF atual |
|---------|------------|-----------|
| Dictionary encoding | Sim | Sim (L3) |
| Run-Length Encoding | Sim | Sim (L1+) |
| **Value encoding numerico** | Sim | **Nao** |
| **Delta encoding** | Sim (implicito) | **Nao** |
| **Frame-of-Reference (FOR)** | Sim | **Nao** |
| Bit packing | Sim (binario 1-21 bits) | N/A (textual) |
| Min/max por segmento | Sim | Parcial (STATS global) |
| Archival (XPRESS) | Sim | Externo (gzip) |

Fonte: [SQL Server Columnstore docs](https://learn.microsoft.com/en-us/sql/relational-databases/indexes/columnstore-indexes-overview)

**RLE sozinho e insuficiente** para dados numericos sequenciais ou com
pequenas variacoes. E ai que os encodings avancados brilham.

## Hipoteses concretas

### H-enc-1: Delta encoding para sequencias monotonicas

**Caso tipico:** IDs incrementais, timestamps, datas, contadores.

```
Original L0: id: 1001 1002 1003 1004 1005 1006 1007 1008
RLE L1:      id: 1001 1002 1003 1004 1005 1006 1007 1008  (nao ajuda!)
Delta:       id: base=1001 deltas=+1+1+1+1+1+1+1
Delta+RLE:   id: base=1001 deltas=7*+1
```

**Ganho potencial:** reducao drastica em colunas sequenciais.

**Onde importa no retail_sales:**
- `dt` (data) — eventos em ordem cronologica
- `preco_unit` — pode ter sequencias de ajustes
- `id` (pk) — geralmente incremental

### H-enc-2: Frame-of-Reference (FOR) para numericos com pequena variacao

**Caso tipico:** precos em faixa estreita, temperaturas, scores.

```
Original L0: preco: 1200 1215 1230 1225 1210 1205 1235 1240
RLE L1:      preco: 1200 1215 1230 1225 1210 1205 1235 1240  (nao ajuda)
FOR:         preco: base=1200 offsets: 0 15 30 25 10 5 35 40
```

Os offsets tem menos digitos → menos caracteres/tokens.

**Onde importa:**
- `preco_unit` em catalogo estavel
- `total` quando os pedidos sao de tamanho similar
- Qualquer metrica normalizada

### H-enc-3: Value encoding numerico textual

**Caso tipico:** floats com muitas casas decimais mas precisao de 2.

```
Original L0: total: 147445.47 12500.00 8932.15
Value-enc:   total[x100]: 14744547 1250000 893215  (remove ponto decimal)
Value-enc+bit: total[x100,digits=8]: 14744547 1250000 00893215  (padding uniforme)
```

Benefeciaria tokenizacao BPE? Precisa testar — numeros sem ponto
podem tokenizar melhor (tokens numericos frequentes no treino).

### H-enc-4: Chunking com min/max local

**Caso tipico:** dataset grande (1000+ rows) onde STATS global atrapalha
(F81 mostrou que STATS confunde em queries per-group).

```
## vendas n=1000 sorted_by=dt
# STATS_local chunk=1-100: sum=14230.50 min=2.50 max=89.90
# STATS_local chunk=101-200: sum=13980.25 min=3.10 max=91.20
...
```

Beneficios:
- LLM ve STATS local relevante ao subgrupo
- Permite queries "total do primeiro trimestre" com hints
- Menos dependencia de STATS global

Relaciona-se com **E-stats-ablation** (F90-F94) — se STATS ajudam tanto,
STATS granulares podem ajudar mais em queries per-group.

## Implementacao textual (nao binaria)

**Importante:** TCF e textual. Nao podemos usar bit packing como o
SQL Server. Mas podemos usar **equivalentes textuais:**

| SQL Server (binario) | TCF (textual) |
|----------------------|---------------|
| Bit packing 1-10 bits | Reducao de digitos (`14744547` vs `147445.47`) |
| Value encoding int | Remove ponto decimal + fator escala no header |
| Delta encoding int | `base=X deltas=Y Z W...` notacao |
| Frame-of-Reference | `offset_from=X: Y Z W` notacao |
| Segment min/max | `# STATS_local chunk=A-B: ...` |

## Niveis propostos (v0.3 futuro)

Atual:
- L0: expanded
- L1: RLE
- L2: sort + RLE
- L3: dict + sort + RLE

Proposto:
- L0: expanded
- L1: RLE
- L2: sort + RLE
- L3: dict + sort + RLE (atual)
- **L4: + delta encoding para sequencias** (NOVO)
- **L5: + Frame-of-Reference para numericos** (NOVO)
- **L6: + value encoding + chunking STATS** (NOVO)

Cada nivel e **estritamente mais agressivo** que o anterior.
Usuario escolhe tradeoff entre compressao e legibilidade.

## Decisao importante

Esses encodings podem:
1. **Comprimir mais** (menos bytes/tokens)
2. **Atrapalhar LLMs** (mais complexo de interpretar)
3. **Confundir gzip** (como RLE pode fazer — ver P-rle-vs-gzip)

**Teste empirico necessario** — nao presumir beneficios.

## Relacao com outros tickets

- **H-compression-layers**: niveis progressivos (parent ticket)
- **P-rle-vs-gzip**: investiga se RLE atrapalha gzip; mesma pergunta para delta/FOR
- **E-token-count**: mede se novos encodings tokenizam melhor ou pior
- **H-smart-rounding**: arredondamento pode amplificar efeito de value encoding
- **G-utility-analysis**: novas dimensoes para o mapa
- **T-multi-lang**: novos encodings complicam decoders em outras linguagens

## Tarefas

- [ ] Implementar delta encoding como `compression.py` nova primitiva
- [ ] Implementar FOR (Frame-of-Reference)
- [ ] Implementar value encoding textual (x10, x100 factor)
- [ ] Implementar chunked STATS (min/max por chunk)
- [ ] Benchmark: L4/L5/L6 vs L0-L3 em dados monotonicos
- [ ] Testar accuracy LLM com novos encodings
- [ ] Testar se gzip ainda ajuda apos esses encodings
- [ ] Decidir se promove a L4-L6 ou mantem como experimental
