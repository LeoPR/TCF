# Case 4 — ip-subnet-C

**Descricao**: D-IP-subnet (50 first) com pre-tx C (padded 12-digit). Strings fixas 12-char com cadence visivel no ultimo octeto. HCC seq-RLE explode.

## Resumo

- Valores: 50
- Input avg length: 12.0 chars
- Raw bytes (input ao sub-exp): 640
- TCF bytes: 44
- Ratio: 6.88%
- cadence_detected: True (rule=1-uniform-length-high-lcp-lcs)
- min_len: 3
- obat_used_hint: True
- seq_rle_runs: 2
- n_unicas: 50
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

**HCC seq-RLE EXPLODE com padding fixo**. Apos pre-tx C, cada IP vira
12-char com leading zeros (`057012140000`, `057012140001`, ...).

Observacoes esperadas:
- column_features: avg_len=12.0, cardinality=1.0, is_numeric=True
- cadence_detected=True (regra 2 ou 1)
- OBAT: usa `processar_with_hint` shape-preserve
- HCC: detector cria refs pro prefix `057012140`
- **seq_rle_runs ~11 runs** (1 por subrede de 100 IPs cada)
- Cada run: `*100+1|057012140000` (1 template + count + delta)

Cada subrede de 100 IPs vira 1 marker. 10 markers + headers = ~229B.

**Conclusao**: HCC seq-RLE eh perfeito pra este perfil. SlotBehavior
explicito desnecessario; padding visivel ja' aciona o mecanismo.

