# Conclusão — tabelão (A) vs duas tabelas (B) [probatório]

**Todos os números vêm de `artifacts/` (gerados por `python run.py`, reproduzíveis).** A prosa aponta;
o artefato mede. Ticket: [T-STUDY-HIERARCHICAL-TCF](../../../../tickets/T-STUDY-HIERARCHICAL-TCF.md).

## O que os 5 estágios mostram

- **01 entrada** → `01-entrada-S3.json` (documento aninhado `{equipment:{...}, day:[16]}`).
- **02 tradução** → o tabelão (`02-traducao-A-tabelao.csv`, 14 col × 16) e as duas tabelas
  (`02-traducao-B-T0` 1 lin, `02-traducao-B-T1` + fk) + os mapas de hierarquia (schema/manifest).
- **03 TCF adaptado** → `03-tcf-adaptado-A.tcf.txt` mostra o **cross ×16 colapsando em 9 linhas RLE**
  (`*16|EQP_\001`, `*16|FAC_A`, …). Trace por coluna em `03-trace-A-obat-hcc.txt`.
- **04 decode** → `04-decode-roundtrip.txt`: **A e B decodam e reconstroem o JSON de entrada** (OK/OK) —
  o JSON reconstruído está impresso no artefato, idêntico à entrada. **Funciona.**
- **05 bytes** → `05-bytes-medida.txt`:

| brotli q11 | M=1 (16 lin) | M=3 (48 lin) |
|---|---|---|
| A (tabelão, sem schema) | 283 | 332 |
| B-dados (T0+T1, sem manifest) | 301 | 327 |
| A + schema | 314 | 370 |
| **B + manifest** | **297** | **354** |

## Verdito nas 4 afirmações do owner (medido)

1. **cross → RLE → uma linha** — CONFIRMADO (`03-tcf-adaptado-A`: 9 linhas `*16|`).
2. **referência implica a mesma repetição** — CONFIRMADO. RLE e fk são **duais** (mesma multiplicidade ×N).
3. **o schema economiza o RLE — se for a necessidade [de reconstruir]** — CORRETO SOB A CONDIÇÃO: no
   regime de **reconstrução**, B < A+schema (297<314; 354<370). Não porque comprima melhor (empate), mas
   porque a **partição pai/filho é grátis em B** (a coluna mora em T0 ou T1) e **custa em A**.
4. **sem schema o RLE ocorre, mas não reconstrói o JSON** — CONFIRMADO. `03-A` faz RT da tabela; o schema
   carrega o mapa de desnormalização. Ambiguidade concreta: `isOutOfRange`/`minValue`/`maxValue` 15/16
   constantes → dedução ingênua os classificaria como contexto.

## Leitura

- **Reconstrução (precisa do JSON) → B vence nos dois M** — robusto, reproduzível.
- **Plano (só a tabela) → empate no ruído** (<1KB, overhead-dominado; direção flipa com M/moldura).
- **Princípio**: a multiplicidade ×N é conservada (~log N). O schema **não compra compressão; compra
  reconstrução**. Prior art: **factorized DBs** (Olteanu & Zavodny), **Dremel/Parquet** rep/def levels
  (Melnik 2010), **Heath** (integridade sse chave).

## Caveats (regime microbyte)

<1KB, gaps de 5–20B dentro do ruído do brotli. Robustos: os estruturais (1,2,4 + "B ganha reconstrução").
**Não passou pelo gate real-world.** Feasibility, não medição primária — progressão pendente (README §Será).
