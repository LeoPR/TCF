# EXP-017 — alvos mensais de data: relatório

**Gerado por `run.py`.** 26 casos · **0 falhas**.
`src/tcf` não é tocado; os alvos são protótipos de [`specs.py`](specs.py).

## A resposta curta

**Os alvos mensais NÃO fecham em dado real** — e o motivo não é o mecanismo, é o corpus:
**nenhuma das 14 colunas reais tem cadência mensal**. Todas são diárias ou
transacionais (TPC-H pedidos/embarques, cadastros BR, futebol desde 1872). Ganho mediano
nos reais: **0.0%**. Nos sintéticos mensais, onde o regime existe: **95.0%**.

Mas o lab achou algo maior no caminho — ver §2.

## 1. Placar

| onde vence | reais |
|---|---:|
| **ordinal-dia** (o spec de hoje) | 10 |
| alvo **mensal** | 2 |
| **nenhum** (core sozinho) | 2 |

Nos 7 sintéticos mensais o alvo vence em **todos**, com 33-48 B contra 655-2799.
O mecanismo funciona; o regime é que não aparece no corpus disponível.

## 2. O achado: a nature soldada não usa a rota plena

Comparar o alvo mensal (medido por `encode(coluna_transformada)`, que passa pela rota flat
**inteira** — polaridade ADR-0035 + bN ADR-0036) contra o spec soldado (cujo candidato sai
de `_encode_column`, **só o corpo do core**) é comparar rotas diferentes. Corrigido o
método, o "ganho" do alvo mensal em dado real virou **0%** — e a diferença apareceu no
lugar certo:

| coluna real | spec soldado | mesmo payload, rota plena | desperdiçado |
|---|---:|---:|---|
| `real-br-cadastro-nat` | 21366 | 20101 | **1265 B** (5.9%) |
| `real-football-nat` | 16241 | 15021 | **1220 B** (7.5%) |
| `real-football-ord` | 16241 | 15021 | **1220 B** (7.5%) |
| `real-br-abertura-ord` | 16234 | 15026 | **1208 B** (7.4%) |
| `real-tpch-shipdate-nat` | 19236 | 18140 | **1096 B** (5.7%) |
| `real-br-cadastro-ord` | 15460 | 14375 | **1085 B** (7.0%) |
| `real-tpch-orderdate-nat` | 19877 | 18817 | **1060 B** (5.3%) |
| `real-tpch-orderdate-ord` | 13521 | 12612 | **909 B** (6.7%) |
| `real-tpch-sf01-orderdate-ord` | 13521 | 12612 | **909 B** (6.7%) |
| `real-tpch-receiptdate-ord` | 13522 | 12618 | **904 B** (6.7%) |
| `real-tpch-shipdate-ord` | 13442 | 12583 | **859 B** (6.4%) |
| `real-tpch-commitdate-ord` | 13218 | 12371 | **847 B** (6.4%) |

**Mediana 6.7% · 12582 B em 12 colunas.** É o `T-NATURE-CANDIDATO-BN`
medido em dado real pela primeira vez — e ele **não é de data**: vale para qualquer nature
(CPF real: 1372 B = 7,0%).

O conserto é **adicionar candidato ao `min()`**, não trocar a rota: há caso em que a rota
plena PERDE (coluna constante: −7 B), porque paga overhead de bN/polaridade onde não ajuda.

## 3. Todos os casos

