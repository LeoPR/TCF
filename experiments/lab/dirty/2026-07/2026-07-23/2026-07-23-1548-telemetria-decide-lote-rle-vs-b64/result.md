# Telemetria decide modo por lote: FIXO-S (frágil) vs ADAPTATIVO (robusto)

Corrigido pós-verificação (wf_876541f7). Corpo-vs-corpo. `batch-fix` = lote de S fixo; `seg-adapt` = fronteira na virada de regime (do run-list, sem S). `Δfix`/`Δadapt` = corpo − whole-best (<0 ganha do melhor modo único). `align?` = bloco casa algum S. RT + passe único.

| caso | n | whole-best | batch-fix(melhor S) | Δfix | seg-adapt | Δadapt | reads/n | RT |
|---|---:|---:|---:|---:|---:|---:|:---:|:---:|
| het-align128 | 2048 | 344 | 264 | -80 | 295 | -49 | 1.0 | ✅ |
| het-mis100 | 2000 | 336 | 384 | +48 | 314 | -22 | 1.0 | ✅ |
| het-mis77 | 1920 | 320 | 300 | -20 | 320 | +0 | 1.0 | ✅ |
| half-100-156 | 256 | 44 | 48 | +4 | 40 | -4 | 1.0 | ✅ |
| noisy | 2048 | 344 | 416 | +72 | 350 | +6 | 1.0 | ✅ |
| alt | 2048 | 344 | 416 | +72 | 350 | +6 | 1.0 | ✅ |

## Leitura corrigida

- **Batch de S FIXO é frágil a alinhamento**: ganha só quando a fronteira de regime cai em múltiplo de S (`het-align128`, Δfix<0); em blocos desalinhados (`het-mis*`, `half-100-156`) PERDE (Δfix>0). O ganho -23% da v1 era artefato de bloco==S.
- **Segmentação ADAPTATIVA é robusta**: coloca a fronteira ONDE o regime vira (do run-list), então ganha em heterogêneo INDEPENDENTE de alinhamento (Δadapt<0 em todos os het-*), e degenera pra ~1 segmento no homogêneo (Δadapt≈0, nunca-pior).
- **Custo honesto**: 'de qualquer forma' cobre SÓ o run-list (o `_rle_adjacente` já roda no bool). O tamanho base64 e a segmentação são passo NOVO barato (O(runs), 1 acumulador) — não reuso. E o ponto de seleção estilo `emitted_mode` é do `.8M`; o `.8H` single-col não tem um hoje (grounding wf_876541f7).
- **Nunca-pior via FLOOR**: o +6 do seg-adapt no homogêneo é só o header `D<n>:` do único segmento. Sob o FLOOR que o TCF já usa (emitir seg-adapt só se `< min(whole-dense, whole-rle)`, como a nature compete), o homogêneo cai pro whole-dense e o adaptativo vira estritamente nunca-pior — o eixo é ganhar no heterogêneo sem risco.
- **Passe único** vale pras duas composições (`reads/n==1.0`): fixo lê fatias disjuntas; adaptativo faz 1 scan da coluna. Latência preservada.
- **Trade composição×paralelismo**: fixo = lotes independentes (paralelizável) mas frágil; adaptativo = comprime robusto mas a fronteira depende do scan (menos paralelizável). A telemetria informa os dois — a ESCOLHA entre eles é o vetor.

**6 casos × 3 S · 0 falhas (RT + passe único).** Regenera: `python run.py`.