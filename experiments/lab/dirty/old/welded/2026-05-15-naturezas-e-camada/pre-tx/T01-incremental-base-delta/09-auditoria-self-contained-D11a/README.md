# 09 — Auditoria self-containment de D11a + revisao das tecnicas

**Estado**: aberto (nona iteracao do T01)
**Macro pai**: [`../README.md`](../README.md)
**Input**: copia byte-exata de `tcf-C.tcf` de sub-exp 08 → `input/D11a.tcf` (42 bytes)

## Princípio sob teste

> "Tudo que e' armazenado ou que precise recuperar tem custo. Pra
> validacao perfeita do algoritmo genérico, o decode SEMPRE precisa
> acompanhar — o arquivo `.tcf` deve carregar tudo que e' necessario
> pra desempacotar (dados, refs, e qualquer cabecalho que seja
> preciso)."

## Pergunta cientifica

Dado apenas `D11a.tcf` (42 bytes) **e nada mais alem do algoritmo
compartilhado** (TCF.decode + pre-tx logic), consegue-se
reconstruir `D11a-datas-dia.csv` byte-canonical?

Equivalente a `gzip`: `gunzip` nao precisa de hint externo —
qualquer `.gz` decodifica sozinho com o algoritmo padrao.

## Hipotese

D11a.tcf e' **self-contained**: a primeira linha (`2026-05-15`)
permite auto-deducao da natureza (`type=date, granularity=day`),
e as linhas subsequentes (`1`, `1`, `3`, `*2|^2`, ...) sao
deltas que reconstroem a serie original.

## O que o decoder NAO recebe

- D11a-datas-dia.csv original (so' usado pra comparar resultado)
- Metadata externo (sem JSON sidecar)
- Hint de natureza/granularidade
- Count de linhas

## Audit trail — todas as tecnicas aplicadas a D11a no T01

Em ordem de aplicacao no encode (inverso no decode):

### Camada 1 — Pre-tx por natureza incremental

**Stage A — Identify** (sub-exp 04+):
- Inspeciona primeira linha
- Detecta `YYYY-MM-DD` → meta `{type=date, format=YYYY-MM-DD, granularity=day}`

**Stage B — Normalize to unit** (sub-exp 04+):
- Converte D11a (12 linhas) em `[base, delta1, delta2, ...]` em dias
- Para D11a: `[2026-05-15, 1, 1, 1, 1, 3, 1, 1, 5, 1, 2, 14]`
- Total: 12 entries (1 base + 11 deltas)

**Stage C — Optimize scales** (sub-exp 04+):
- Tenta escalas maiores onde encaixa exato
- Para D11a: **nenhuma escala se aplica** (deltas em dias variam, nao alinham com M/Y)
- Output identico ao Stage B

### Camada 2 — TCF encode (OBAT + HCC, src/tcf canonical)

**OBAT (alg16)** — tokenizacao bidirectional via LCP/LCS:
- Strings unicas em D11a stage C output: 6
  - "2026-05-15" (base — unica)
  - "1" (delta — aparece 7 vezes)
  - "3", "5", "2", "14" (deltas — cada um aparece 1 vez)
- Cada string e' tokenizada como literal (nenhuma comparte prefixo/suffixo util com outra)

**HCC (M8.A)** — composicional + RLE adjacente:
- Detector unificado processa pieces
- RLE adjacente agrupa linhas identicas consecutivas:
  - 4 "1" consecutivos → `*4|...`
  - 2 "1" consecutivos → `*2|...`
- Emit usa marcadores:
  - `\<digits>` escapa literal numerico (pra diferenciar de IDs)
  - `^N` referencia N-esimo node declarado
  - `*N|<linha>` repete a linha N vezes

### Output final — D11a.tcf (42 bytes)

```
\2026-\05-\15
*4|\1
\3
*2|^2
\5
^2
\2
\14
```

8 linhas. Cada uma codifica:

| Linha | Conteudo | Significa |
|---|---|---|
| 1 | `\2026-\05-\15` | base date (literal escapado) |
| 2 | `*4|\1` | 4 copias da linha "1" (declara node 2) |
| 3 | `\3` | literal "3" (node 3) |
| 4 | `*2|^2` | 2 copias de ref ao node 2 (i.e., "1" 2x) |
| 5 | `\5` | literal "5" (node 4) |
| 6 | `^2` | ref ao node 2 (i.e., "1") |
| 7 | `\2` | literal "2" (node 5) |
| 8 | `\14` | literal "14" (node 6) |

## Procedimento do experimento

1. Decoder lê ONLY `input/D11a.tcf` (42 bytes).
2. Aplica `TCF.decode` (algoritmo padrao) → reconstroi pre-tx output.
3. Aplica `identify_from_first_line` na primeira linha → meta `{date, day}`.
4. Aplica Stage C+B inversos baseado em meta → linhas originais.
5. Compara com `D11a-datas-dia.csv` original (apenas pra VERIFICAR).

## Como rodar

```bash
python experiments/lab/dirty/2026-05-15-naturezas-e-camada/pre-tx/T01-incremental-base-delta/09-auditoria-self-contained-D11a/run.py
```

Ou direto via:
```bash
python experiments/lab/dirty/2026-05-15-naturezas-e-camada/pre-tx/T01-incremental-base-delta/09-auditoria-self-contained-D11a/decode_standalone.py input/D11a.tcf
```

## Criterio de fechamento

- [ ] Decoder reconstroi 12 linhas a partir de input/D11a.tcf
- [ ] Linhas reconstruidas = D11a-datas-dia.csv byte-canonical
- [ ] Auto-deducao da natureza funciona (sem hint externo)
- [ ] Audit trail das tecnicas registrado

## Observacao operacional

Se em iteracoes futuras for necessario **cabecalho explicito**
(quando first-line nao for suficiente pra disambiguar tudo), ele
tera que estar **DENTRO do .tcf** (ex: linha de metadata antes
do base). Hoje a auto-deducao basta porque:

- Date format se auto-detecta (regex + fromisoformat)
- Stage C/B sao deterministicos dada a granularidade detectada em A
- Outros tipos (templated, enumerated) podem precisar de header
  no futuro — fora do escopo de T01

## Conexoes

- [`decode_standalone.py`](decode_standalone.py) — decoder isolado (one-file)
- [`../08-granularidades-finas/outputs/D11a-datas-dia/tcf-C.tcf`](../08-granularidades-finas/outputs/D11a-datas-dia/tcf-C.tcf) — fonte do input
- [docs/algorithms/](../../../../../../docs/algorithms/) — TCF/OBAT/HCC reference
