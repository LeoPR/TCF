# 2026-07-23-1759 — bN generalizado (bool + low-card) e as peças se compõem?

Micro-lab EXPERIMENTAL. Pedido do owner: não só bool — "elementos de poucos que caibam no bN". E
refletir se é **seguro soltar peças e mantê-las pros próximos**, vendo se compõem. Este lab exercita
um **kit lab-local** ([`pecas.py`](pecas.py)): cardinalidade → largura `w` (bN) compondo com a
segmentação adaptativa por regime (do estudo bool). Continua
[lote/adaptativo `1548`](../2026-07-23-1548-telemetria-decide-lote-rle-vs-b64/).

## O kit (reusável pelos próximos, sem tocar src/tcf)

`pecas.py` expõe um contrato estreito sobre `runs = [(idx,len)]` + `w`:
`build_and_scan` (1 passe → domínio + runs) · `width_for(k)` · `enc_dense`/`enc_rle`/`seg_adapt(runs,w)`
+ decoders. Bool = caso `w=1` domínio implícito; low-card = `w∈{2,4,8}` domínio embutido.

## Evidência (9/9 RT + passe único ✅; Δadapt = seg-adapt − melhor modo único, no corpo)

| caso | k / w real | melhor modo único | seg-adapt | Δadapt |
|---|---|---|---:|---:|
| k4-**hetero** | 4 / 2 | dense 172 | 143 | **−29** |
| k16-**hetero** | 16 / 4 | dense 344 | 208 | **−136** |
| k2-hetero | 2 / 1 | dense 88 | 98 | +10 |
| k4-runny | 4 / 2 | rle 107 | 136 | +29 |
| k16-runny | 15 / 4 | rle 79 | 94 | +15 |
| k2-runny | 2 / 1 | dense 88 | 111 | +23 |
| *-noisy (k2/4/16) | — | dense | — | +5 |

## Conclusão honesta

- **A CADEIA VERTICAL compõe** (o que o RT prova): `build_and_scan → width_for(k) → codec(runs,w) →
  decoder → domínio`. A mesma `seg_adapt(runs,w)` roda em w=1/2/4 sem código novo, RT fecha nos 9,
  passe único (`reads/n==1.0`). **Os 3 modos NÃO se encadeiam** — são SUBSTITUÍVEIS sob o contrato
  comum `(runs,w)`, unificados por um `min()` externo. "Compõem" = cadeia vertical, não trio.
- **seg-adapt NÃO é vitória geral** (perde em 7/9): só bate o modo único em **misto genuíno e w≥2**
  (`k4/k16-hetero`). Em uniforme perde — `runny` o modo compacto ganha (whole-rle p/ k≥4, whole-dense
  p/ bool), `noisy` o whole-dense; e em **bool (w=1)** o piso denso baixo faz o misto perder até no
  hetero (+10).
- **w amplifica o ganho do misto**: piso denso maior → segmentos RLE têm mais o que bater (−29 em w=2,
  −136 em w=4). Bool é o **pior** caso pro misto — o oposto do otimismo inicial.
- **FLOOR obrigatório**: seg-adapt só é seguro em `min(whole-dense, whole-rle, seg-adapt)` — os +Δ
  viram fallback, líquido nunca-pior. **A peça a soldar é o FLOOR/min (já padrão), seg-adapt como
  candidato, não default.** RESSALVA: este `min` é só de bytes-de-corpo — não conta o byte do seletor
  de modo nem o custo de computar os 3 candidatos (em payload minúsculo, 1 byte importa).
- **Custo do bN low-card = domínio embutido** (5→11→53 conforme k). NOTA: este lab usa strings
  `c0/c1`, então k=2 TAMBÉM paga domínio — a economia de um bool REAL (domínio implícito, 0B) é
  conceitual, não medida aqui.

## Reflexão sobre soltar/manter (a pergunta do sequenciamento)

Seguro **manter as peças no lab** (contrato estreito, substituíveis, zero `src/tcf`). Sobre a "terceira
desavio": este lab **descarta incompatibilidade ENTRE as peças** (RT fecha), mas **não mede integração**
— o `.8H` nunca é tocado. Então o ponto-de-seleção inexistente no `.8H` é o risco de weld **por
eliminação** (hipótese herdada dos labs anteriores), não uma medição deste lab. Conclusão prática: as
peças conversam no nível-lab; o risco real de weld segue sendo o arnês, mas isso é apontado, não provado
aqui.

## O que NÃO está provado / rodar

Dados sintéticos pequenos; low-card só até k=16 medido (w=8/k≤256 não exercitado); domínio embutido
como newline-join (não otimizado). `python run.py` — 9 casos, 0 falhas. Protótipos lab-local.
