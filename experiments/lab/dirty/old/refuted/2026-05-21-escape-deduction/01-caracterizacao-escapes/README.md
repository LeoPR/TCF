# Sub-exp 01 — caracterizacao escapes em real-world

**Objetivo**: medir overhead de escapes (`\digits`, `\*`, `\\`, `\~`)
em encode HCC em datasets variados, e quantos sao **deduziveis** por
cada heuristica H-ED-01/02/03.

## Metodo

Pra cada dataset:
1. Encode normal (canonical), salvar `.tcf`
2. Parsear bytes do `.tcf`, contar escapes por categoria:
   - `\digits` (digit-runs escapados)
   - `\*` `\\` `\~` (operator escapes)
3. Classificar cada escape:
   - **H-ED-01 candidate**: linha 1 do body (count=0, todos digits literais)
   - **H-ED-02 candidate**: digit-run apos `*` separator (lit context)
   - **H-ED-03 candidate**: operator escape em posicao deduzivel
   - **non-removable**: contexto realmente ambiguo

Pra H-ED-01 ser candidata, basta posicao = primeira linha apos meta.
Pra H-ED-02, precisa rastrear estado parser linha-a-linha.
Pra H-ED-03, mais complexo — analise per-caso.

## Datasets

- D1-D9 (controle algoritmo) — single-col
- Adult Census 1000, 5000 rows — multi-col real-world
- TPC-H 3 tabelas (region, customer, lineitem) 5000 rows

## Output

Tabela por dataset:
- bytes total
- N escapes total
- N escapes deduziveis-H-ED-01 (% bytes saveable)
- N escapes deduziveis-H-ED-02 (% bytes saveable)
- N escapes nao-removiveis

## Aceite

- Tabela comparativa com 3 grupos de dataset
- Decisao informada de quais H-ED priorizar nos sub-exps 02-04
- Estimativa de byte saving total esperado pra real-world
