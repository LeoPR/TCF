# 04 — Staged pipeline (D11c, 3 estagios explicitos)

**Estado**: aberto (quarta iteracao do T01)
**Macro pai**: [`../README.md`](../README.md)
**Dataset**: [`D11c-datas-mensal.csv`](../../../../../../../datasets/synthetic/D11c-datas-mensal.csv)

## Pergunta cientifica

Quebrar a "compressao delta" em **3 estagios explicitos** preserva
o mesmo resultado final do sub-exp 03 (encoder v1 monolitico, 22
bytes em D11c) MAS expoe os estados intermediarios pra inspecao?

A separacao em estagios serve a dois propositos:
1. **Verificar mid-pipeline** se cada transformacao e' otimizavel.
2. **Preparar terreno** pra futura "compressao do algoritmo" — quando
   um dia quisermos que o sistema identifique + normalize + otimize
   em **tempo de leitura online**, sabemos exatamente quais
   operacoes condensar.

Lema: **"burros e trabalhadores agora, pequenos e rapidos depois"**.

## Os 3 estagios

```
linhas brutas
    │
    ▼ stage A: identify
metadata = { type, format, granularity }   <- nao transforma dados
    │
    ▼ stage B: normalize_to_unit
[base, delta_1_dias, delta_2_dias, ...]    <- tudo na unidade base, naive
    │
    ▼ stage C: optimize_scales
[base, 1M, 1M, ...]                        <- aplica Y/M onde encaixa exato
    │
    ▼ TCF.encode (OBAT + HCC)
bytes
```

Decoder inverte na ordem reversa: TCF.decode -> C reverse -> B
reverse -> linhas. Metadata e' re-identificado da primeira linha
(que sempre carrega a base intocada).

## Estagio A — Identify

Inspeciona **somente a primeira linha** (nesta iteracao).

Regex: `^\d{4}-\d{2}-\d{2}$` + valida via `date.fromisoformat`.

Saida:
```json
{
  "n_samples": 13,
  "type": "date",
  "format": "YYYY-MM-DD",
  "granularity": "day"
}
```

**Nao transforma dados.** Apenas descreve.

Iteracoes futuras: inspecionar mais linhas (sample), detectar
HH:MM, numericos, templates (CPF/UUID — entrara em T02).

## Estagio B — Normalize to unit

Converte tudo a **unica unidade base** (no caso, dia).

Saida:
- `linhas[0]` (base intocada)
- `linhas[i] (i>=1)`: delta em **dias** entre linhas[i] e linhas[i-1]

**Nao otimiza escala.** Saida "naive" mas correta.

Esta saida e' tambem o output do **encoder v0** dos sub-exps
01/02. Stage B e' o "good baseline".

## Estagio C — Optimize scales

Recebe saida do B + metadata. Reconstroi datas a partir de base +
deltas-em-dias, e pra cada delta tenta:

1. **Ano exato**: data atual = data anterior + N anos (mesmo mes e dia)?
   Sim → emite `NY`.
2. **Mes exato**: data atual = data anterior + N meses (mesmo dia)?
   Sim → emite `NM`.
3. Caso contrario → mantem em dias.

**Otimiza escala.** Saida e' equivalente ao encoder v1 do sub-exp 03.

## Comparacao com sub-exps anteriores

| Sub-exp | Estagios | Resultado |
|---|---|---|
| 01 (D11a) | A + B (implicito monolitico) | 42 bytes |
| 02 (D11b borda) | A + B (implicito monolitico) | 59 bytes |
| 03 (D11c) | A + B + C (monolitico em v1) | 22 bytes |
| **04 (D11c) este** | **A + B + C SEPARADOS** | **22 bytes esperado** (mesma compressao) |

A meta deste sub-exp **nao e' melhorar bytes** — e' **decompor o
processo** mantendo o resultado. O ganho e' metodologico.

## Como rodar

```bash
python experiments/lab/dirty/2026-05-15-naturezas-e-camada/pre-tx/T01-incremental-base-delta/04-staged-pipeline-D11c/run.py
```

## Saidas

`outputs/` (gitignored):
- `00-input.txt` — linhas brutas
- `stage-A-metadata.json` — saida do identify
- `stage-B-normalized.txt` — saida do normalize (deltas em dias)
- `stage-C-optimized.txt` — saida do optimize (com escalas)
- `tcf-B.tcf` — TCF de stage B (= encoder v0)
- `tcf-C.tcf` — TCF de stage C (= encoder v1, esperado 22 bytes)
- `tcf-puro.tcf` — TCF de raw (sem pre-tx)
- `debug-obat-C.txt`, `debug-hcc-trace-C.txt`, `debug-hcc-rede-C.txt`
- `decoded-B.txt`, `decoded-C.txt` — decoders aplicados
- `rt-result.txt` — RT verificacao em 4 pontos
- `bytes-comparison.md`

`result.md` (commitavel) — resumo.

## Criterio de fechamento

- [ ] RT byte-canonical preservado (stage C output → decode → linhas originais)
- [ ] Bytes do stage C == bytes do encoder v1 monolitico (sub-exp 03 = 22 bytes)
- [ ] Stage A metadata inspecionavel (JSON limpo)
- [ ] Stage B output inspecionavel (deltas em dias visiveis)
- [ ] Stage C output inspecionavel (escalas aplicadas visiveis)
- [ ] Documentar onde otimizacao alternativa poderia entrar (mid-pipeline)
