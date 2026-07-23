# bN generalizado (bool + low-card) — as peças conversam?

Kit `pecas.py`: cardinalidade→largura `w`, compondo com segmentação adaptativa. Corpo-vs-corpo (domínio embutido reportado à parte). `Δadapt` = seg-adapt − best (<0 ganha). `reads/n` 1.0=passe único. RT = decode→índices→domínio == original == JSON.

| caso | k | w | n | domínio B | dense | rle | best | seg-adapt | Δadapt | reads/n | RT |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| k2-runny | 2 | 1 | 512 | 5 | 88 | 93 | 88 | 111 | +23 | 1.0 | ✅ |
| k2-noisy | 2 | 1 | 512 | 5 | 88 | 2047 | 88 | 93 | +5 | 1.0 | ✅ |
| k2-hetero | 2 | 1 | 512 | 5 | 88 | 816 | 88 | 98 | +10 | 1.0 | ✅ |
| k4-runny | 4 | 2 | 512 | 11 | 172 | 107 | 107 | 136 | +29 | 1.0 | ✅ |
| k4-noisy | 4 | 2 | 512 | 11 | 172 | 2047 | 172 | 177 | +5 | 1.0 | ✅ |
| k4-hetero | 4 | 2 | 512 | 11 | 172 | 734 | 172 | 143 | -29 | 1.0 | ✅ |
| k16-runny | 15 | 4 | 512 | 49 | 344 | 79 | 79 | 94 | +15 | 1.0 | ✅ |
| k16-noisy | 16 | 4 | 512 | 53 | 344 | 2239 | 344 | 349 | +5 | 1.0 | ✅ |
| k16-hetero | 16 | 4 | 512 | 53 | 344 | 886 | 344 | 208 | -136 | 1.0 | ✅ |

## Leitura — as peças conversam?

- **A CADEIA VERTICAL compõe** (é o que o RT prova): `build_and_scan → width_for(k) → codec(runs,w) → decoder → domínio`. A mesma `seg_adapt(runs,w)` roda em w=1/2/4 sem código novo, RT fecha nos 9. Os 3 modos (dense/rle/seg-adapt) NÃO se encadeiam — são SUBSTITUÍVEIS sob o contrato comum `(runs,w)`, unificados por um `min()` externo.
- **Passe único preservado** (`reads/n==1.0`): 1 scan constrói domínio + índices + runs juntos; os encoders consomem `runs` (nunca a fonte). A telemetria sai desse passe.
- **seg-adapt NÃO é vitória geral** (corrige o otimismo anterior): perde em 7/9. Só bate o modo único em MISTO genuíno e w≥2 — `k4-hetero` −29, `k16-hetero` −136. Em UNIFORME perde: `runny` o modo compacto já ganha (whole-rle p/ k≥4: k4 +29, k16 +15; whole-dense p/ bool k2 +23), `noisy` o whole-dense ganha (+5), e em bool k2 o piso denso baixo faz o misto perder também no hetero (+10). Segmentar só paga quando NENHUM modo único é bom o tempo todo.
- **w AMPLIFICA o ganho do misto**: piso denso maior → segmentos RLE têm mais o que bater → o ganho no heterogêneo cresce com k (−29 em w=2, −136 em w=4). Bool (w=1) é o PIOR caso pro misto — o oposto do otimismo inicial.
- **FLOOR obrigatório**: como seg-adapt perde na maioria, só é seguro em `min(whole-dense, whole-rle, seg-adapt)` — os +Δ viram fallback e o líquido é nunca-pior. A peça a soldar é o FLOOR/min (já padrão), com seg-adapt como candidato, não default. RESSALVA: este `min` é só de bytes-de-corpo; NÃO conta o byte do seletor de modo nem o custo de computar os 3 — em payload minúsculo (k2-runny rle=88 vs seg-adapt=111) 1 byte importa.
- **Custo do bN low-card = domínio embutido** (`domínio B`: 5→11→53 conforme k). NOTA: este lab usa categorias-string `c0/c1`, então k=2 TAMBÉM paga domínio (5B) — a economia de um bool REAL (domínio implícito {0,1}, 0B) não é medida aqui, é conceitual. O domínio é constante aditivo aos 3 modos, não muda QUAL vence.
- **Seguro soltar/manter?** As peças são lab-local, substituíveis sob contrato estreito (`runs`+`w`), reusáveis pelos próximos SEM tocar src/tcf. Este lab DESCARTA incompatibilidade entre as peças (RT fecha), mas NÃO mede integração — o `.8H` nunca é tocado. Logo o ponto-de-seleção inexistente no `.8H` é o risco de weld por ELIMINAÇÃO (hipótese herdada), não uma medição deste lab.

**9 casos · 0 falhas (RT + passe único).** Regenera: `python run.py`.