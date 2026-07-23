# Proveniência — telemetria decide o modo por lote

**Origem**: 100% sintético/determinístico. Nenhum dado real, nenhum download. Ruído via LCG local
(seeds fixas por bloco), reprodutível byte-a-byte, sem `random` global. Domínio bool, bit1=true.

**Dados PEQUENOS/heterogêneos de propósito** (viabilidade efêmera). Construídos para exercitar o
contraste modo-único vs por-lote:
- `blocky` (n=256) / `blocky-big` (n=2048) — blocos alternados de run (all-true) e ruído 50%; o
  `-big` existe só para ver a **amortização** do manifesto quando n cresce (não é teste massivo, é o
  mínimo pra o overhead fixo parar de dominar).
- `half-half` (n=256) — metade run, metade ruído: o caso limpo onde 2 lotes bastam.
- `runny` (6% true) / `noisy` (50%) / `alt` — homogêneos, controle: por-lote NÃO deve ganhar.

**Viés declarado**: os blocos têm tamanho 32/128 alinhados a alguns S testados — isso FAVORECE o
batch-dyn quando S casa a fronteira. É proposital (mostra o teto do ganho) e está dito: o resultado
diz "quando a granularidade casa o regime", não "sempre". Desalinhamento perde — é a ressalva.

**Reprodutibilidade**: `python run.py` regenera. RT self-contained por lote (decode==orig==json_rt);
fonte instrumentada prova passe único (`reads/n==1.0`). Bytes só com RT ✅. Comparação corpo-vs-corpo
(framing genérico fora) para isolar a composição.
