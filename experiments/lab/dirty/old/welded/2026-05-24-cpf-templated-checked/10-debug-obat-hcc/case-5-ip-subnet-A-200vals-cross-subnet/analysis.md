# Case 5 — ip-subnet-A-cross

**Descricao**: D-IP-subnet (200 first = 2 subnets completas) com M10 puro. Investiga discrepancia: 50 vals = 5.78%, mas full 1000 vals = 118%. Hipotese: transicao entre subnets quebra near-identical.

## Resumo

- Valores: 200
- Input avg length: 12.4 chars
- Raw bytes (input ao sub-exp): 2680
- TCF bytes: 1827
- Ratio: 68.17%
- cadence_detected: True (rule=1-uniform-length-high-lcp-lcs)
- min_len: 6
- obat_used_hint: True
- seq_rle_runs: 2
- n_unicas: 200
- RT input -> decoded: True

## Arquivos neste case

- `input.txt` — valores raw (input ao sub-exp)
- `pretx.txt` — apos pre-tx (se aplicavel)
- `output.tcf` — TCF final do encode
- `column_features.json` — pre-pass features (analyze_column)
- `cadence_info.json` — decisao detect_cadence
- `obat-log.txt` — log per-string do OBAT (LCP/LCS, cobertura, tokens)
- `hcc-trace.txt` — detector HCC iteracoes (candidatos / net / decisoes)
- `hcc-rede.txt` — rede atoms + composicoes + uso por ref
- `seq_rle_runs.json` — runs near-identical detectados
- `summary.json` — metricas resumidas

## Interpretacao

**Cross-subnet behavior** — investigando a discrepancia 5.78% (50 vals)
vs 118% (1000 vals) reportada em sub-exp 08.

Hipotese: cada subnet tem prefix diferente (random 3 octetos). Quando
HCC seq-RLE detecta runs WITHIN um subnet, a transicao subnet1->subnet2
quebra near-identical (length pode mudar + prefix muda).

Observacoes esperadas:
- 200 IPs = 2 subnets × 100 IPs
- Esperado: runs dentro de cada subnet (similar a case 3) + literal na
  transicao
- Se M10 manage to capture 2 + 2 runs (4 total), ratio fica baixo
- Se M10 confunde por mudanca de prefix, ratio sobe

Comparar tcf_bytes com 2x bytes do case 3 (50 vals = 37B).
Esperado: ~150-300B se funciona; >500B se confunde.