| caso | família | n | core | ordinal | mes31dia | fimdemes | anomes | vence | ganho | pin |
|---|---|---:|---:|---:|---:|---:|---:|---|---:|---|
| sint-mensal-dia1 | 600 | 1085 | 679 | 664 | 33 | 3750 | 3745 | **mes31dia** | 95.0% | 15 | ✓ |
| sint-mensal-dia15 | 600 | 1085 | 679 | 664 | 33 | 3750 | 3745 | **mes31dia** | 95.0% | 15 | ✓ |
| sint-mensal-fim | 600 | 6455 | 655 | 642 | 745 | 35 | 5820 | **fimdemes** | 94.5% | 13 | ✓ |
| sint-mensal-faltas | 600 | 2799 | 2799 | 2875 | 48 | 4866 | 4861 | **mes31dia** | 98.3% | -76 | ✓ |
| sint-trimestral | 400 | 3791 | 78 | 78 | 33 | 4363 | 4358 | **mes31dia** | 57.7% | 0 | ✓ |
| sint-ano-mes | 600 | 826 | 826 | 886 | 886 | 890 | 30 | **anomes** | 96.4% | -60 | ✓ |
| sint-misto-d01-d15 | 600 | 7628 | 629 | 618 | 36 | 7340 | 7335 | **mes31dia** | 94.2% | 11 | ✓ |
| ctrl-diario | 600 | 414 | 32 | 32 | 136 | 593 | 404 | **ordinal-soldado** | 0.0% | 0 | ✓ |
| ctrl-uteis | 600 | 2454 | 40 | 40 | 271 | 2762 | 2168 | **ordinal-soldado** | 0.0% | 0 | ✓ |
| ctrl-espalhado | 600 | 6708 | 4062 | 3770 | 3778 | 6777 | 6867 | **ordinal-rota-plena** | 0.0% | 292 | ✓ |
| valv-mensal-sujo-5pct | 600 | 1596 | 1579 | 1502 | 511 | 1846 | 1841 | **mes31dia** | 66.0% | 77 | ✓ |
| valv-mensal-null | 600 | 1143 | 756 | 741 | 86 | 3786 | 3781 | **mes31dia** | 88.4% | 15 | ✓ |
| real-tpch-orderdate-nat | 3000 | 22961 | 19877 | 18817 | 18825 | 23115 | 23279 | **ordinal-rota-plena** | 0.0% | 1060 | ✓ |
| real-tpch-orderdate-ord | 3000 | 18641 | 13521 | 12612 | 12579 | 19988 | 16568 | **mes31dia** | 0.3% | 909 | ✓ |
| real-tpch-shipdate-nat | 3000 | 23004 | 19236 | 18140 | 18144 | 23379 | 23488 | **ordinal-rota-plena** | 0.0% | 1096 | ✓ |
| real-tpch-shipdate-ord | 3000 | 18716 | 13442 | 12583 | 12600 | 18867 | 19016 | **ordinal-rota-plena** | 0.0% | 859 | ✓ |
| real-tpch-commitdate-ord | 3000 | 17941 | 13218 | 12371 | 12412 | 18011 | 18127 | **ordinal-rota-plena** | 0.0% | 847 | ✓ |
| real-tpch-receiptdate-ord | 3000 | 18735 | 13522 | 12618 | 12662 | 19992 | 19876 | **ordinal-rota-plena** | 0.0% | 904 | ✓ |
| real-tpch-sf01-orderdate-ord | 3000 | 18641 | 13521 | 12612 | 12579 | 19988 | 16568 | **mes31dia** | 0.3% | 909 | ✓ |
| real-br-cadastro-nat | 3000 | 28771 | 21366 | 20101 | 20108 | 29429 | 29612 | **ordinal-rota-plena** | 0.0% | 1265 | ✓ |
| real-br-cadastro-ord | 3000 | 25718 | 15460 | 14375 | 14400 | 26082 | 26331 | **ordinal-rota-plena** | 0.0% | 1085 | ✓ |
| real-br-abertura-ord | 3000 | 28840 | 16234 | 15026 | 15027 | 28672 | 29066 | **ordinal-rota-plena** | 0.0% | 1208 | ✓ |
| real-receita-yyyymmdd | 3000 | 4145 | 4145 | 4157 | 4157 | 4161 | 4156 | **core** | 0.0% | -12 | ✓ |
| real-retail-datetime | 3000 | 1666 | 1666 | 1677 | 1677 | 1681 | 1676 | **core** | 0.0% | -11 | ✓ |
| real-football-nat | 3000 | 33380 | 16241 | 15021 | 15160 | 31940 | 32226 | **ordinal-rota-plena** | 0.0% | 1220 | ✓ |
| real-football-ord | 3000 | 33380 | 16241 | 15021 | 15160 | 31940 | 32226 | **ordinal-rota-plena** | 0.0% | 1220 | ✓ |

## 4. As provas

Cada caso passou por: **RT estrito** (contra os dados originais), **RT do espelho** do alvo
isolado, **determinismo** (encode 2× byte-idêntico), **nunca-pior** (o FLOOR com alvos nunca
excede o melhor de hoje) e **"o artefato é o wire"** (`.tcf` lido em binário == wire medido).

O `espera` de [`casos.py`](casos.py) é um **PIN** fixado no comportamento medido: mover a
fronteira do FLOOR de propósito quebra o lab.
