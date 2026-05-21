# Sub-exp 01 v2 — caracterizacao escapes (com H-ED-original)

## Tabela completa

| dataset | n_cols | body | digits_esc | atoms | H-ED-01 | H-ED-02 | **H-ED-original** | orig % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| D1-emails-simples | 1 | 98 | 0 | 12 | 0 | 0 | **0** | 0.00% |
| D2-emails-quote-id | 1 | 139 | 6 | 12 | 1 | 1 | **4** | 2.88% |
| D3-stress-substring | 1 | 140 | 5 | 12 | 1 | 1 | **4** | 2.86% |
| D4-caos-mix | 1 | 93 | 5 | 12 | 1 | 0 | **0** | 0.00% |
| D5-padroes-multiplos | 1 | 238 | 22 | 12 | 5 | 2 | **10** | 4.20% |
| D6-poucos-em-ruido | 1 | 230 | 31 | 12 | 1 | 4 | **16** | 6.96% |
| D7-aninhamento | 1 | 183 | 0 | 12 | 0 | 0 | **0** | 0.00% |
| D8-cabeca-cauda | 1 | 66 | 0 | 12 | 0 | 0 | **0** | 0.00% |
| D9-frequencia-alta | 1 | 134 | 8 | 20 | 1 | 0 | **0** | 0.00% |
| adult-1000 | 15 | 39,157 | 790 | 1268 | 8 | 0 | **692** | 1.77% |
| adult-5000 | 15 | 192,909 | 3174 | 5022 | 8 | 0 | **3039** | 1.58% |
| tpch.region-5k | 3 | 380 | 1 | 15 | 1 | 0 | **0** | 0.00% |
| tpch.customer-5k | 8 | 210,296 | 13160 | 9029 | 20 | 1034 | **1523** | 0.72% |
| tpch.lineitem-5k | 16 | 497,978 | 12642 | 19407 | 30 | 79 | **5391** | 1.08% |

## Agregado

- Total body: 942,041B
- Total digit escapes: 29844
- H-ED-01 savable: 77B (0.01%)
- H-ED-02 savable: 1121B (0.12%)
- **H-ED-original savable**: 10679B (1.13%) ← lower bound

## Interpretacao

**H-ED-original** captura digit-runs cujo valor > n_atoms_total da
coluna. Esse e' LOWER BOUND — implementacao real (count crescendo
linha-a-linha) detectaria MAIS (count_at_emit < n_atoms_total na
maioria das emissoes).

### Comparacao com criterio de aceite

| Variante | Real-world weighted | Aceite (>=5%)? |
|---|---:|---|
| H-ED-01 (linha 1) | 0.01% | NAO |
| H-ED-02 (apos `*`) | 0.12% | NAO |
| **H-ED-original lower bound** | **1.13%** | NAO |
| Upper bound estimado (smart encoder full) | ~2-3% (a-medir) | provavelmente NAO |

### Recomendacao

**Pacote 2 nao atinge criterio de aceite em real-world**. Custos pra
implementar (smart encoder+decoder pareados, versionamento de formato
opt-in OU compat-break, ADR + re-validacao multi-camada, manter dois
decoders) sao **altos comparados ao ganho marginal**.

Comparacao com Pacote 4 ADR-0009:
- ADR-0009: 2.70x speedup, ZERO byte loss, ZERO compat break
- Pacote 2: 1-3% bytes, ALTO risco compat break, complexo

**Decisao sugerida**: fechar Pacote 2 como **CLOSED-INSUFFICIENT-GAIN**.
Sub-exp 11 T01 antigo (15.7% em D11a-h) nao generaliza pra real-world
porque dataset era construido com perfil especial (digits dominantes).

### Caminho alternativo

Se quiser numero EXATO (upper bound), implementar smart encoder simulado
em sub-exp 02 — so' medir, sem weldar nada. Se upper bound >= 5%,
reabrir; senao, fechar definitivo.

