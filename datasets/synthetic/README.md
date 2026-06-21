# datasets/synthetic — Controle sintético (D1-D15)

> **Status (2026-05-15)**: datasets de controle do algoritmo TCF-CORE.
> D1-D9 elevados do dirty lab; D10-D15 criados pra cobrir tipos
> notaveis de ERP/CRM (datas, datetimes, CPF, UUID, base64).

## Proposito

Conjunto de **datasets sinteticos pequenos** projetados para
verificar comportamento do algoritmo TCF-CORE + Compactacao
composicional em cenarios variados. Complementa os datasets reais
em `datasets/canonical/` (Adult Census, TPC-H).

Cada arquivo e' um cenario distinto. Single-column CSV com header
`val` e ~12-20 linhas focadas em variedade de forma/tipo.

## Cenarios — D1-D9 (controle TCF-CORE/HCC)

| Arquivo | Cenario | Linhas | Raw bytes | Caracteristica |
|---|---|---:|---:|---|
| D1-emails-simples.csv | Emails 3 dominios | 12 | 191 | Padrao classico (gmail/hotmail/yahoo) |
| D2-emails-quote-id.csv | Emails + apostrofes | 12 | 248 | Nomes com `'` (d'angelo, o'brien) |
| D3-stress-substring.csv | URLs `api/users/...` | 12 | 348 | Stress para detector subseq |
| D4-caos-mix.csv | Mix `[X]*'YYY'@4Z` | 12 | 157 | Alto caos, baixa redundancia |
| D5-padroes-multiplos.csv | email + UUID coexistentes | 12 | 419 | Multi-padrao paralelo |
| D6-poucos-em-ruido.csv | Log com timestamps unicos | 12 | 528 | Estresse para pre-tx delta |
| D7-aninhamento.csv | `[start][a][middle][a][end]` | 12 | 335 | Padrao em multiplas positions |
| D8-cabeca-cauda.csv | `prefix/X/suffix` (X varia) | 12 | 384 | Cenario ideal (prefix/suffix estaveis) |
| D9-frequencia-alta.csv | `@@@KEY=valueX@@@` (X varia) | 20 | 363 | Wrapper com slot variavel |

## Cenarios — D10-D15 (tipos ERP/CRM, controle pra EXP-008+)

Focados em **variedade de formato** (poucas linhas, varios layouts
do mesmo tipo semantico). Pensados pra estresse de type encoders /
pre-filtros (Estrategia 1.A do roadmap).

| Arquivo | Cenario | Linhas | Raw bytes | Caracteristica |
|---|---|---:|---:|---|
| D10-datas-mundiais.csv | Datas mundiais (ISO/US/EU/BR) | 15 | 177 | Mesma data em 15 layouts (`2026-05-15`, `05/15/2026`, `15 de maio de 2026`, ...) |
| D11-datetime-precisao.csv | Datetime com precisao variavel | 13 | 311 | Segundos → nanosegundos; ISO 8601 + variantes basicas |
| D12-datetime-timezone.csv | Timezones variados | 14 | 385 | `Z`, `+00:00`, `-03:00`, `America/Sao_Paulo`, `UTC`, `BRT` |
| D13-cpf-variados.csv | CPFs com/sem mascara, defeitos | 15 | 211 | `123.456.789-09`, sem pontuacao, misto, digito errado |
| D14-uuid-variados.csv | UUIDs em varios layouts | 12 | 455 | Canonico, sem hifen, uppercase, braces, `urn:uuid:`, v7 |
| D15-base64-variados.csv | Base64 com/sem padding, URL-safe | 14 | 323 | `=`/`==`/sem padding, alfabeto URL-safe (`-_`) |

## Cenarios — Dxxa/b/c (sub-datasets controlados, foco por nivel de precisao)

Sub-datasets criados conforme necessidade dos macros do dirty lab.
Cada um e' **mais estreito** que seu pai (D10-D15), focado em **um
aspecto especifico** da natureza pra controle fino.

