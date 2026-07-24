# Proveniência — fechamento hex-n (saúde vs corrupção)

**Fonte**: 100% sintético/determinístico. Nenhum dado real, nenhum download.

**Parte A (saúde)**: 127 datasets bool cobrindo N ∈ {0,1,2,3,7,8,9,15,16,17,63,64,65,99,100,
101,255,256,257,999,1000,1001,4095,4096,4097,10000,50000} — fronteiras de byte do bit-pack
(±1 em cada potência) — × regimes {all-true, all-false, alternado}; + proporções {1,5,10,25,
50,75,90,95,99}% via LCG local (seed determinística) para N∈{64,256,1000,4096}; + 12 runs
mistos (blocos aleatórios, seed 20260724) para exercitar o FLOOR core-vs-denso.

**Parte B (corrupção)**: mutações determinísticas (não aleatórias) sobre 60 wires reais gerados
na parte A: flip de 1 char em cada posição do header (índices 6-11), truncamento do corpo (−1 e
−2 chars), 1 char de lixo no fim, zero-à-esquerda no `n` hex. **Todas as saídas mutadas são
descartáveis por construção** — nenhuma reintroduzida como dado real.

**Reprodutibilidade**: `python run.py` regenera byte-a-byte (LCG + mutações determinísticas,
sem `random` não-seedado). Classificação de achados (payload/estrutural/pré-existente/novo) é
lógica, não amostral — reproduz igual a cada rodada. Zero toque em `src/tcf`.
