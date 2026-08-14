# Proveniência dos dados

**Corpus REAL**, lido de `Z:/tcf-data/interim/*.db` pelo `extrai.py`. Nada foi baixado — a
regra do projeto é que dados grandes vivem no hub e nunca se baixa quando ele já tem.

As fatias ficam congeladas em `inputs/fontes/`, para que `run.py` rode **sem `Z:`**.

## Descoberta automática, e por quê

O `extrai.py` **varre** os bancos e pega toda coluna de tipo numérico declarado com ao menos
200 linhas e ao menos 2 valores distintos. Não escolhi colunas a dedo, e a razão é registrada:
escolher a dedo seria montar o corpus para a resposta que eu queria — o erro que o projeto já
nomeou como *"benchmark que embute a própria resposta"*.

Filtros aplicados (todos declarados no código): só `int` puro nesta rodada (float é caso
próprio, já registrado); colunas constantes fora (não ensinam nada aqui); `N_MAX = 3000`.

Cada coluna sai em **duas ordens** — natural e ordenada — porque a ordem é a maior alavanca
conhecida do projeto.

## O que veio: 39 colunas

| origem | colunas | o que são |
|---|---:|---|
| **TPC-H** (sf001 + sf01) | **25** | chaves (`orderkey`, `partkey`, `custkey`, `suppkey`), `linenumber`, `size`, `availqty`, `nationkey` |
| br-identidades | 2 | ids de município |
| IBGE | 1 | id de município |
| online-retail | 1 | `quantity` (tem negativos) |
| wine-quality | 1 | nota de qualidade (k=7) |
| demais | 9 | variadas |

## ⚠ Viés declarado — leia antes de generalizar

**25 das 39 colunas (64%) vêm de TPC-H**, que é um **gerador sintético de benchmark**, não
dado de produção. Ele produz muitas chaves sequenciais densas — exatamente o regime que
**favorece o PAD**. As colunas de origem independente são **14**.

Consequências para a leitura dos resultados:

- o ganho do PAD (mediana 1,72×) está **provavelmente superestimado** para dado de produção
  genérico;
- a ausência de ganho do `min_len` reflete a **ausência de timestamps e bases altas** neste
  corpus, não uma propriedade do mecanismo;
- a proporção "18 de 39 sem ganho" é específica deste conjunto.

O que o lab sustenta com firmeza é a **ordem relativa** entre os mecanismos e a **calibração
dos gatilhos** — não os valores absolutos como previsão universal.

Nenhum dado pessoal: as colunas são chaves, quantidades e ids numéricos. As de
`br-identidades` e `receita-cnpj` que entraram são **ids de município**, não documentos.
