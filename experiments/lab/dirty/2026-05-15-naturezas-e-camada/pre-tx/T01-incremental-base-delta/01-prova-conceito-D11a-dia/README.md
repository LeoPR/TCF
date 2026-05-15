# 01 — Prova de conceito incremental dia (D11a)

**Estado**: aberto (primeira iteracao do T01)
**Macro pai**: [`../README.md`](../README.md) — T01 incremental
**Dataset**: [`D11a-datas-dia.csv`](../../../../../../../datasets/synthetic/D11a-datas-dia.csv)

## Pergunta cientifica

Em datas no formato `YYYY-MM-DD`, todas variando **apenas em dias**
(ano e mes podem variar como consequencia, mas o foco e' a
resolucao dia), conseguimos reduzir bytes representando como:
- **Linha 0**: data base (intocada).
- **Linhas 1+**: delta em **dias** (inteiro) em relacao a linha anterior.

E depois passar essa saida pelo TCF (OBAT + HCC)?

## Hipotese inicial

Bytes apos `pre-tx + TCF` < bytes apos `TCF puro` no mesmo input.

O motivo intuitivo: a linha base e' unica, mas os deltas
geralmente sao numeros de **1-2 digitos** com **muita repeticao**
(varios "1" consecutivos), o que e' caso ideal pra OBAT + HCC.

## Fluxo (pipeline completo com debug)

```
csv → pretx_dia.encode → TCF.encode (OBAT + HCC) → TCF.decode → postx_dia.decode → RT check
                              │
                              ├─ debug OBAT tokens (tree)
                              ├─ debug HCC trace (composicao)
                              └─ debug HCC rede (network)
```

Cada estagio sai pra arquivo em `outputs/` pra inspecao.

## Linguagem do pre-tx incremental (versao 0)

**Output do pre-tx** tem N linhas (mesmo N do input):
- Linha 0: **base date**, no formato `YYYY-MM-DD` (literal do input).
- Linhas 1+: **delta em dias** (inteiro como string), relativo a
  linha **imediatamente anterior**.

Razao de usar delta-relativo-anterior (em vez de relativo-a-base):
- Sequencias consecutivas (`+1, +1, +1, ...`) viram repeticoes
  exatas — OBAT + HCC adoram. Se fosse relativo-a-base teriamos
  `0, 1, 2, 3, ...` sem repeticao.

**Decoder**: reverso ponto-a-ponto.

**Limitacoes conhecidas v0**:
- Resolucao fixa em **dias**. Outros niveis (hora, segundo, ms, us, ns)
  ficam pra sub-experimentos posteriores.
- Delta de 0 dias permitido (mesma data repetida) mas ainda nao testado.
- Delta negativo permitido em principio (datas fora de ordem) mas
  D11a e' monotonicamente crescente, nao testa esse caso.
- Apenas formato `YYYY-MM-DD`. Outros formatos (DD/MM/YYYY, etc.)
  ficam pra sub-experimentos futuros (vide D10 datas-mundiais).

## Como rodar

```bash
python experiments/lab/dirty/2026-05-15-naturezas-e-camada/pre-tx/T01-incremental-base-delta/01-prova-conceito-D11a-dia/run.py
```

## Saidas (em `outputs/`, gitignored)

- `00-input.txt` — linhas do CSV (sem header)
- `01-pretx-output.txt` — saida do pre-tx (base + deltas)
- `02-tcf-encoded.tcf` — texto TCF
- `03-obat-tokens.txt` — arvore de tokens OBAT (debug)
- `04-hcc-trace.txt` — trace da composicao HCC (debug)
- `05-hcc-rede.txt` — rede de refs HCC (debug)
- `06-tcf-decoded.txt` — saida do TCF decode (deve igualar pre-tx)
- `07-postx-output.txt` — saida do pos-tx (deve igualar input)
- `08-rt-result.txt` — resultado do RT byte-canonical
- `bytes-comparison.md` — tabela de bytes por etapa

E `result.md` (top-level, commitado) — resumo dos resultados.

## Criterio de fechamento desta iteracao

- [ ] RT byte-canonical OK (`postx_out == linhas`)
- [ ] Bytes `pre-tx + TCF` < bytes `TCF puro` em D11a
- [ ] Debug visiveis: OBAT tree, HCC trace, HCC rede
- [ ] Lecoes registradas em [`../README.md`](../README.md) (atualizar com observacoes)
