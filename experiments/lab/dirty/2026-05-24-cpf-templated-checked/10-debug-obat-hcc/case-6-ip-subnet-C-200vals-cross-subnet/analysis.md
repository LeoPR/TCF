# Case 6 — ip-subnet-C-cross

**Descricao**: D-IP-subnet (200 first = 2 subnets completas) com pre-tx C. Comparacao com case 5 mostra se padding ajuda no cruzamento de subnets.

## Resumo

- Valores: 200
- Input avg length: 12.0 chars
- Raw bytes (input ao sub-exp): 2680
- TCF bytes: 61
- Ratio: 2.28%
- cadence_detected: True (rule=1-uniform-length-high-lcp-lcs)
- min_len: 6
- obat_used_hint: True
- seq_rle_runs: 3
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

**Padded com cross-subnet**. Esperado bom comportamento mesmo no
cruzamento porque padding mantem length uniforme (sempre 12 chars).

Observacoes esperadas:
- 2 subnets, 100 IPs cada, padded
- HCC detecta runs em cada subnet (last octet 0-99)
- Transicao entre subnets: novo prefix mas mesma length
- Esperado: ratio similar ao case 4 (~7-10% em 200 vals)
- Se mantem proporcionalidade: confirma que C escala bem

