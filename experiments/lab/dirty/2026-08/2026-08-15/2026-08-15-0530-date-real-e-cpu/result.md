# Resultado — o date em dado REAL, e o preço do `min()` ampliado

Fecha as duas ressalvas que o lab `…-0400` deixou abertas: **tudo era sintético** e **CPU não
foi medida**. 8 colunas reais × 3 amostragens × 6 transformações, com predição declarada antes
de cada medição, **0 falhas** de RT. Orienta, não fecha.

---

## O resumo em três linhas

1. **`componentes` vence nas 7 colunas embaralhadas** (51,9–55,1% sobre o ordinal welded) e não
   sai do lugar: nem reordenando, nem mudando a amostragem.
2. **`delta` vence na única coluna real já ordenada** (`football-date`), com **71,0%** — em
   ordem física, sem reordenar nada.
3. **`delta2` — que era o achado do lab sintético — não venceu uma única vez em 24 medições.**

O `min()` ampliado custa **+47,7% a +86,1%** de encode.

---

## 1. As colunas reais, com a predição declarada antes da medição

A disciplina: classificar o regime, **declarar** o que a partição sintética prevê, e só então
medir. Sem isso, "o `delta` ganhou" é indistinguível de pescaria.

| coluna | n | k | ND% | ordinal (welded) | melhor | ganho | previu | acertou |
|---|---:|---:|---:|---:|---:|---:|---|:--:|
| `br-abertura` | 2000 | 1694 | 51,0 | 13939 | **6264** `componentes` | **55,1%** | componentes | ✓ |
| `br-cadastro` | 2000 | 1607 | 50,0 | 13645 | **6234** `componentes` | **54,3%** | componentes | ✓ |
| `tpch-orderdate` | 2000 | 1370 | 49,4 | 12886 | **6170** `componentes` | **52,1%** | componentes | ✓ |
| `tpch-receiptdate` | 2000 | 1377 | 49,5 | 12866 | **6170** `componentes` | **52,0%** | componentes | ✓ |
| `tpch-shipdate` | 2000 | 1365 | 49,3 | 12835 | **6170** `componentes` | **51,9%** | componentes | ✓ |
| `tpch-commitdate` | 2000 | 1359 | 49,6 | 12827 | **6170** `componentes` | **51,9%** | componentes | ✓ |
| `tpch01-orderdate` | 2000 | 1350 | 49,7 | 12815 | **6170** `componentes` | **51,9%** | componentes | ✓ |
| **`football-date`** | 2000 | 1880 | **100,0** | 11625 | **3368** `delta` | **71,0%** | delta2 | ✗ |

**7 de 8**, com **dois vencedores distintos** — e é a oitava linha que dá valor às sete
primeiras. Sem ela, as 7 previram a mesma coisa e o teste cobriria uma célula da partição, não
a partição.

**Por que as sete concordam**: nenhuma está ordenada. ND% fica em 49,3–51,0 — cara-ou-coroa,
com repetição adjacente ~0%. O dado está fisicamente embaralhado, e aí só a igualdade sobrevive.

**Por que a oitava discorda**: `football-date` é a única coluna do corpus que já vem ordenada
(ND=100%), com \|Δ\| mediano de 11 dias e 83,6% dos saltos dentro de um mês. Contra o spec de
hoje (12548 B) o ganho é **73,2%**.

---

## 2. Contra-prova A — as mesmas colunas ORDENADAS

Mesmos valores, mesma cardinalidade. **Só a ordem muda.** Se a predição não mudar, o
classificador é um carimbo.

| coluna | previu | mediu | ordinal | melhor | ganho |
|---|---|---|---:|---:|---:|
| `tpch-orderdate` | delta | **delta** ✓ | 9155 | **1387** | **84,8%** |
| `tpch-shipdate` | delta | **delta** ✓ | 9169 | **1392** | **84,8%** |
| `tpch01-orderdate` | delta | **delta** ✓ | 9195 | **1395** | **84,8%** |
| `tpch-commitdate` | delta | **delta** ✓ | 9093 | **1388** | **84,7%** |
| `tpch-receiptdate` | delta2 | delta ✗ | 9186 | 1399 | 84,8% |
| `br-abertura` | delta2 | delta ✗ | 10564 | 2170 | 79,5% |
| `br-cadastro` | delta2 | delta ✗ | 10068 | 2161 | 78,5% |
| `football-date` | delta2 | delta ✗ | 11625 | 3368 | 71,0% |

- **A predição mudou em 7 de 8** ao ordenar — o classificador *é* um classificador.
- **4 de 8 acertos**, e as 4 falhas são todas idênticas: previu `delta2`, mediu `delta`.

---

## 3. Contra-prova B — a amostragem é uma transformação

**Este bloco existe porque eu errei o método**, e o erro só apareceu ao medir a coluna inteira.
Amostrei com passo espalhado (`v[::300]`) — a convenção do projeto, que existe para evitar viés
de cabeça. Mas `lineitem` está fisicamente ordenada por `l_orderkey` e as datas de um mesmo
pedido são próximas: **passo 300 pula sempre para outro pedido.**

