# Case 3 — ip-subnet-A

**Descricao**: D-IP-subnet (50 first) com M10 puro. M10 detecta cadence mas variable-length octets quebram near-identical (so' 2 runs).

## Resumo

- Valores: 50
- Input avg length: 11.8 chars
- Raw bytes (input ao sub-exp): 640
- TCF bytes: 37
- Ratio: 5.78%
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

**M10 puro em subnet IPs**. Strings variable-length (`57.12.140.0` =
11 chars vs `57.12.140.99` = 12 chars).

Observacoes esperadas:
- cadence_detected=True via regra 1 (LCP+LCS) PORQUE primeiras 5
  strings devem ter lengths uniformes (`57.12.140.0..4` todos 11 chars)
- HCC seq-RLE detecta ~2 runs entre IPs com mesmo length, depois
  para quando length muda (10..99 viram 12 chars)
- OBAT cria refs significativos pro prefix `57.12.140.`

**Conclusao**: HCC seq-RLE PARCIALMENTE funciona, mas variabilidade
de length impede captura total. Padding (case 4) resolve.

