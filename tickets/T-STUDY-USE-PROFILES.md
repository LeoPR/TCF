---
title: T-STUDY-USE-PROFILES, perfis de uso (transmissão × armazenamento) e a calibração dos vértices
status: open
priority: P3
created: 2026-08-20
updated: 2026-09-01
gate: "estudo (alimenta decisao, sem ciclo proprio) (triagem 2026-09-01)"
target: ".9 / pré-1.0 (estudo; nenhuma mudança no .8)"
blocked-by: []
related:
  - docs/adr/0002-vertice-triplice-restricao.md
  - docs/adr/0050-sort-by-vira-candidato-o-floor-decide.md
  - tickets/T-REL-08-CLOSEOUT.md
  - tickets/T-CODE-PARALLEL-BUDGET.md
  - experiments/lab/dirty/notas/diario/2026-08-20.md
  - experiments/lab/dirty/notas/2026-07/contrato-externalizado-e-aceleradores.md
---

# T-STUDY-USE-PROFILES: perfis de uso e a calibração dos vértices

**[dispositivo → registro. SÓ ESTUDAR, não mexer em `src/tcf`.]**

## Contexto

Direção do owner (2026-08-20, diário): o TCF tem **perfis de uso** com economia diferente, e
os vértices ortogonais poderiam ser *calibrados por situação*:

1. **Transmissão assimétrica**: muitos clients gastam tempo comprimindo; um servidor
   central precisa de descompressão rápida. *"O TCF joga as cargas nos lugares corretos."*
2. **Armazenamento**: gasta tempo compactando/guardando uma vez, com a vantagem de decode
   rápido, `view()` lazy nas consultas, e possivelmente índice sidecar (à la Parquet/HDFS).

## A tensão que este ticket EXISTE para resolver

**A [ADR-0002](../docs/adr/0002-vertice-triplice-restricao.md) rejeitou explicitamente a
Opção 3, "trade-off por flag"** (*"múltiplos formatos pra suportar = manutenção alta"*), e
decidiu o vértice tríplice como **restrição dura**: *"técnicas multi-pass / memória > O(1) /
look-ahead são descartadas mesmo com ganho"*.

**"Calibrar por situação" é aquela Opção 3.** Este estudo não pode contorná-la por fora: ou
conclui que a restrição dura se mantém, ou **produz o material para uma ADR que a supersede**
o padrão que a ADR-0034 usou com a ADR-0029.

### E o código já se moveu, sem registro (medido 2026-08-20)

Os candidatos V2 são **batch por construção**: `_v2b_encode` e `_struct_split_encode`
recebem a coluna inteira e varrem tudo (2× e 7×) antes de decidir; o gate do split é
`for v in values[1:]`, look-ahead total, que a ADR-0002 lista como **refutado**
(*"Sliding window pattern detect, Buffer > O(1)"*).

As **ADR-0025 e ADR-0026 não mencionam** a ADR-0002. Leitura provável: a restrição
constrangia o **core de coluna** (OBAT/HCC) e o ciclo 0.7 acrescentou uma camada de
**orquestração multi-col** batch, sem que a fronteira fosse redocumentada.

## Sinal do owner (2026-08-20)

> *"o ADR-0002 me parece obsoleto também, mas vamos seguir pro DOC-03 e ver as condições
> novamente dos ADRs depois."*

Registrado: o owner **inclina-se a considerar a ADR-0002 obsoleta**, e pediu uma **revisão
geral das condições dos ADRs** em momento próprio. Isso reforça o P3 abaixo (mapear a
fronteira real) e sugere que a revisão não seja só da 0002, vale varrer o índice inteiro
atrás de ADRs cuja premissa o código já superou (o padrão que apareceu 3× nesta sessão:
0029→0034 no default do header, 0031→0033 no `H`, e agora 0002 vs os candidatos V2).

**Não** é decisão tomada, é sinal registrado para não se perder.

## O que estudar

