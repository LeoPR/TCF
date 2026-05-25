# Case 2 — cpf-clustered-B

**Descricao**: D-CPF-clustered (50 first) com pre-tx B (strip+check+base94). 5-char base-94 strings densas; OBAT/HCC com pouca redundancia visivel.

## Resumo

- Valores: 50
- Input avg length: 5.0 chars
- Raw bytes (input ao sub-exp): 750
- TCF bytes: 308
- Ratio: 41.07%
- cadence_detected: False (rule=None)
- min_len: 3
- obat_used_hint: False
- seq_rle_runs: 0
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

**OBAT/HCC com strings curtas densas (5-char base-94)**. Apos pre-tx
B, cada CPF vira 5 chars random em alfabeto BASE94.

Observacoes esperadas:
- OBAT raramente acha LCP/LCS >= 3 entre strings tao curtas
- HCC trabalha em pieces curtos; refs criados sao quase nulos
- Ganho da compressao vem do **encode mais denso** (5 vs 14 chars),
  nao do OBAT/HCC.

Cardinalidade altissima (1000 unique em 50 sample = 1.0). M10
cadence regra 2 (numeric+high-card) NAO dispara aqui porque o
output base-94 tem letras (`is_numeric=False`).

**Conclusao**: compressao real vem do pre-tx, nao do pipeline canonical.
TCF apenas serializa.

