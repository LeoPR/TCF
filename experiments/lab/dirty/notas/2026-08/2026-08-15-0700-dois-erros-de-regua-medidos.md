# Dois erros de régua, medidos — e nenhum dos dois é sobre `date`

> Origem: lab [`2026-08-15-0530-date-real-e-cpu`](../../2026-08/2026-08-15/2026-08-15-0530-date-real-e-cpu/).
> O lab era sobre data. Os dois achados abaixo **não são** — atingem qualquer eixo do projeto,
> e por isso saem da pasta do lab.

---

## 1. A entropia é o comparador errado para escolher candidato no TCF

**O que aconteceu.** Uma análise de entropia de ordem zero sobre as colunas de data do corpus
prevê `delta` como vencedor, com folga:

| coluna (`lineitem`, contígua) | H(valor) | H(Δ) | H(ano)+H(mês)+H(dia) |
|---|---:|---:|---:|
| `l_shipdate` | 10,24 | **8,55** | 11,31 |
| `l_commitdate` | 10,21 | **7,91** | 11,31 |

Pela entropia, decompor em componentes é a **pior** das três opções — perde do `delta` por
**2,76 bits/linha**. **Medido em bytes pelo encoder real, `componentes` ganha por 1,60×**
(6170 B contra 9855).

**Por que.** O núcleo do TCF **não é um codificador de entropia**. É texto com dicionário e
tokenizador (OBAT). Três alfabetos pequenos de strings curtas e muito repetidas (`1995`, `03`,
`14`) são baratos para ele de um jeito que H de ordem zero não enxerga; um alfabeto médio de
strings numéricas variadas (`-437`, `+1203`) é caro. A entropia mede informação por símbolo; o
TCF paga por **caractere emitido depois do dicionário**.

**A regra.** Entropia serve de **intuição** para gerar hipótese, nunca de **evidência** para
escolher candidato. É a §RT aplicada à escolha de transformação: *nunca reportar bytes sem RT
validado* vira, aqui, **nunca escolher mecanismo sem byte medido pelo encoder real**.

**Onde isso morde.** Em qualquer avaliação de candidato feita "no papel" — inclusive as que um
agente auxiliar produz rápido, porque calcular H é barato e rodar o encoder é caro. Foi
exatamente o que aconteceu: a análise de entropia previu `delta` para 6 das 13 colunas de data
do corpus; o byte medido deu `componentes` em todas.

---

## 2. O passo espalhado não é uma amostra quando o eixo lê vizinhos

**O que aconteceu.** A convenção do projeto para amostrar coluna real é o **passo espalhado**
(`v[::k]`), que existe para evitar viés de cabeça — e está certa para isso. Mas medindo a coluna
inteira de `lineitem` (600572 linhas) contra as amostras:

| `l_shipdate` | \|Δ\| mediano | saltos ≤31d | deltas distintos |
|---|---:|---:|---:|
| coluna inteira | 50 | 34,7% | 2422 |
| **espalhada `v[::300]`** | **710** | **2,6%** | 1249 |
| contígua (2000 do meio) | 51 | 32,8% | 499 |

**A amostra espalhada mediu uma adjacência que não existe na coluna.**

**Por que.** `lineitem` está fisicamente ordenada por `l_orderkey`, e as datas de um mesmo
pedido são próximas (\|Δ\| mediano 35 dentro do pedido, 704 entre pedidos). Passo 300 cai
**sempre** em outro pedido — então amostra só a distribuição "entre pedidos", que é 1/20 da
população de pares adjacentes.

**A regra.** Para qualquer eixo que leia **vizinhos** — delta, delta², RLE, seq-RLE, periódico,
`*N|<linha>`, qualquer coisa que compare a linha `i` com a `i-1` — o passo espalhado **é uma
transformação dos dados, não uma amostra**. Precisa de **par contíguo**, e a janela contígua
deve vir do **meio** (`(len-n)//2`), não da cabeça, para não reintroduzir o viés que o passo
espalhado evitava.

**Onde isso morde.** Todo lab que mediu mecanismo adjacente em coluna real amostrada com passo
espalhado. Vale reconferir — não porque as conclusões caiam necessariamente (neste lab não
caíram: `componentes` venceu nas duas amostragens), mas porque o **número** pode estar medindo
outra população.

---

## 3. O que os dois têm em comum

Os dois são **atalhos que parecem neutros e não são**: calcular H em vez de rodar o encoder;
pular linhas em vez de ler adjacentes. Cada um troca a coisa medida por um proxy, e em ambos os
casos o proxy **inverteu o resultado ou mudou a população**.

O padrão já está registrado no projeto sob outro nome — *"design-panel não é evidência, só o lab
gravado"* ([`feedback_metodo_lab_verificacao_adversarial`]). Estes dois são o mesmo princípio
descendo um nível: **dentro do lab**, o proxy barato também não é evidência.

## Vínculo

Lab de origem: [`2026-08-15-0530-date-real-e-cpu`](../../2026-08/2026-08-15/2026-08-15-0530-date-real-e-cpu/)
([`result.md` §3 e §5](../../2026-08/2026-08-15/2026-08-15-0530-date-real-e-cpu/result.md)) ·
`T-DATA-ALVO-DELTA` (onde o achado está registrado no `STATUS.md`) ·
`T-DATA-ALVO-MENSAL` / `T-CORPUS-DATA-MENSAL` (o precedente sintético→real, que **se repetiu**
no `delta2` neste mesmo lab) · `T-CANDIDATO-SEM-DEDUP` (a régua de CPU)
