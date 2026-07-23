# Proveniência — bN low-card generaliza e compõe

**Origem**: 100% sintético/determinístico. Nenhum dado real, nenhum download. Ruído/runs via LCG
local (`_lcg`, seeds fixas por regime: runny=11, noisy=23, hetero=37; sem `hash()` randomizado).
Valores = categorias `c0..c{k-1}` (low-card strings).

**Grade**: k∈{2,4,16} × regime∈{runny, noisy, hetero}, n=512. Cobre bool (k=2, w=1) e low-card
(k=4→w=2, k=16→w=4). w=8/k≤256 NÃO exercitado (limite declarado).

**Regimes (propositais, SEM parâmetro alinhado embutido — a lição do lab 1548)**:
- `runny` — runs longos de comprimento VARIÁVEL (8..47); baixa entropia → whole-rle deve ganhar.
- `noisy` — 1 símbolo aleatório por posição; alta entropia → whole-dense deve ganhar.
- `hetero` — blocos alternados run(20..79)/ruído(15..59), tamanhos VARIÁVEIS → sem alinhamento a
  parâmetro fixo (seg-adapt é adaptativo, não tem S; por construção imune ao artefato da v1 do 1548).

**Nota**: `k2-runny` degenerou pra k=1 (o LCG escolheu 1 só categoria em 512) — caso-limite legítimo,
mantido. A cardinalidade REAL medida é a do domínio observado, não a nominal.

**Reprodutibilidade**: `python run.py` regenera. RT dos 3 modos → índices → domínio → valores ==
original == json_rt. Fonte instrumentada prova passe único. Bytes só com RT ✅. Comparação
corpo-vs-corpo (domínio embutido reportado à parte, constante aditivo).