| Arquivo | Cenario | Linhas | Raw bytes | Foco | Macro origem |
|---|---|---:|---:|---|---|
| D11a-datas-dia.csv | Datas YYYY-MM-DD, variando so' em dias | 12 | 136 | Resolucao dia (delta = inteiro de dias) | [T01-incremental](../../experiments/lab/dirty/old/welded/2026-05-15-naturezas-e-camada/pre-tx/T01-incremental-base-delta/) |
| D11b-datas-borda.csv | Datas YYYY-MM-DD, bordas mes/ano + leap year | 14 | 158 | Validar RT calendar (Feb 29, year boundary) | [T01-incremental sub 02](../../experiments/lab/dirty/old/welded/2026-05-15-naturezas-e-camada/pre-tx/T01-incremental-base-delta/02-bordas-D11b/) |
| D11c-datas-mensal.csv | Datas YYYY-MM-DD, fatura mensal dia 5 por 13 meses | 13 | 156 | Cadencia mensal realistic — testa escala `+1M` | [T01-incremental sub 03](../../experiments/lab/dirty/old/welded/2026-05-15-naturezas-e-camada/pre-tx/T01-incremental-base-delta/03-cadencia-mensal-D11c/) |
| D11d-datetime-min.csv | Datetime YYYY-MM-DD HH:MM:SS, heartbeat top-of-minute | 13 | 264 | Granularity=second, cadencia minuto — testa escala `+1m` | [T01-incremental sub 06](../../experiments/lab/dirty/old/welded/2026-05-15-naturezas-e-camada/pre-tx/T01-incremental-base-delta/06-staged-granularity-second/) |
| D11e-datetime-mensal.csv | Datetime YYYY-MM-DD HH:MM:SS, fatura mensal dia 5 às 9h | 13 | 264 | Granularity=second, cadencia mensal — demo escala `+1M` em datetime (ganho 57% C vs B) | [T01-incremental sub 07](../../experiments/lab/dirty/old/welded/2026-05-15-naturezas-e-camada/pre-tx/T01-incremental-base-delta/07-cadencia-mensal-datetime-D11e/) |
| D16a-ids-3digits.csv | IDs sequenciais "100".."112" | 13 | 65 | Numeric ID, cardinality 3 com transicao 9→10 | [obat-delta-aware sub 05](../../experiments/lab/dirty/2026-05-17-OBAT-delta-aware/05-numeric-ids-h-da-06/) |
| D16b-ids-4digits.csv | IDs sequenciais "1000".."1012" | 13 | 62 | Numeric ID, cardinality 4 uniforme | [obat-delta-aware sub 05](../../experiments/lab/dirty/2026-05-17-OBAT-delta-aware/05-numeric-ids-h-da-06/) |
| D16c-ids-prefixados.csv | IDs "USR-100".."USR-112" | 13 | 70 | Numeric ID com prefix string + transicao | [obat-delta-aware sub 05](../../experiments/lab/dirty/2026-05-17-OBAT-delta-aware/05-numeric-ids-h-da-06/) |
| D17a-multi-column-mixed.csv | tabela 4 colunas (timestamp, id, email, categoria) | 13 | 601 | Multi-column basico — testa pipeline EXP-011 com tipos mistos | [EXP-011 multi-column](../../experiments/lab/clean/EXP-011-multi-column-basic/) |

(Outros Dxxc/d... criados quando macros pedirem niveis hora/segundo/ms/us/ns ou outros focos.)

## Compressao validada (M9 baseline)

D1-D9 sob HCC composicional: **1615 bytes em 2981 raw = 54.2% ratio**
(re-verificado em EXP-007). Varia 26% (D8 melhor) a 72% (D4 caos).
Ver [`../../experiments/lab/clean/EXP-007-prototipo-tcf-core/`](../../experiments/lab/clean/EXP-007-prototipo-tcf-core/).

D10-D15 **ainda nao tem baseline** — TCF-CORE atual e' single-column
e nao tem type encoders. Esses datasets entram em EXP-008+ (type
encoders / pre-filtros, Estrategia 1.A).

## Uso

Macros futuros (M10+) e EXP-NNN no `experiments/lab/clean/`
referenciam diretamente estes arquivos.

```python
DATASETS_DIR = Path(__file__).resolve().parents[N] / "datasets" / "synthetic"
```

## Direcoes futuras

- **EXP-008** (Estrategia 1.A): type encoders pra CPF/UUID/data
  ISO/datetime/base64 — input direto D10-D15.
- **EXP-009** (Estrategia 1.B): multi-coluna (instancias TCF por
  coluna) — exige datasets multi-coluna (fora do escopo D*).
- Variantes incrementais (D1a, D1b, ...) pra stress de escala —
  nao urgente.

## Conexoes

- D1-D9: originadas em `experiments/lab/dirty/old/2026-05-17-M9-stress-adversarial/data/`,
  validadas por M9-M14 + EXP-007.
- D10-D15: criados pra EXP-008+ (controle de tipos ERP/CRM).
- Para datasets canonicos reais ver `../canonical/`.