| `l_shipdate` | \|Δ\| mediano | saltos ≤31d | deltas distintos |
|---|---:|---:|---:|
| coluna inteira (600572) | 50 | 34,7% | 2422 |
| **espalhada `v[::300]` (o que o Bloco 1 viu)** | **710** | **2,6%** | 1249 |
| contígua (2000 do meio) | 51 | 32,8% | 499 |

**Para transformações que leem vizinhos, o passo espalhado não é uma amostra — é uma
transformação dos dados.**

### O que declarei antes de rodar, e o que aconteceu

> **(a)** o classificador vai prever igual, porque a regra lê **ordem** e **contagem**, nunca
> **magnitude**; **(b)** a medição **pode virar para `delta`** no TPC-H, porque o alfabeto cai
> pela metade e os saltos ficam pequenos.

**(a) quase se confirmou: 7 de 8. (b) foi REFUTADA: o vencedor virou em 0 de 8.**

| coluna | amostra | \|Δ\| med | Δdist | delta | componentes | vencedor |
|---|---|---:|---:|---:|---:|---|
| `tpch-commitdate` | espalhada | 700 | 1558 | 9696 | **6170** | componentes |
| | **contígua** | **26** | **559** | 9376 | **6170** | componentes |
| `tpch-shipdate` | espalhada | 700 | 1544 | 9669 | **6170** | componentes |
| | **contígua** | **50** | **642** | 9855 | **6170** | componentes |
| `br-abertura` | espalhada | 1704 | 1804 | 10300 | **6264** | componentes |
| | contígua | 1753 | 1810 | 10366 | **6260** | componentes |
| `football-date` | espalhada | 11 | 155 | **3368** | 8200 | delta |
| | contígua | **0** | **10** | **1388** | 3211 | delta |

O `delta` mal se mexe no TPC-H (9696 → 9376, −3,3%) mesmo com o \|Δ\| mediano caindo **27×**. O
`componentes` fica **constante em 6170 B** — insensível à ordem *e* à amostragem, porque
decompõe em três alfabetos pequenos cujo multiconjunto quase não muda.

**Minha predição estava errada, e o resultado ficou mais forte do que se estivesse certa**: o
`componentes` não vence por acidente de amostragem, e o `delta` do `football` também não.

---

## 4. O classificador: 18 de 24, e as duas falhas são diagnosticáveis

| bloco | acertos |
|---|---|
| 1 — ordem física, espalhada | 7 de 8 |
| 1b — ordenadas | 4 de 8 |
| 1c — contíguas | 7 de 8 |
| **total** | **18 de 24 (75%)** |

As 6 falhas são de **exatamente dois tipos**, e ambos erram na mesma direção — **subestimam o
`delta`**:

1. **Previu `delta2`, mediu `delta`** (5 casos). A regra manda `delta2` quando há muitos deltas
   distintos, mas em coluna real ordenada os deltas são muitos **e pequenos** — regime do
   `delta`, não da 2ª diferença.
2. **Previu `componentes` numa coluna ORDENADA, mediu `delta`** (1 caso, `football` contígua).
   A regra testa `repetição > 50%` **antes** de testar a ordem; com 75,5% de repetição ela
   manda `componentes`. Mas numa coluna ordenada, valor repetido vira **Δ = 0**, e uma fila de
   zeros é o que o seq-RLE do núcleo come melhor: `delta` faz 1388 contra 3211.

Ou seja: **o primeiro ramo da regra precisa ser condicionado à coluna estar desordenada.** Em
dado real, `delta` venceu 10 vezes e `delta2` venceu **zero**.

---

## 5. Por que a entropia previu o contrário — e por que o byte manda

Uma análise de entropia de ordem zero prevê `delta` para as colunas do TPC-H, com folga:

| coluna (contígua) | H(valor) | H(Δ) | H(ano)+H(mês)+H(dia) |
|---|---:|---:|---:|
| `tpch-shipdate` | 10,24 | **8,55** | 11,31 |
| `tpch-commitdate` | 10,21 | **7,91** | 11,31 |
| `br-abertura` | 10,62 | 10,77 | 12,67 |

Pela entropia, `componentes` é a **pior** das três — perde do `delta` por 2,76 bits/linha no
`shipdate`. **Medido em bytes pelo encoder real, ele ganha por 1,60×.**

A causa é estrutural: **o núcleo do TCF não é um codificador de entropia** — é texto com
dicionário e tokenizador (OBAT). Três alfabetos pequenos de strings curtas e muito repetidas
(`1995`, `03`, `14`) são baratos de um jeito que a entropia de ordem zero não enxerga; um
alfabeto médio de strings numéricas variadas (`-437`, `+1203`) é caro.

**Consequência de método, e vale além do date**: entropia é o comparador errado para escolher
candidato no TCF. Serve de intuição, não de evidência — a evidência é o byte pelo encoder real.
É a §RT aplicada à escolha de transformação.

---

## 6. O nicho do `delta2` não existe no corpus

