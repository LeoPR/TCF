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

## Evidência (9/9 RT + passe único ✅)

| regime | k=2 (w1) | k=4 (w2) | k=16 (w4) |
|---|---|---|---|
| runny | +1 | +21 | +17 |
| noisy | +5 | +5 | +5 |
| **hetero** | +10 | **−29** | **−136** |

(Δadapt = seg-adapt − melhor modo único, no corpo; <0 = seg-adapt ganha.)

## Conclusão honesta

- **As peças COMPÕEM mecanicamente** — resposta ao "conversam?": **sim**. A mesma `seg_adapt(runs,w)`
  roda pra k∈{2,4,16} sem código novo (só `w` muda), RT fecha nos 9, passe único preservado
  (`reads/n==1.0`). Cardinalidade→largura casa com a segmentação.
- **Mas seg-adapt NÃO é vitória geral**: só bate o modo único em dados **genuinamente mistos e w≥2**
  (`k4/k16-hetero`). Em uniformes perde — `runny` o whole-rle compacto já ganha, `noisy` o whole-dense,
  e em **bool (w=1) quase nunca compensa** (piso denso de 1 bit/elem é baixo demais).
- **w amplifica o ganho do misto**: piso denso maior → segmentos RLE têm mais o que bater (−29 em w=2,
  −136 em w=4). Bool é o pior caso pro misto — o oposto do que o otimismo inicial sugeria.
- **FLOOR é obrigatório**: como seg-adapt perde na maioria, só é seguro em `min(whole-dense, whole-rle,
  seg-adapt)` — aí os +Δ viram fallback e o líquido é nunca-pior. **A peça a soldar é o FLOOR/min (já
  é padrão), com seg-adapt como candidato — não seg-adapt como default.**
- **Custo novo do bN vs bool**: o domínio embutido (`domínio B`) — constante aditivo aos 3 modos, não
  muda qual vence, mas conta no total.

## Reflexão sobre soltar/manter (a pergunta do sequenciamento)

Seguro **manter as peças no lab** (contrato estreito, reusáveis, zero `src/tcf`). A "terceira desavio"
que o owner teme **não é incompatibilidade entre as peças** — elas conversam aqui. O risco real de
weld continua sendo estrutural: o **ponto-de-seleção inexistente no caminho `.8H` single-col**. Ou
seja: testar as peças juntas no lab (feito) NÃO elimina o risco de integração, só confirma que o risco
está no ARNÊS (onde plugar), não nas peças.

## O que NÃO está provado / rodar

Dados sintéticos pequenos; low-card só até k=16 medido (w=8/k≤256 não exercitado); domínio embutido
como newline-join (não otimizado). `python run.py` — 9 casos, 0 falhas. Protótipos lab-local.
