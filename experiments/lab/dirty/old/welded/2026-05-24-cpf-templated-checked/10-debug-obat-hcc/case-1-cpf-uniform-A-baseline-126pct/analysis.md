# Case 1 — cpf-uniform-A

**Descricao**: D-CPF-uniform (50 first) com M10 puro — sem pre-tx. Reproduz o 126% ratio.

## Resumo

- Valores: 50
- Input avg length: 14.0 chars
- Raw bytes (input ao sub-exp): 750
- TCF bytes: 942
- Ratio: 125.6%
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

**OBAT/HCC com material aleatorio**. CPFs uniformes sao essencialmente
strings de alta entropia separadas por marcadores fixos `.` `.` `-`.

Observacoes esperadas no `obat-log.txt`:
- OBAT acha LCP=0/LCS=0 entre a maioria das strings (sem prefix/sufix
  significativo)
- min_len=3 padrao; raras coincidencias casam mas net negativo
- Cobertura per string: quase 100% TokLit (literais)

Observacoes esperadas no `hcc-trace.txt`:
- Detector itera procurando sub-tuplas com freq >=2
- Candidatos rejeitados (net <= 0) dominam
- Poucas composicoes welded; output dominado por literais + marcadores

**Conclusao**: M10 e' anti-compressor pra esta natureza. Pre-tx
explicito (variante B sub-exp 05) eh a saida.

