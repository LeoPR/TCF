# EXP-017 — alvos mensais de data: bateria probatória [clean]

**Lab clean** que testa os **alvos mensais** de data (`mês×31+dia`, fim-de-mês, `YYYY-MM`)
contra o `SPEC_DATA_ISO` soldado, em **corpus real + sintético**. Consolida o estudo dirty
de 2026-08-09 (labs `1853` e `2228`) numa bateria declarativa e auto-verificável, no molde
do [EXP-016](../EXP-016-bn-familia-bits/README.md).

```
python extrai.py    # (uma vez) congela as colunas reais de Z:/tcf-data em inputs/
python run.py       # regenera outputs/ e report.md; exit 0 só se tudo fechar
```

Estado atual: **26 casos, 0 falhas.** `src/tcf` **não é tocado** — os alvos são protótipos
em [`specs.py`](specs.py), e o núcleo entra pelos `encode()`/`decode()` reais.

## O que este lab respondeu

**A pergunta era "vai fechar?" — e a resposta é não, pelo motivo que interessa.** Os alvos
mensais ganham **95%** nos sintéticos e **0%** nos reais, porque **nenhuma das 14 colunas
reais tem cadência mensal**: o corpus disponível é todo diário/transacional. O mecanismo
está certo; o regime-alvo não está representado.

**E o lab achou algo maior no caminho**: corrigir o método de comparação expôs que o
candidato interno da nature soldada não passa pela rota plena (sem polaridade, sem bN) —
**mediana 6,7% desperdiçado** em dado real, e vale para **qualquer** nature, não só data.
Detalhe em [`report.md`](report.md) §2.

## O corpus real (congelado em `inputs/`)

10 colunas × 2 ordens (natural e ordenada — a ordem é a maior alavanca conhecida do
projeto), 3000 valores cada, extraídas de `Z:/tcf-data/`:

| fonte | colunas | o que exercita |
|---|---|---|
| TPC-H sf001/sf01 | `o_orderdate`, `l_shipdate`, `l_commitdate`, `l_receiptdate` | data comercial, k alto, colunas irmãs |
| br-identidades | `data_cadastro`, `data_abertura` | cadastro BR, span curto e longo |
| receita-cnpj | `data_inicio` | **`YYYYMMDD` compacto** — o spec recusa por design |
| online-retail | `InvoiceDate` | **datetime com hora** — não é date puro |
| football-results | `date` | **1872..hoje**, o maior span do corpus |

## Os arquivos

| arquivo | o quê |
|---|---|
| [`extrai.py`](extrai.py) | lê os hubs em `Z:` e congela fatias em `inputs/` (roda uma vez) |
| [`specs.py`](specs.py) | os alvos-protótipo, no mesmo protocolo per-valor-com-válvula das natures soldadas |
| [`casos.py`](casos.py) | catálogo declarativo: cada caso declara **quem deve vencer** o FLOOR |
| [`run.py`](run.py) | roda, aplica as 5 provas, gera `outputs/` e `report.md` |
| `outputs/<caso>.tcf` | o wire vencedor de cada caso |
| `outputs/medicoes.json` | tudo em máquina (bytes por candidato, lacuna de rota, CPU, memória) |

## As cinco provas

| prova | o que garante |
|---|---|
| **RT estrito** | `decode(encode(v)) == v` contra os dados **originais** |
| **RT do espelho** | `decode_col(encode_col(v)) == v` — o alvo isolado, sem o núcleo |
| **determinismo** | `encode` 2× byte-idêntico — o FLOOR não pode depender de ordem |
| **nunca-pior** | o FLOOR com alvos **nunca** excede o melhor de hoje |
| **o artefato é o wire** | o `.tcf` lido em **binário** == o wire medido (pega CRLF do Windows) |

Mais o **PIN**: `espera` em `casos.py` está fixado no comportamento medido — mover a
fronteira do FLOOR de propósito quebra o lab, que é o ponto.
