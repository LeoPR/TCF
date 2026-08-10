# EXP-017 — alvos mensais de data: relatório

**Gerado por `run.py`.** 27 casos · **0 falhas**.
`src/tcf` não é tocado; os alvos são protótipos de [`specs.py`](specs.py).
**Este relatório incorpora as correções de uma caçada adversarial de 4 lentes**
(613 colunas varridas, 15 variantes realistas construídas) — as ressalvas abaixo
são dela.

## A resposta, com as ressalvas que ela precisa

**Nos dados de fato crus do corpus, os alvos mensais não pagam** — nenhuma das 9
colunas lógicas de data tem cadência mensal (varredura exaustiva: todas têm os 31
dias-do-mês quase uniformes). Ganho mediano real: **0.0%** (neste n).

As TRÊS ressalvas que impedem a manchete simples:

1. **O "0%" é propriedade do n amostrado, não do dado**: a mesma coluna TPC-H dá
   0,3% em n=3000 e **18,7% em n=4000** (o candidato ordinal cai num penhasco entre
   n=3850-3900). Instabilidades de pré-passe criam penhascos — ver `T-PENHASCO-INICIO`.
2. **O regime mensal é ALCANÇÁVEL a partir do corpus**: colunas de agregado mensal
   derivadas do mesmo dado real (um registro por mês presente — a forma de qualquer
   tabela de agregado) ganham **1,8× a 9,8×**. O que não tem regime mensal são as
   colunas de FATO cruas.
3. **O "95% sintético" (95.0% aqui) é O(n) e frágil**: em n=12 o alvo PERDE;
   com o escorregamento real de fim de semana (~29%) sobra 1,5×; com jitter ±2 dias,
   1,1×. E folha de pagamento (último/5º dia útil) fica NEGATIVA nos 3 alvos — mas um
   4º eixo (dia ÚTIL) recupera 99,0%. **Nenhum conjunto fixo de alvos cobre; é o
   argumento medido para "spec orienta eixos, não manda alvo"** (direção do owner).

## 1. Placar

| onde vence | reais |
|---|---:|
| **ordinal-dia** (o spec de hoje) | 9 |
| alvo **mensal** | 2 — ambos por acidente estrutural de 0,1-0,3%, não regime |
| **nenhum** (core sozinho) | 2 |

## 2. O achado transversal: a nature soldada não usa a rota plena

O candidato interno da nature sai de `_encode_column` — só o corpo do core, **sem
polaridade e sem bN** — enquanto a rota flat normal aplica os dois (provado byte-exato:
`encode(vals, nature=SPEC) == header + _encode_column(transformed)` em 20/20 colunas
reais onde a nature vence).

| coluna real | spec soldado | mesmo payload, rota plena | desperdiçado |
|---|---:|---:|---|
| `real-br-cadastro-nat` | 21366 | 20101 | **1265 B** (5.9%) |
| `real-football` | 16241 | 15021 | **1220 B** (7.5%) |
| `real-br-abertura-ord` | 16234 | 15026 | **1208 B** (7.4%) |
| `real-tpch-shipdate-nat` | 19236 | 18140 | **1096 B** (5.7%) |
| `real-br-cadastro-ord` | 15460 | 14375 | **1085 B** (7.0%) |
| `real-tpch-orderdate-nat` | 19877 | 18817 | **1060 B** (5.3%) |
| `real-tpch-orderdate-ord` | 13521 | 12612 | **909 B** (6.7%) |
| `real-tpch-receiptdate-ord` | 13522 | 12618 | **904 B** (6.7%) |
| `real-tpch-sf01-orderdate-ord` | 13476 | 12612 | **864 B** (6.4%) |
| `real-tpch-shipdate-ord` | 13442 | 12583 | **859 B** (6.4%) |
| `real-tpch-commitdate-ord` | 13218 | 12371 | **847 B** (6.4%) |

Recalibrado pela caçada: **mediana ~5,7% no corpus amplo** (não os 6,7% deste
subconjunto), máx **11,9%** (CPF `socio_cpf` — a lacuna vale para QUALQUER nature),
**variando com n** (a mesma coluna vai de 6,4% em n=200 a 0,24% em n=15000). Os
"negativos" de versões anteriores eram artefato de métrica (a lacuna só é interpretável
quando a nature vence o FLOOR — casos agora marcados `n/i`). E a rota plena **é
nunca-pior por construção** (o FLOOR da polaridade devolve sufixo vazio quando não paga;
stress de 8000 colunas, 0 violações) — o conserto do `T-NATURE-CANDIDATO-BN` é trocar o
corpo do candidato pela rota plena, mantendo o FLOOR nature-vs-baseline que já existe.

## 3. Todos os casos

