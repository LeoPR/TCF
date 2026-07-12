# F4-mínimo — públicos nos hubs prontos (gerado por scripts/bench_evidencia_f4.py)

Amostras determinísticas (primeiros N; SAMPLE=5000); população total = janela
dedicada pós-release (decisão F3/ROI). RT validado em TODOS os casos antes de
qualquer número. Natures: só contagens nos registros (§2.3); nenhum blob salvo.
Sinal de compressão externa: zlib9 (stdlib) (brotli indisponível no venv) — qualitativo, nunca gate.

## Casos

| caso | linhas×cols | TCF B | CSV B | Δ vs CSV | modos | apply_rate | enc mediana ms (n) | nota |
|---|---|---:|---:|---:|---|---|---:|---|
| adult-5k | 5000×15 | 101967 | 539244 | 81.1% | @@!@@@@@@@tt@t@ | - | 570 (3) | census 15 cols, mix num/categ |
| tpch-lineitem-5k | 5000×16 | 299787 | 601788 | 50.2% | t@@@%%@@@t%%%@@t | - | 25550 (3) | 16 cols, free-text l_comment (regime do gate real-world) |
| tpch-customer-full | 1500×8 | 180006 | 241155 | 25.4% | tt!@%!@t | - | 908 (9) | 1500 linhas FULL, 8 cols |
| ibge-municipios-full | 5571×8 | 136914 | 434625 | 68.5% | t!@@tttt | - | 6496 (9) | 5571 linhas FULL (real, geografia BR) |
| br-pessoas-5k | 5000×6 | 284386 | 404576 | 29.7% | %@!@%t | - | 87877 (3) | sintético DV-válido (declared-bias), SEM natures |
| br-pessoas-5k-natures | 5000×6 | 256243 | 404576 | 36.7% | !@!@%t | [1.0] | 76729 (3) | idem + :cpf (delta natures em volume; §2.3 só contagens) |
| br-empresas-5k-natures | 5000×6 | 159289 | 356101 | 55.3% | !@!@%! | [1.0] | 12572 (3) | + :cnpj sintético DV-válido |
| receita-5k | 5000×8 | 100121 | 266387 | 62.4% | %tttt@@@ | - | 14617 (3) | REAL non-PII, SEM natures |
| receita-5k-natures | 5000×8 | 107460 | 266387 | 59.7% | !tttt@@@ | [1.0] | 2279 (3) | + :cnpj em dado REAL (fonte confirmada-empirica; apply_rate reportado, sem gate) |

## Sinal de compressão externa (mesmo conteúdo, qualitativo §2.8)

| caso | zlib9(csv) | zlib9(tcf) |
|---|---:|---:|
| adult-5k | 61724 | 42581 |
| tpch-lineitem-5k | 170726 | 135655 |
| tpch-customer-full | 91446 | 73894 |
| ibge-municipios-full | 66905 | 52781 |
| br-pessoas-5k | 129610 | 121351 |
| br-pessoas-5k-natures | 129610 | 107612 |
| br-empresas-5k-natures | 113554 | 82860 |
| receita-5k | 65126 | 51097 |
| receita-5k-natures | 65126 | 52071 |

Notas: tpch-sf01 (600k) e tabelas cheias (500k) = janela dedicada;
n=3 nos casos grandes -> latência INDICATIVA (claims de latência exigem n>=9).
