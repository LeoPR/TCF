# Sub-exp 04 — OBAT shape-consistency hint (H-DA-07)

**Data**: 2026-05-17
**Estado**: ativo
**Macro pai**: [`../README.md`](../README.md)
**Hipotese**: H-DA-07 (`../../notas/roadmap-hipoteses.md`)
**Depende de**: sub-exp 02 (HCC fork seq-RLE — reusado)

## Hipotese a validar

**H-DA-07**: Se OBAT, dada dica generica "prefer shape consistency",
mantiver shape P+L+S atraves de transicoes de cardinalidade (escolha
nao-greedy quando necessario), as linhas pos-transicao formam novo
seq-RLE run, recuperando bytes.

## Origem (do sub-exp 03)

Audit revelou: residual Type B em D11d/e/f/g/h = 24 bytes por dataset
(linhas pos-transicao s11/s12/s13). Razao: OBAT escolhe greedy max
LCP+LCS, mudando shape no s11 (carry 9→10). Resultado: s11 vira P+L+S
com tamanhos diferentes, s12/s13 viram P+S (sem L) — 3 shapes
distintos, sem compactacao.

## Solucao proposta — OBAT shape-preserve

Fork de OBAT (`obat_fork.py`) que aceita hint **generica**
`prefer_shape_consistency=True`. Comportamento:

1. Apos cada emissao, memoriza shape `(p_src, p_len, has_L, s_src, s_len)`
2. Para proxima string, tenta replicar shape:
   - **Exato**: mesmo p_src, p_len, s_src, s_len. Verifica LCP/LCS suficientes.
   - **Mais largo (fallback)**: se exato falha, reduz p_len/s_len pra
     o maximo que cabe com mesmos sources, exigindo lit > 0
3. Se nem o exato nem o largo funcionam → fallback pra greedy
4. Atualiza shape memorizada apos cada emissao

**Caracteristicas**:
- Single-pass (so' look-back via memoria)
- Memoria O(1) extra (so' last_shape)
- Hint generica (`prefer_shape_consistency=True`) — nao nomeia tipo
- src/tcf intocado (fork dirty)

## Cenario esperado (concreto em D11d)

Estado atual (apos sub-exp 02):
```
\2026-\05-\15 \09:*\0*\0*:\00       (line 1, s1)
1~2\1*4                              (line 2, s2)
*8+1|5\2*4                          (line 3, run s3-s10)
1\1*3,4                              (line 4, s11 — Type B)
1~15,6,4                             (line 5, s12 — Type B)
16,7,4                               (line 6, s13 — Type B)
                                     Total: 73 bytes
```

Esperado com H-DA-07:
- s11 forcado a shape (1, 14, True, 1, 3) → body `1\10*4`
- s12 forcado mesma shape → body `1\11*4`
- s13 forcado mesma shape → body `1\12*4`
- seq-RLE compacta s11-s13: `*3+1|1\10*4`

```
\2026-\05-\15 \09:*\0*\0*:\00       (line 1)
1~2\1*4                              (line 2)
*8+1|5\2*4                          (line 3, run s3-s10)
*3+1|1\10*4                         (line 4, NOVO run s11-s13)
                                     Total esperado: ~61 bytes
```

Save: ~12 bytes/dataset. Em 5 datasets (D11d-h): ~60 bytes.

## Hipoteses derivadas (testar tambem)

Pode acontecer:

**H-DA-07a**: H-DA-07 funciona como esperado nos datasets cadencia
regular (D11d-h).

**H-DA-07b**: H-DA-07 PIORA bytes em alguns datasets (greedy era
melhor, hint forca pior coverage). Notavel em D11b (bordas).

**H-DA-07c**: H-DA-07 nao muda nada em D11a/D11c (cadencia ja' captada
bem por greedy + seq-RLE existente).

Medir tudo.

## Validacao

Pra cada D11a-h:
- bytes canonical (sub-exp 01)
- bytes com tentativa 02 (HCC fork sozinho)
- **bytes com H-DA-07 (OBAT fork + HCC fork)** ← novo
- RT byte-canonical (decode espelho funciona?)

**Aceite**:
- RT 8/8 OK (obrigatorio)
- Ganho mensuravel em pelo menos 1 dataset (alem do tentativa 02)
- Sem regressao grosseira em outros (>= -5% aceitavel)

## Estrutura

```
04-obat-shape-consistency-hint/
├── README.md          (plano)
├── obat_fork.py       (processar com hint)
├── run.py             (executor + comparativo)
├── result.md          (analise pos-execucao)
└── outputs/<ds>/
    ├── 1-tokens-canonical.txt    (do baseline)
    ├── 2-tokens-fork.txt          (NOVO — H-DA-07)
    ├── 3-body-fork-canonical-obat.tcf  (tentativa 02 puro)
    ├── 4-body-fork-fork-obat.tcf       (H-DA-07 — NOVO)
    ├── 5-rt-status.txt
    └── 6-diff-bodies.md
```
