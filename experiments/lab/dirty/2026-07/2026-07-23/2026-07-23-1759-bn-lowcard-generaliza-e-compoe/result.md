# bN generalizado (bool + low-card) — as peças conversam?

Kit `pecas.py`: cardinalidade→largura `w`, compondo com segmentação adaptativa. Corpo-vs-corpo (domínio embutido reportado à parte). `Δadapt` = seg-adapt − best (<0 ganha). `reads/n` 1.0=passe único. RT = decode→índices→domínio == original == JSON.

| caso | k | w | n | domínio B | dense | rle | best | seg-adapt | Δadapt | reads/n | RT |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| k2-runny | 1 | 1 | 512 | 2 | 88 | 5 | 5 | 6 | +1 | 1.0 | ✅ |
| k2-noisy | 2 | 1 | 512 | 5 | 88 | 2047 | 88 | 93 | +5 | 1.0 | ✅ |
| k2-hetero | 2 | 1 | 512 | 5 | 88 | 816 | 88 | 98 | +10 | 1.0 | ✅ |
| k4-runny | 2 | 1 | 512 | 5 | 88 | 106 | 88 | 109 | +21 | 1.0 | ✅ |
| k4-noisy | 4 | 2 | 512 | 11 | 172 | 2047 | 172 | 177 | +5 | 1.0 | ✅ |
| k4-hetero | 4 | 2 | 512 | 11 | 172 | 734 | 172 | 143 | -29 | 1.0 | ✅ |
| k16-runny | 8 | 4 | 512 | 26 | 344 | 83 | 83 | 100 | +17 | 1.0 | ✅ |
| k16-noisy | 16 | 4 | 512 | 53 | 344 | 2239 | 344 | 349 | +5 | 1.0 | ✅ |
| k16-hetero | 16 | 4 | 512 | 53 | 344 | 886 | 344 | 208 | -136 | 1.0 | ✅ |

## Leitura — as peças conversam?

- **SIM, compõem mecanicamente**: a MESMA peça `seg_adapt(runs, w)` roda pra k∈{2,4,16} (w=1/2/4) sem código novo — só `w` muda (de `width_for(k)`). RT fecha nos 9 → cardinalidade→largura casa com a segmentação. Bool = caso w=1 com domínio implícito.
- **Passe único preservado** (`reads/n==1.0`): 1 scan constrói domínio + índices + runs juntos. A telemetria (k, runs) sai desse mesmo passe.
- **MAS seg-adapt NÃO é vitória geral** (corrige o otimismo anterior): ele só bate o melhor modo único em dados GENUINAMENTE MISTOS e w≥2 — `k4-hetero` −29, `k16-hetero` −136. Em dados UNIFORMES perde: `runny` (k4 +21, k16 +17) o whole-rle compacto já ganha; `noisy` (+5) o whole-dense já ganha; e em k2 (bool) o piso denso é tão baixo (1 bit/elem) que o misto quase nunca compensa (k2-hetero +10). A segmentação por-segmento só paga quando NENHUM modo único é bom o tempo todo.
- **w AMPLIFICA o ganho do misto**: quanto maior o piso denso (w maior), mais os segmentos RLE têm o que bater → o ganho no heterogêneo cresce com k (−29 em w=2, −136 em w=4). Bool (w=1) é o pior caso pro misto.
- **FLOOR é obrigatório, não opcional**: como seg-adapt perde na maioria, ele SÓ é seguro competindo em `min(whole-dense, whole-rle, seg-adapt)` — aí os +Δ viram fallback pro modo único e o líquido é nunca-pior. A peça a soldar é o FLOOR/min (já é padrão), com seg-adapt como mais um candidato — não seg-adapt como default.
- **Custo novo do bN vs bool**: o `domínio B` (bool tem domínio implícito {0,1}; low-card embute os k distintos). Constante aditivo aos 3 modos — não muda QUAL vence, mas conta no total.
- **Seguro soltar/manter?** As peças são lab-local, compõem por contrato estreito (`runs`+`w`) e são reusáveis pelos próximos SEM tocar src/tcf. A 'terceira desavio' (integração) NÃO é incompatibilidade entre as peças (elas conversam) — é o ponto-de-seleção inexistente no `.8H`, que segue sendo o risco real de weld.

**9 casos · 0 falhas (RT + passe único).** Regenera: `python run.py`.