| caso | família | n | core | ordinal | mes31dia | fimdemes | anomes | vence | ganho | pin |
|---|---|---:|---:|---:|---:|---:|---:|---|---:|---|
| sint-mensal-dia1 | 600 | 1085 | 679 | 664 | 33 | 3750 | 3745 | **mes31dia** | 95.0% | 15 | ✓ |
| sint-mensal-dia15 | 600 | 1085 | 679 | 664 | 33 | 3750 | 3745 | **mes31dia** | 95.0% | 15 | ✓ |
| sint-mensal-fim | 600 | 6455 | 655 | 642 | 745 | 35 | 5820 | **fimdemes** | 94.5% | 13 | ✓ |
| sint-mensal-faltas | 600 | 2799 | 2799 | 2875 | 48 | 4866 | 4861 | **mes31dia** | 98.3% | n/i | ✓ |
| sint-trimestral | 400 | 3791 | 78 | 78 | 33 | 4363 | 4358 | **mes31dia** | 57.7% | 0 | ✓ |
| sint-ano-mes | 600 | 826 | 826 | 886 | 886 | 890 | 30 | **anomes** | 96.4% | n/i | ✓ |
| sint-misto-d01-d15 | 600 | 7628 | 629 | 618 | 36 | 7340 | 7335 | **mes31dia** | 94.2% | 11 | ✓ |
| ctrl-diario | 600 | 414 | 32 | 32 | 136 | 593 | 404 | **ordinal-soldado** | 0.0% | 0 | ✓ |
| ctrl-uteis | 600 | 2454 | 40 | 40 | 271 | 2762 | 2168 | **ordinal-soldado** | 0.0% | 0 | ✓ |
| ctrl-espalhado | 600 | 6708 | 4062 | 3770 | 3778 | 6777 | 6867 | **ordinal-rota-plena** | 0.0% | 292 | ✓ |
| valv-mensal-sujo-5pct | 600 | 1596 | 1579 | 1502 | 511 | 1846 | 1841 | **mes31dia** | 66.0% | 77 | ✓ |
| valv-sujeira-no-inicio | 600 | 5900 | 4500 | 4318 | 4089 | 3825 | 3820 | **anomes** | 11.5% | 182 | ✓ |
| valv-ym-unicode | 600 | 862 | 862 | 924 | 924 | 928 | 70 | **anomes** | 91.9% | n/i | ✓ |
| valv-mensal-null | 600 | 1143 | 756 | 741 | 86 | 3786 | 3781 | **mes31dia** | 88.4% | 15 | ✓ |
| real-tpch-orderdate-nat | 3000 | 22961 | 19877 | 18817 | 18825 | 23115 | 23279 | **ordinal-rota-plena** | 0.0% | 1060 | ✓ |
| real-tpch-orderdate-ord | 3000 | 18641 | 13521 | 12612 | 12579 | 19988 | 16568 | **mes31dia** | 0.3% | 909 | ✓ |
| real-tpch-shipdate-nat | 3000 | 23004 | 19236 | 18140 | 18144 | 23379 | 23488 | **ordinal-rota-plena** | 0.0% | 1096 | ✓ |
| real-tpch-shipdate-ord | 3000 | 18716 | 13442 | 12583 | 12600 | 18867 | 19016 | **ordinal-rota-plena** | 0.0% | 859 | ✓ |
| real-tpch-commitdate-ord | 3000 | 17941 | 13218 | 12371 | 12412 | 18011 | 18127 | **ordinal-rota-plena** | 0.0% | 847 | ✓ |
| real-tpch-receiptdate-ord | 3000 | 18735 | 13522 | 12618 | 12662 | 19992 | 19876 | **ordinal-rota-plena** | 0.0% | 904 | ✓ |
| real-tpch-sf01-orderdate-ord | 3000 | 18633 | 13476 | 12612 | 12598 | 20024 | 16631 | **mes31dia** | 0.1% | 864 | ✓ |
| real-br-cadastro-nat | 3000 | 28771 | 21366 | 20101 | 20108 | 29429 | 29612 | **ordinal-rota-plena** | 0.0% | 1265 | ✓ |
| real-br-cadastro-ord | 3000 | 25718 | 15460 | 14375 | 14400 | 26082 | 26331 | **ordinal-rota-plena** | 0.0% | 1085 | ✓ |
| real-br-abertura-ord | 3000 | 28840 | 16234 | 15026 | 15027 | 28672 | 29066 | **ordinal-rota-plena** | 0.0% | 1208 | ✓ |
| real-receita-yyyymmdd | 3000 | 4145 | 4145 | 4157 | 4157 | 4161 | 4156 | **core** | 0.0% | n/i | ✓ |
| real-retail-datetime | 3000 | 1666 | 1666 | 1677 | 1677 | 1681 | 1676 | **core** | 0.0% | n/i | ✓ |
| real-football | 3000 | 33380 | 16241 | 15021 | 15160 | 31940 | 32226 | **ordinal-rota-plena** | 0.0% | 1220 | ✓ |

## 4. As provas — e o que cada uma vale

**RT estrito** e **RT do espelho** são as provas falsificáveis (o guard de re-emissão do
YM veio delas: dígitos Unicode colapsavam payloads — 4ª ocorrência da classe).
**Determinismo** e **artefato-é-o-wire** idem. **"Nunca-pior"** neste harness é
tautologia (min sobre superconjunto) — fica como documentação da invariante; a prova
real é pós-weld. Os **PINs** estão fixados no comportamento medido; os dois casos
`mensal` reais estão anotados como ruído de 0,1-0,3%, não regime.