| # | pergunta | por quê |
|---|---|---|
| **P1** | Qual a assimetria encode/decode **medida hoje**? (o encode paga `min()` de 4 candidatos; o decode fatia por size) | é a tese central do perfil de transmissão. **MEDIDA em 2026-09-01**, ver a nota abaixo: de 3,6× a 1.060×, conforme a forma do dado |
| **P2** | O que muda entre "1 encode / 1 decode" e "1 encode / N decodes"? | decide se encode caro se paga |
| **P3** | A fronteira da ADR-0002 hoje: **onde** o single-pass ainda vale e onde já não vale? | precede qualquer supersede |
| **P4** | Perfis de *emissão* (um formato, esforço variável) resolvem sem virar `L0..L9`? | preserva a decisão da ADR-0002 |
| **P5** | O que o Parquet/HDFS resolve que o `.tcfx` sidecar precisaria resolver? | já triado em `T-REL-08:113` como `.9`/2.0 |

## Atualizado 2026-09-01 (0.8.4): o P1 foi medido, e o eixo de cenário ganhou uma direção

### P1, medido

Encode contra decode, melhor de sete, no código da 0.8.4 sem otimização:

| dado | encode | decode | razão |
|---|---:|---:|---:|
| categórico de baixa cardinalidade, 2.000 linhas | 55,0 ms | 13,3 ms | 4,1× |
| IDs zero-padded, 5.000 linhas | 135,4 ms | 37,2 ms | 3,6× |
| tabela mista, 2.000 linhas | 142,9 ms | 16,5 ms | 8,7× |
| adult-census real, 3.000 × 15 | 366 ms | 18,1 ms | **20,3×** |
| texto livre repetitivo, 2.000 linhas | 5.914 ms | 5,6 ms | **1.060×** |

Em vazão, no caso real: **8.194 linhas/s** encodando contra **165.947 linhas/s** decodificando.

A tese do perfil de transmissão se sustenta, e a razão **não é constante**: ela varia duas
ordens de grandeza com a forma do dado, então "a assimetria do TCF" é uma faixa, não um número.
Quem calibrar por situação precisa medir a situação.

### A direção que faltava no cenário 1

O contexto acima descreve **um** sentido: muitos clients comprimindo, um servidor central
descomprimindo. O owner acrescentou o inverso (2026-09-01), e ele tem veredito diferente:

| topologia | quem paga o encode | quem paga o decode | leitura |
|---|---|---|---|
| **A. cliente encoda, servidor consome** (upload, telemetria, sync) | cada cliente, 1×, em CPU ociosa | o servidor, N× | o caro é **distribuído e paralelo por construção**, o barato é o concentrado. É o melhor caso, e é o que a assimetria foi desenhada para servir |
| **B1. servidor encoda o MESMO payload para N clientes** (catálogo, feed, config) | o servidor, 1× | cada cliente, 1× | o encode **amortiza sobre N**, e melhora quanto maior o N. Cada cliente ainda economiza banda e parsing |
| **B2. servidor encoda payload ÚNICO por requisição** (resposta personalizada) | o servidor, a cada requisição | um cliente, 1× | é **1:1**, e os 366 ms entram no caminho da requisição. Só paga se a rede for o gargalo, ou seja abaixo do break-even de 1,2 a 36 Mbps |
| **C. disco e armazenamento** | 1× na escrita | N× nas leituras | topologicamente igual ao B1, mas o **concorrente muda**: Parquet e ORC são colunares **com índice**, e ganham em acesso aleatório e predicate pushdown. Não medido: é o P5 |

**A distinção que decide não é "cliente ou servidor", é cacheável ou personalizado.** O B1 e o
B2 estão do mesmo lado do fio e em lados opostos da conta, e agrupá-los como "o servidor
enviando" esconde exatamente a variável que importa.

### O que isto NÃO autoriza

O TCF **não é ETL**, e medir em massa serve para ter noção de ordem de grandeza, não para
decidir. Os números de volume que existem (o `lineitem` de 60k em 475 s, as 500 mil linhas que
não terminam) descrevem uma **borda**, não o alvo. Usá-los como veredito geral seria tão errado
quanto usar o caso favorável.

E nada disso mexe na [ADR-0002](../docs/adr/0002-vertice-triplice-restricao.md): continuam
sendo material para uma decisão, não a decisão.