Era **o achado** do lab `…-0400`: `esparsa-ordenada`, 3854 → **605 B**, 84,3% — o único
candidato clássico de série temporal que o projeto nunca havia tocado.

**Em dado real não venceu uma única vez, nas 24 medições.** Na ordem física perde para
`componentes` ou `delta`; ordenada, perde para o `delta` em 8 de 8. O único lugar onde chega
perto é `lineitem` contígua (9347 contra 9855 do `delta`) — e ali os dois perdem do
`componentes` por 1,5×.

É **o precedente do `T-DATA-ALVO-MENSAL` se repetindo**: 95% em sintético, 0,0% em real. O
`delta2` merece registro como candidato conhecido, **não como motivo para mexer no formato**.

---

## 7. O preço: a CPU do `min()` ampliado

Duas rodadas, **dev-run declarado** — máquina não quiescente, portanto **razões, não absolutos**.

| | faixa medida | pico de memória |
|---|---|---|
| rodada 1 (7 colunas) | +49,4% a +61,8% | 3,6–4,6 MB |
| rodada 2 (8 colunas) | **+47,7% a +86,1%** | 3,6–4,3 MB |

Réguas do projeto: o `T-CANDIDATO-SEM-DEDUP` mediu **+84–93%** para **um** candidato análogo; o
split mede **+47–54%**. Seis candidatos custando +50–86% fica **dentro** da faixa que o projeto
já pagou por um — o `min()` ampliado não é proibitivo por CPU.

**A objeção real não é CPU: é que 4 dos 6 candidatos nunca vencem em dado real.** Um `min()` de
três (`ordinal`, `componentes`, `delta`) cobriria as 8 colunas.

---

## 8. O inventário do corpus — e uma contagem errada no `STATUS.md`

Varredura por **valor** (grafia sobre todas as colunas de todas as tabelas), não por nome:

- **13 colunas de data físicas** — 12 nos `.db` de `Z:/tcf-data/interim/` + 1 no CSV do
  `football-results`;
- **9 identidades independentes** — as 4 colunas de data do `tpch-sf001` são prefixo do
  `tpch-sf01` (o próprio EXP-017 já registrava isso para `orderdate`: *"LIMIT 3000 puro devolve
  as MESMAS linhas do sf001, md5 idêntico"*, e por isso usa `OFFSET 90000`).

O `STATUS.md:71` diz *"das 12 colunas de data do corpus (10 distintas)"*. Esse **10** é o
tamanho da lista `FONTES` do EXP-017 (`extrai.py:37-51`) — que é uma **seleção**, não o
inventário: conta `orderdate` duas vezes (sf001 e sf01 com offset) e **omite as 3 colunas de
`lineitem` do `sf01`**. Vale corrigir o `STATUS.md`; não muda nenhuma conclusão medida.

---

## 9. Ressalvas honestas

- **As 8 colunas não são 8 fontes.** Cinco são TPC-H (mesmo `dbgen`), quatro delas de um banco
  que é prefixo do outro. Em identidades independentes são **quatro**: TPC-H `orders`, TPC-H
  `lineitem`, `br-identidades`, `football-results`.
- **A coluna ordenada é uma só.** Os 71,0% do `football` são um caso real, não uma amostra de
  casos reais. Os 78,5–84,8% do Bloco 1b continuam sendo medição real de um cenário construído.
- **Duas grafias reais ficaram de fora**: `receita-cnpj` (`YYYYMMDD`) e `online-retail`
  (`YYYY-MM-DD HH:MM:SS`). Nenhuma transformação daqui se aplica — o guard de re-emissão do
  `data_iso` recusa, corretamente. Já cobertas pelo `T-DATA-GRAFIAS-IRMAS`.
- **`componentes` não é o `split` do formato** — é a mesma ideia numa lista só, para caber no
  single-col. O split real é multi-col embutido.
- **n = 2000.** A lacuna do bN varia com `n` (`STATUS.md:56`: mesma coluna, 6,4% em n=200 →
  0,24% em n=15000); nada garante que 52% se mantenha em n=600k.
- **Nada aqui é proposta de weld.** `src/tcf` intocado.

---

## 10. O que isto orienta

1. **`componentes` é o candidato que o dado real pede** — 51,9–55,1% sobre o ordinal welded, em
   7 de 8 colunas, estável a ordem e a amostragem.
2. **`delta` é o segundo, e tem caso real** — `football-date`, 71,0% em ordem física. Não é mais
   hipotético.
3. **`delta2` não tem caso real.** Registrar como conhecido; não usar como motivo.
4. **O `min()` que o corpus pede tem três candidatos, não seis** — e custa dentro da faixa que o
   projeto já pagou por um.
5. **A decisão de design continua sendo o protocolo de transformação de COLUNA.** Mas agora tem
   preço medido (+48–86% de encode) e ganho medido em dado real (52% e 71%), em vez de só
   sintético.
6. **Corrigir a régua de amostragem do projeto**: para qualquer eixo que leia vizinhos, o passo
   espalhado precisa de par contíguo. Isso não vale só para o date.
