# Telemetria decide o modo POR LOTE (RLE vs base64) — CORPO-vs-corpo

Bool heterogêneo, dados pequenos. Compara o CORPO de cada composição (o framing genérico magic+S+n é igual pra todas e fica de fora; o manifesto `RDDR` É custo do batch-dyn). `whole-*`=1 modo/coluna; `batch-dyn/S`=modo por lote pela telemetria. `reads/n` 1.0=passe único; RT self-contained.

| caso | n | whole-dense | whole-rle | whole-best | bd/32 | bd/64 | bd/128 | melhor corpo | Δ vs best | reads/n | RT |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|---:|:---:|:---:|
| blocky | 256 | 44 | 147 | 44 | 64 | 56 | 52 | whole-dense | +8 | 1.0 | ✅ |
| blocky-big | 2048 | 344 | 1028 | 344 | 512 | 320 | 264 | bd/128 | -80 | 1.0 | ✅ |
| half-half | 256 | 44 | 116 | 44 | 64 | 40 | 33 | bd/128 | -11 | 1.0 | ✅ |
| runny | 256 | 44 | 106 | 44 | 80 | 56 | 52 | whole-dense | +8 | 1.0 | ✅ |
| noisy | 256 | 44 | 277 | 44 | 80 | 56 | 52 | whole-dense | +8 | 1.0 | ✅ |
| alt | 256 | 44 | 513 | 44 | 80 | 56 | 52 | whole-dense | +8 | 1.0 | ✅ |

## Leitura (telemetria por lote + composição)

- **Medição justa (corpo)**: o framing genérico é o mesmo pra todos; o que se compara é a COMPOSIÇÃO. `Δ vs best` < 0 = o dinâmico-por-lote bate o melhor modo único.
- **A telemetria já resolve a decisão**: por lote, denso=`b64_len(S)` (fórmula grátis) e rle=soma sobre os runs do lote (do scan que você já faz) — os mesmos números que o pipeline conta 'no processo, não no fim' (emitted_bytes/mode, side_outputs.py:62-67), só que por LOTE. Materializa só o vencedor.
- **Passe único preservado**: `reads/n==1.0` mesmo fatiando (fatias disjuntas).
- **Onde ganha vs onde o overhead do manifesto pesa**: ver `Δ` e o `S` vencedor por caso — heterogêneo grande favorece o dinâmico; homogêneo/pequeno favorece modo único (manifesto por lote não se paga). A GRANULARIDADE (S, e lote-vs-coluna) é mais um número que a telemetria escolhe — não um valor fixo.
- **Composição = a alavanca / paralelismo**: o manifesto `RDDR...` É a forma do arquivo mudando por lote; lotes são unidades INDEPENDENTES (encoda/decoda sozinhas) — base pra liberar/paralelizar por estágio. Trade explícito: fixo=paralelizável mas paga fronteira; adaptativo (fronteira só na virada de regime, como o seq-RLE) comprime mais mas é menos paralelizável. A telemetria informa os dois lados.

**6 casos × 3 lotes · 0 falhas (RT + passe único).** Regenera: `python run.py`.