## O que este ticket NÃO é

- **Não é** proposta de flags `L0..L9`. Se o estudo levar lá, exige ADR de supersede.
- **Não** duplica `T-REL-08:113` (adapter/sidecar/chunking/index-on-arrival, já triados):
  este cobre o eixo **transmissão assimétrica**, que aquele não cobre.
- **Não** toca `src/tcf`.

## Ordem sugerida (e uma discordância registrada)

O owner sugeriu: *"depois de otimizar bem os algoritmos, conseguimos medir melhor as
situações"*. **Registro a discordância**: o perfil de uso decide **quais** otimizações valem,
não o contrário, e o `bn-dict-perspectivas` já estabeleceu o padrão ao mandar *"medir a
latência ANTES de cravar formato"*.

Proposta: **P1 e P3 primeiro** (baratos, e P1 usa o bench que já existe). São eles que dizem
se P2/P4/P5 valem o esforço. Decisão de ordem é do owner.

## P6 (novo, 2026-08-25): a CONSULTA é um quarto eixo, e ela conflita com os outros

Direção do owner:

> *"o TCF trabalha em modos, logo ele tem modos de velocidade, memória, latência,
> compressão, e também pode ter para agrupamento. São intenções, é claro, e não tem uma
> chave definitiva que exclua tudo. Com o cobertor curto, se uma opção sacrificar outra,
> pode ser que basta a gente criar uma chave [...] A busca é sempre um win-win total, mas
> infelizmente pode não ocorrer."*

A ADR-0002 fixou três vértices (compressão, memória, latência) e rejeitou a opção
"trade-off por flag". Mas ela é de 2026-05-17 e trata do **encode**: a latência ali é a de
quem escreve o wire. A camada de **consulta** não existia, e ela tem um custo próprio que
o encoder decide sem saber.

### O que foi medido (2026-08-25)

O encoder escolhe o modo de cada coluna pelo **menor wire**, um critério só. Mas o modo
escolhido também decide o custo de consultar aquela coluna, e os dois perfis não são
graus da mesma coisa:

| controle (n=2000) | modo | bytes | posições visitadas | valores construídos |
|---|---|---:|---:|---:|
| k2-curto | `@dict` | 3258 | 2000 | **2** |
| | core | 7250 | **0** | 2000 |
| k50-curto | `@dict` | 3264 | 2000 | **50** |
| | core | 8710 | **0** | 2000 |
| k1000-curto | `@dict` | 5285 | 2000 | **1000** |
| | core | 6175 | **0** | 2000 |

O `@dict` constrói K valores e **varre N posições**; o core não varre nada e constrói os N
valores. Conforme K se aproxima de N, o dicionário perde a vantagem de memória e continua
pagando a varredura.

Lab: `experiments/lab/dirty/2026-08/2026-08-25/2026-08-25-0200-cobertor-curto/`.

### O que isso sugere, e o que ainda não foi medido

Nos nove controles testados, quando o dicionário vence ele vence **folgado** (14% a 62% de
bytes), então **não se achou ainda o caso de conflito real**: o encoder não está
economizando 1% de bytes e cobrando 60x na consulta. O cobertor pode não estar tão curto
quanto se temia.

O que falta medir antes de propor qualquer chave:

- [ ] **Existe a zona de empate?** Uma coluna em que `@dict` e core ficam a menos de 5% de
      distância em bytes, e os perfis de consulta divergem muito. Se ela não existir em dado
      realista, não há chave a criar.
- [ ] **O custo de varrer N posições em Python vs construir N valores**, em unidade
      comparável. Hoje só se sabe que são coisas diferentes, não qual dói mais e a partir
      de que n.
- [ ] **`sort_by` é o caso já conhecido de conflito** (habilita `group_ranges`/`agg_by`,
      reordena as linhas, muda os bytes). Ele é o precedente: uma chave que declara
      intenção, com custo assumido e documentado.

**Atualizado 2026-09-01 (0.8.4)**: as três afirmações entre parênteses no item do `sort_by`
caíram. A [ADR-0050](../docs/adr/0050-sort-by-vira-candidato-o-floor-decide.md) transformou o
kwarg em **candidato**: o encoder monta as duas versões, a ordenada e a de entrada, e emite a
menor. Ele não promete mais ordenar.

