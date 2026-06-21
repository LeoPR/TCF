# Sub-exp 10 — Debug OBAT/HCC (report consolidado)

Owner pediu visibilidade dos algos internos pra entender por que
M10 piora CPF (126%) e por que C subnet domina dramatically (1.71%).

## Cases analisados

| Case | Dataset | Variante | avg_len | TCF bytes | Ratio | cadence | seq_rle |
|---|---|---|---:|---:|---:|:---:|---:|
| 1 | CPF | A | 14.0 | 942 | 125.6% | × | 0 |
| 2 | CPF | B | 5.0 | 308 | 41.07% | × | 0 |
| 3 | IP | A | 11.8 | 37 | 5.78% | ✓ | 2 |
| 4 | IP | C | 12.0 | 44 | 6.88% | ✓ | 2 |
| 5 | IP | A | 12.4 | 1827 | 68.17% | ✓ | 2 |
| 6 | IP | C | 12.0 | 61 | 2.28% | ✓ | 3 |

## Arquivos por case

Cada `case-N-*/` contem dump completo: input, pretx, output.tcf,
column_features.json, cadence_info.json, obat-log.txt, hcc-trace.txt,
hcc-rede.txt, seq_rle_runs.json, summary.json, analysis.md.

## Cases listados

- `experiments\lab\dirty\2026-05-24-cpf-templated-checked\10-debug-obat-hcc\case-1-cpf-uniform-A-baseline-126pct/analysis.md`
- `experiments\lab\dirty\2026-05-24-cpf-templated-checked\10-debug-obat-hcc\case-2-cpf-clustered-B-base94-46pct/analysis.md`
- `experiments\lab\dirty\2026-05-24-cpf-templated-checked\10-debug-obat-hcc\case-3-ip-subnet-A-baseline-118pct/analysis.md`
- `experiments\lab\dirty\2026-05-24-cpf-templated-checked\10-debug-obat-hcc\case-4-ip-subnet-C-padded-1pct/analysis.md`
- `experiments\lab\dirty\2026-05-24-cpf-templated-checked\10-debug-obat-hcc\case-5-ip-subnet-A-200vals-cross-subnet/analysis.md`
- `experiments\lab\dirty\2026-05-24-cpf-templated-checked\10-debug-obat-hcc\case-6-ip-subnet-C-200vals-cross-subnet/analysis.md`

## Achados consolidados

### Cases 1-4 (sample 50)

**Por que M10 piora CPF (case 1 126%)**: alta entropia + marcadores
fixos. OBAT nao acha LCP/LCS significativos; HCC cria poucos refs;
marcadores `.` `.` `-` viram overhead estatico.

**Por que B funciona (case 2 46%)**: ganho vem do pre-tx (14->5 chars),
NAO do pipeline canonical. TCF apenas serializa output base-94 denso.

**Surpresa case 3 (M10 puro 5.78%!)**: com 50 IPs do mesmo subnet,
M10 comprime BRILLIANTLY. seq-RLE pega 2 runs cobrindo todos. Body
real eh 3 linhas: `\57.\12.\140.*\0`, `*9+1|1\1`, `*40+1|1\10`.
Apenas 37 bytes pra 50 IPs!

**Case 4 (padded 6.88%)** marginal pior que case 3 — padding adiciona
leading zeros e marker overhead em sample pequeno.

### Cases 5-6 (sample 200, cross-subnet)

**Case 5 explica o 118% do sub-exp 08!** Com 200 IPs:
- min_len pulou de 3 -> 6 (gating ADR-0010 ativa em n>=100)
- M10 puro: 1827B = 68.17% (vs 5.78% em case 3!)
- gating muda comportamento dramaticamente entre n<100 e n>=100

**Case 6 imune ao gating**: padded C mantem 2.28% em 200 vals
(similar 1.71% em 1000). Porque padding garante prefix >= 6 chars
uniformes -> OBAT acha refs mesmo com min_len=6.

### Lesson META — gating min_len escala mal em variable-length

ADR-0010 gating (n>=100 ativa min_len heur v3) foi calibrado pra
datasets reais Adult/TPC-H. Em IP subnet sem padding, min_len=6
destroi a habilidade do OBAT de captar prefixos curtos (`140.0` =
5 chars).

Implicacao pra src/tcf canonical: gating ADR-0010 nao eh universal —
tem cenarios onde min_len=3 (padrao) seria melhor. Hipotese pra
investigar: detectar 'variable-length cadence' antes de aplicar
gating, ou desativar gating quando cadence_detected=True.

**Esta sub-experimento e' bom exemplo de como debug expoe bugs
de calibracao do canonical pipeline.**

### Lesson global

HCC seq-RLE eh poderoso QUANDO:
1. Input tem padroes near-identical de length uniforme
2. min_len suficientemente baixo pra captar prefix comum

Padding viabiliza ambos: length uniforme + prefix longo. Por isso
C domina C subnet em 1.71% no full dataset 1000 vals.

