# Procedência dos dados — e os vieses declarados

## Dado REAL, do corpus — nada sintético aqui

Ao contrário do lab `…-0400` (inteiramente sintético), **todas as colunas deste lab vêm de
`Z:/tcf-data/interim/`**, lidas em modo somente-leitura via `file:...?mode=ro`. Nenhum download:
o corpus já existe na máquina.

| coluna | banco | tabela.coluna | grafia |
|---|---|---|---|
| `tpch-orderdate` | `tpch-sf001.db` | `orders.o_orderdate` | `YYYY-MM-DD` |
| `tpch-shipdate` | `tpch-sf001.db` | `lineitem.l_shipdate` | `YYYY-MM-DD` |
| `tpch-commitdate` | `tpch-sf001.db` | `lineitem.l_commitdate` | `YYYY-MM-DD` |
| `tpch-receiptdate` | `tpch-sf001.db` | `lineitem.l_receiptdate` | `YYYY-MM-DD` |
| `tpch01-orderdate` | `tpch-sf01.db` | `orders.o_orderdate` | `YYYY-MM-DD` |
| `br-cadastro` | `br-identidades.db` | `pessoas.data_cadastro` | `YYYY-MM-DD` |
| `br-abertura` | `br-identidades.db` | `empresas.data_abertura` | `YYYY-MM-DD` |
| **`football-date`** | `external/football-results/` | `results.csv:date` | `YYYY-MM-DD` |

n = 2000 por coluna. As derivadas `-ORDENADA` e `-CONTIGUA` são pares de contra-prova sobre
exatamente estas.

**`football-date` é a única coluna real do corpus que já vem ORDENADA** (ND = 100%), e por isso
entra apesar de ser CSV e não `.db` — sem ela, o regime onde `delta`/`delta2` ganham só
existiria no par de contra-prova, isto é, seria medição real de um caso de uso construído.
Span de 1872-11-30 a 2026-07-04 (155 anos).

## Viés 1 — as 8 colunas não são 8 fontes independentes

**Cinco das oito são TPC-H**, geradas pelo mesmo `dbgen` determinístico. Pior: o `tpch-sf001` é
**prefixo** do `tpch-sf01` — o próprio EXP-017 registrou isso (*"LIMIT 3000 puro devolve as
MESMAS linhas do sf001, md5 idêntico"*) e passou a usar `OFFSET 90000` por causa disso; aqui o
passo de amostragem difere (30 contra 300), então as linhas não coincidem, mas **a distribuição
subjacente é a mesma**.

Em identidades independentes são **quatro**: TPC-H `orders`, TPC-H `lineitem`, `br-identidades`,
`football-results`.

**Portanto "7 de 8 acertos" deve ser lido como "quatro origens, das quais três concordaram"** —
e o `result.md` diz isso explicitamente. É o motivo de os dois blocos de contra-prova existirem:
eles variam a coluna, não a fonte.

## Viés 2 — a amostragem, que neste lab virou objeto de medição

O projeto usa **passo espalhado** (`v[::k]`) para evitar viés de cabeça. Este lab mediu que essa
convenção **não é neutra** quando o eixo lê vizinhos:

| `l_shipdate` | \|Δ\| mediano | saltos ≤31d | deltas distintos |
|---|---:|---:|---:|
| coluna inteira (600572 linhas) | 50 | 34,7% | 2422 |
| espalhada `v[::300]` | **710** | **2,6%** | 1249 |
| contígua (2000 do meio) | 51 | 32,8% | 499 |

Causa: `lineitem` está fisicamente ordenada por `l_orderkey` e as datas de um mesmo pedido são
próximas; passo 300 sempre cai em outro pedido. **A amostra espalhada mede só a distribuição
"entre pedidos".**

Por isso o Bloco 1c mede as duas lado a lado. A janela contígua é tomada **do meio**
(`(len-n)//2`), não da cabeça — o viés que o passo espalhado existia para evitar continua
evitado.

## Viés 3 — só UMA coluna real está ordenada

ND% fica em 49,3–51,0 em sete das oito: cara-ou-coroa. Isso não é escolha do lab, é o corpus.
A oitava (`football-date`) é a única com ND = 100%.

A consequência para a leitura dos números: os **71,0%** do `football` são **um** caso real de
regime ordenado, não uma amostra de casos reais. E os **78,5–84,8%** do Bloco 1b continuam sendo
medição real de um cenário **construído** — reais como medição, hipotéticos como frequência no
mundo.

## O que ficou de fora, e por quê

- **`receita-cnpj.data_inicio`** (`YYYYMMDD`, 8 chars) e **`online-retail.InvoiceDate`**
  (`YYYY-MM-DD HH:MM:SS`, 19 chars): nenhuma transformação deste lab se aplica — o guard de
  re-emissão do `data_iso` recusa, corretamente. Já cobertas pelo `T-DATA-GRAFIAS-IRMAS`.
  São **as duas grafias irmãs**, e continuam sendo o gap conhecido do spec.
- **As 3 colunas de `lineitem` do `tpch-sf01`**: prefixo-equivalentes às do `sf001`, que já
  estão aqui. Medi-las seria contar a mesma distribuição duas vezes.
- **`beijing-pm25.db`**: arquivo de 0 bytes; o CSV correspondente tem a data decomposta em
  `year,month,day` inteiros, ou seja, não é coluna de data.

## O que NÃO foi medido

- **A interação com o multi-col, o `.8H` e o split real.** O `componentes` daqui é single-col.
- **Colunas maiores que n=2000.** A lacuna do bN varia com `n` (registrado no `STATUS.md:56`:
  mesma coluna, 6,4% em n=200 → 0,24% em n=15000); nada garante que 52% se mantenha em n=600k.
- **Máquina quiescente.** O Bloco 2 é **dev-run declarado** — razões, não absolutos.