Medido em 0.8.4 com 60 linhas, chave `k0..k5` cíclica e seis companheiras sequenciais
(`str(1000 + i + c * 100)`), o FLOOR recusa a ordenação:

| tabela (60 linhas) | sem `sort_by` | com `sort_by` | o que o encoder fez |
|---|---:|---:|---|
| 6 companheiras independentes da chave | 295 B | 295 B | recusou; wire byte-idêntico |
| 3 companheiras função da chave | 355 B | 127 B | ordenou; −64,2% |

Na primeira linha da tabela o `decode` devolve a chave na ordem de entrada
(`k0, k1, k2, k3, k4, k5, k0, k1, ...`), o `group_ranges('chave')` levanta `ValueError`, e o
`agg_by('chave')` responde `{'k0': 10, ...}`, o mesmo que o `group_count`. Não habilitou o
layout, não reordenou e não mexeu num byte.

O precedente não morreu, mudou de natureza, e a natureza nova serve melhor ao P6. O que o
`sort_by` demonstra hoje é um knob que declara **intenção** e deixa o encoder decidir se ela
paga, porque só o encoder tem as duas versões na mão. É a mesma forma de chave desenhada na
seção seguinte (`encode(..., para="consulta")`), com a vantagem de já mostrar que a decisão
sai barata quando o critério de desempate é o próprio wire.

O conflito real continua de pé, e ficou mais nítido. O `group_ranges` segue estrito, e nenhum
kwarg garante hoje o layout que ele exige: a mensagem de erro nova manda ordenar as linhas na
origem, fora do TCF. O eixo de consulta perdeu a única chave que o atendia, o que **reforça** a
pergunta do P6 em vez de respondê-la.

### Reforco de 2026-08-25: o remapeamento entre colunas depende do modo

Uma medicao nova torna o P6 mais concreto. A hipotese do owner era que, numa consulta
ordenada, so' a coluna ordenada pagaria o preco e as outras poderiam ser "puladas" por
mapeamento logico. Ela se sustenta, mas **so' quando as outras colunas caem em dict ou
denso**:

| modo | acesso a' linha i | medido |
|---|---|---|
| `@dict` | O(1), `offset = i * width` | 5 posicoes de 2000, **0 bytes decodificados** |
| denso | O(1), `offset = i * w bits` | por construcao |
| `raw` | O(i), achar o i-esimo LF | nao medido |
| `core` | **impossivel**, refs resolvidas em sequencia | ler 1 posicao construiu 2000 valores |

Isso liga o P6 a uma consequencia pratica: a escolha de modo do encoder decide se a
consulta ordenada e' barata ou nao, e essa escolha hoje e' feita so' por bytes. Uma tabela
em que 3 colunas caem em dict e 1 em core tem 3 colunas "pulaveis" e uma que obriga a
materializar tudo.

Registrado como `H-QUERY-04f`.

### A pergunta de desenho, para depois da medição

Se a zona de empate existir, a chave não precisa ser um nível global (`L0..L9`, que a
ADR-0002 rejeitou por bons motivos). Pode ser uma **intenção declarada** que só desempata
onde há empate, do tipo `encode(..., para="consulta")`, mantendo o win-win onde ele existe
e escolhendo lado só onde o cobertor é curto de fato.

Isso preserva o espírito da ADR-0002 (nada de sacrificar um vértice por ganho em outro) e
resolve o caso que ela não previu (o vértice de consulta, que só apareceu com o `view`).

## Critérios de aceite

- [ ] P1 medido, com o mesmo rigor dos labs (§RT, evidência em disco, mix declarado)
- [ ] P3 respondido: mapa de onde o single-pass vale hoje
- [ ] Decisão registrada: a ADR-0002 se mantém, ou entra ADR de supersede
- [ ] P6: a zona de empate existe em dado realista? Se não, não há chave a criar
- [ ] Se supersede: a ADR nova cita ADR-0025/0026 e resolve a fronteira core × orquestração
