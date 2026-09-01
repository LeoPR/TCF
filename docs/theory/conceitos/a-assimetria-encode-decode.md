---
title: "A assimetria: o encode paga, o decode colhe"
type: explanation
parent: theory
subsystem: conceitos
---

# A assimetria: o encode paga, o decode colhe

> O TCF é caro de escrever e barato de ler, **de propósito**. Esta página diz o quanto, por
> que a troca é essa, e onde ela **não** vale, que é a parte que costuma ser omitida.

## O quanto

Encode contra decode, mesmo dado, melhor de sete medições:

| dado (2.000 a 5.000 linhas) | encode | decode | razão |
|---|---:|---:|---:|
| categórico de baixa cardinalidade | 55,0 ms | 13,3 ms | 4,1× |
| IDs zero-padded | 135,4 ms | 37,2 ms | 3,6× |
| tabela mista (categórico + data + contador) | 142,9 ms | 16,5 ms | 8,7× |
| **texto livre repetitivo** | **5.914,2 ms** | **5,6 ms** | **1.060×** |

A última linha não é defeito, é a tese levada ao extremo: quase seis segundos para escrever,
cinco milissegundos e meio para ler.

## Por que a troca é essa

**A topologia real é 1 encode para N decodes.** Um dado é escrito uma vez e lido muitas: por
cada consumidor, a cada requisição, em cada réplica. Gastar no lado que roda uma vez para
economizar no que roda N vezes é aritmética, não preferência.

E o decode é barato por **construção**, não por otimização. O wire carrega referências, não
buscas: `^N` diz "a string da linha N", `*N|` diz "esta linha, N vezes", `*N+d|` descreve uma
progressão. Ler é **substituição mapeada**, e o trabalho caro (descobrir quais referências
valem a pena) já foi feito por quem escreveu.

O encode carrega esse peso porque é ele quem procura. O OBAT compara cada valor com os
anteriores atrás de afixos comuns, e o HCC procura composições. Procurar é o que custa.

## Onde a leitura é estrutural, e onde não é

Aqui a versão curta da tese engana, e vale a precisão. "O decode é O(1)" **não** é verdade em
geral: o que existe é um conjunto de perguntas que a estrutura responde sem expandir as linhas,
e ele **depende do modo em que a coluna caiu**.

Linhas materializadas para responder cada pergunta, numa tabela de 2.000 × 2:

| coluna | modo | `count()` | `group_count()` | `where().sum()` | `select()` |
|---|---|---:|---:|---:|---:|
| categórico | `@dict` | **0** | **0** | 2.000 | 4.000 |
| IDs | `tcf` (core) | **0** | 2.000 | 4.000 | 4.000 |
| texto | `%split` | **0** | 2.000 | 4.000 | 4.000 |

Três leituras dessa tabela, e as três importam:

**Contar é estrutural em todo modo.** O número de linhas está declarado ou é somável dos
contadores, então `count()` não abre coluna nenhuma. Essa parte da tese vale sempre.

**Agrupar e filtrar sem materializar é propriedade do `@dict`**, não do decode. O dicionário
guarda K únicos mais um stream de índices de largura fixa, então a pergunta se resolve nos K e
numa varredura de bytes, sem construir um único valor. Nos outros modos a mesma pergunta
materializa a coluna.

**O core não tem acesso aleatório.** Ler a linha *i* de uma coluna em modo `tcf` exige replay
de 1 até *i*, porque as referências encadeiam. O `@dict` e o bN denso têm acesso O(1) por
aritmética (`offset = i × width`); o `raw` é O(i), achando o *i*-ésimo LF; o core é
**impossível** sem replay. Isso não é lacuna a preencher: é o preço de o core comprimir por
referência.

## Onde a tese não vale

**Blob genérico não é o alvo.** Numa coluna densa de texto livre o compressor binário vence
sozinho, e pôr TCF por baixo chega a **piorar 41%**, porque reescrever valores como referências
atrapalha o modelo de entropia dele. Numa tabela estruturada a conta inverte: **−72%** contra
CSV, e ainda compõe.

O que decide não é o container, é a **estrutura do dado**. O TCF é para dataset: coluna com
domínio, valor que repete, grafia regular. Onde não há estrutura para explorar, não há o que
o encode caro compre, e a assimetria vira só o custo sem o retorno.

**E o volume importa.** Em payload minúsculo a moldura domina e não há o que fatorar. A
vantagem aparece com linhas.

## O que isso implica para quem usa

A pergunta não é *"o TCF é rápido?"*, é **quem paga o encode e quantas vezes**. O TCF não é
ferramenta de ETL, e medir em massa serve para ordem de grandeza, não para decidir: a decisão é
por topologia.

| topologia | leitura |
|---|---|
| **cliente encoda, servidor consome** (upload, telemetria, sync) | o lado caro fica **distribuído** por muitos clientes, um encode cada, em CPU ociosa; o barato fica no servidor, que decodifica N vezes. É o melhor caso, e é o que a assimetria foi desenhada para servir |
| **servidor encoda o mesmo payload para N clientes** (catálogo, feed, config) | o encode **amortiza sobre N**, e melhora quanto maior o N |
| **servidor encoda payload único por requisição** | é **1 para 1**, e o encode entra no caminho da requisição. Só paga se a rede for o gargalo |
| **disco e armazenamento** | escreve uma vez, lê muitas, o que é favorável; mas o concorrente deixa de ser CSV e passa a ser Parquet e ORC, que são colunares **com índice**. Ainda não medido |

A distinção que decide **não é "cliente ou servidor"**: é **cacheável ou personalizado**. Os dois
casos de servidor estão do mesmo lado do fio e em lados opostos da conta.

O eixo do `.9` é reduzir o lado caro: o encode é o alvo, e a medição já diz por onde começar,
porque o gargalo é **cardinalidade**, não volume. Até lá, nenhum número de encode desta página
deve ser lido como definitivo.

## Ver também

- [O custo da consulta](custo-da-consulta.md), que detalha o lado da leitura
- [O wire em uma página](o-wire-em-uma-pagina.md), para o que as marcas significam
- [Onde a view ganha](../desempenho/onde-a-view-ganha.md)
