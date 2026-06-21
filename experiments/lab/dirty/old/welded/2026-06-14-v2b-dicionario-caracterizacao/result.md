# V2-B — dicionario/categorico (lossless, order-free): caracterizacao

**Data**: 2026-06-14 · **Status**: confirmada-empirica · confianca: Alta ·
**Tipo**: [probatorio] · FORK exploratorio (nao toca src/tcf)

## Ponto cego (ADR-0018 §V2-B)

Coluna low-card de N linhas, K unicos. Hoje o HCC deduplica os K e emite
1 whole-value ref `^idx\n` por linha repetida — `^` + indice decimal + `\n`
~ 3-4 bytes/linha. Pra K=24, N=8000 isso e' ~28KB (`beijing.hour`: tcf=28927)
contra ~4.6KB de entropia real. O fallback 0.7 (V2-A) so' troca por raw
(~3 bytes/linha = 20661) — melhor, mas ainda 4.5x acima do piso.

## Desenho medido

V2-B separa a coluna em **[TABELA de unicos: `encode(unicas)`]** +
**[STREAM de indices]**, 1 char por linha (alfabeto printable 0x21..0x7E = 94
chars; K<=94 -> 1 char). Order-free: nao depende da ordem. Variantes medidas:

- `v2b` (packed): stream = N chars contiguos.
- `v2bRLE`: runs `*<count><char>` no stream (ganha em adjacencia natural).
- `v2bSrt`: idem com valores ordenados (combina com `sort_by`/O-FMT-02).

## Resultados (8 datasets reais, ROWS=8000, RT 42/42 OK)

### Por-coluna (42 colunas low-card, K<=96)
```
soma base(min tcf,raw)=575570
  v2b order-free = 208646  (63.7%)
  v2b sorted     =   7567  (98.7%)   <- combinado com sort_by
  piso entropia  = 148107  (74.3%)
```
v2b order-free vence o fallback em 37/42 colunas. As 5 que perdem (ibge
uf/regiao, wine.variant) ja' estao **pre-ordenadas no dataset** -> o TCF atual
ja' as RLE-comprime (base 41-397B); a tabela+stream do V2-B so' adiciona framing.

### Ao nivel de TABELA (peso real-world) — V2-B como 3o candidato do fallback
```
dataset        cols lowK   baseTbl  savings  gain%
adult            15   13    287615   142781  49.6%
beijing          13    9    167791    61902  36.9%
tpch-lineitem    16    8    706480   103963  14.7%
wine             13    3    298001    23785   8.0%
receita           8    3    307987    18495   6.0%
br-pessoas        6    1    535786    15927   3.0%
online-retail     8    1    174803      105   0.1%
ibge              8    4    159587        0   0.0%
WEIGHTED                   2638050   366958  13.9%
```

## Decisao de desenho (zero-regressao por construcao)

V2-B entra como **3o candidato do fallback per-coluna**: `min(tcf, raw, v2b)`.
- Onde V2-B nao vence (ibge pre-ordenado, high-card), o fallback mantem o atual.
  ibge = 0.0% gain (V2-B nunca vence -> nenhuma coluna trocada). **Sem regressao.**
- Gating barato: so' tenta V2-B quando `n_unicas` (ja' em column_features) e'
  baixo e ha' repeticao (K < N). idx_width derivavel de K.

## Checklist "confirmada-empirica" (CLAUDE.md)
1. Real-world testado? **Sim** — 8 datasets reais (Adult, TPC-H, beijing, wine,
   receita, br-pessoas, ibge, retail).
2. N >= 5 fontes? **Sim** (8).
3. Sintetico vs real? N/A — tudo real.
4. Vies declarado? N/A.
5. Bytes absolutos >= 5% weighted? **Sim** — 13.9% weighted, 367KB / 2.64MB.

## Proposta de weld (para aprovacao do owner)

1. **Formato**: novo marcador de coluna no header #TCF.7 — `@<size>=<name>`
   (dicionario), ao lado de `!` (raw) e `<size>=<name>` (tcf). Slot da coluna =
   `<ntable>\n` + `<table_text>` + `<stream>` (ntable = bytes da tabela ->
   fronteira inequivoca; width derivado de K apos decodar a tabela).
2. **encoder** (`multi.py`): per-coluna, calcula candidato V2-B quando low-card
   e escolhe `min(tcf, raw, v2b)`. Reaproveita o mecanismo V2-A.
3. **decoder** (`multi.py`): roteia `@` -> decoda tabela (single-col), le stream,
   mapeia indices de volta.
4. **GATE**: `test_real_world_snapshots.py` (retail/lineitem low-card mudam ->
   re-pin intencional, ADR-0024) + baselines + RT multi-col. ADR-0025 (weld).

**Conexoes**: ADR-0018 §V2-B · ADR-0022 (V2-A fallback, mecanismo reaproveitado)
· O-FMT-02 `sort_by` (sorted leva V2-B a 98.7%) · roadmap Pacote V2.
