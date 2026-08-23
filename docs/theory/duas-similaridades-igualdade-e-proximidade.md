# As duas similaridades do núcleo: igualdade e proximidade

**Data**: 2026-08-09
**Tipo**: nota teórica transversal (estrutural; vale para qualquer coluna, não só data)
**Origem**: pergunta do owner ao revisar o `data-mensal`, *"o tcf é baseado em quebrar
similaridades e depois fazer os encaixes (…) se elas forem realmente similares, ou
próximas como deltas, também poderiam gerar nós (…) em parte temos um algoritmo cego no
núcleo que pega os pedaços sem julgar a semântica, só olha string (…) essa é uma
oportunidade de apenas olhar a estrutura pra ver se tem algum encaixe melhor nesse fluxo"*
**Evidência**: lab [`2026-08-09-1943-fluxo-igualdade-x-proximidade`](../../experiments/lab/dirty/2026-08/2026-08-09/2026-08-09-1943-fluxo-igualdade-x-proximidade/result.md)
**Conecta com**: [`comparacao-modular-camadas.md`](comparacao-modular-camadas.md) ·
[`2026-05-11-comparacoes-nao-literais.md`](2026-05-11-comparacoes-nao-literais.md)
(delta/aproximação, a intuição original) ·
[`patricia-trie-exploration.md`](patricia-trie-exploration.md) (H-TH-02) ·
[`tipos-o-caminho-do-dado-ate-o-tcf.md`](tipos-o-caminho-do-dado-ate-o-tcf.md)
**Status**: análise estrutural registrada. **Não acionável sem decisão do owner**, todo
o conteúdo é `.9` (otimização), não `.8` (completude).

---

## 1. A tese em uma frase

O núcleo do TCF captura **duas** noções de similaridade, mas só uma delas chega a ser
candidata: a outra é apagada antes de existir.

| | o que captura | mecanismos | quando ganha |
|---|---|---|---|
| **IGUALDADE** | "este valor já apareceu" | `^N` (HCC), bN de domínio, dict V2-B | cardinalidade baixa |
| **PROXIMIDADE** | "este valor é o anterior + d" | seq-RLE `*N+d\|`, periódico `*N~…\|` (ADR-0040), multi-delta (ADR-0016) | cadência, qualquer cardinalidade |

O projeto inteiro é construído sobre `min()`, candidatos competem, nunca substituem. Mas
essas duas famílias **não competem**: a igualdade roda *dentro* do OBAT/HCC, e a
proximidade lê o corpo que sobrou. É ordem de pipeline, não escolha.

## 2. A evidência

Coluna com ciclo perfeito de período 12 (`01,02,…,12,01,…`, 600 linhas):

```
corpo canônico:
  \01 \02 \03 \04 \05 \06 \07 \08 \09 \10 \11 \12    ← 12 literais
  ^1  ^2  ^3  ^4  …                                   ← da 13ª em diante, REFERÊNCIA

deltas que o seq-RLE consegue ler:  [1] × 11, depois None para sempre
runs periódicos detectados: 0
```

**A leitura aritmética morre na linha `k`**: exatamente onde a primeira repetição aciona
o dedup:

| coluna | k | 1ª `^N` | deltas legíveis | runs | bytes |
|---|---:|---:|---:|---:|---:|
| mês `01..12` (cicla) | 12 | linha 12 | 11 | 0 | **423** |
| dia `01..28` (cicla) | 28 | linha 28 | 27 | 0 | **523** |
| mesma aritmética sem repetir | 600 | n/a | 599 | 0 (uniforme) | **20** |
| úteis, ciclo `1,3,1,1,1` | 600 | n/a | 599 | 1 | **30** |

~20× de diferença. A causa não é o dado, é que a repetição fez o HCC juntar por
igualdade, e essa escolha apagou a estrutura que o periódico resolveria com **um
marcador**.

## 3. O que isso diz sobre os specs

Vale reformular o papel da semântica, porque a leitura usual ("semântica ajuda a
comprimir") não explica os números:

> **O spec não adiciona informação. Ele escolhe um domínio onde a aritmética sobrevive ao
> dedup.**

`ordinal-dia` e `mês-época` produzem **k = 600 distintos**: nada repete, nada dedupa, e o
seq-RLE enxerga a coluna inteira. Foi por isso que o mensal caiu de 679 → 31 B: não porque
o TCF passou a "entender data", mas porque o alvo devolveu ao núcleo uma coluna onde o
mecanismo de proximidade consegue trabalhar.

**Corolário desconfortável**: parte do ganho dos specs é o núcleo compensando uma escolha
própria. Se a proximidade competisse de verdade, o spec ganharia *menos*, e ganharia por
mérito (o domínio compacto), não por desempate.

**Corolário útil**: spec e estrutura **não são redundantes**. O spec escolhe o *domínio*;
o encaixe estrutural escolhe a *segmentação*. São eixos ortogonais, e o `min()` cabe os
dois.

## 4. Uma correção de premissa

**Não existe Patricia no núcleo.** O soldado é um **hash de trigrama** (ADR-0009): bucket
pelos 3 primeiros chars, varredura linear com LCP/LCS dentro do bucket. Em coluna de data
ISO ele degenera:

| coluna | k | buckets | maior bucket |
|---|---:|---:|---|
| diário ISO | 600 | **1** | **600 (100%)** |
| úteis ISO | 600 | **1** | **600 (100%)** |
| mensal ISO | 600 | 5 | 120 (20%) |
| ordinal-dia | 600 | 19 | 33 (6%) |

Todo `2026-…` cai em `202`: o índice vira lista e "achar o melhor pedaço" volta a ser O(n)
por string. A `H-PERF-04` foi adiada com a nota *"hash tradicional não preserva
byte-canonical em datas com prefixo popular; solução precisaria Patricia trie"*, e o
estudo de viabilidade existe ([`patricia-trie-exploration.md`](patricia-trie-exploration.md),
H-TH-02, registrada como candidata v2.0 em ADR-0018).

## 5. O espaço de decisão

Três encaixes. **Nenhum é mecanismo novo**: todos são disponibilizar o que já existe.

### E1 · `T-SPLIT-SINGLE-COL`: o split não está na rota que a data toma

O ADR-0026 (marcador `%`) já corta `ano|mês|dia`. É exatamente "os pedaços da data como
pedaços". Mas é candidato só do multi-col; a rota single-col flat não o consulta.

| coluna | split | flat hoje | multi-col escolheu? |
|---|---:|---:|---|
| mensal | **700** | 1085 | sim (`#TCF.8M%dt`) |
| úteis | **903** | 2454 | sim |
| diário | 820 | **414** | não (correto) |

- **Custo**: um candidato a mais no `min()` da rota flat.
- **Risco**: baixo, o mecanismo é soldado e testado; o FLOOR protege.
- **Classe**: **terceira ocorrência** de *"o candidato existe e a rota não o consulta"*
  (antes: `T-BN-TIPADO`; FLOOR da nature que não via o bN). Isso já é padrão, não acidente.

### E2 · `T-CANDIDATO-SEM-DEDUP`: fazer a proximidade competir

O micro-seletor que a pergunta original descreve. **Não** é um modo macro
("igualdade" × "proximidade"): é materializar o corpo *sem referências* como mais um
candidato do `min()` que já existe, e deixar os dois disputarem por bytes.

- **Teto medido**: mês 423 → ordem de 35 B; dia 523 → ordem semelhante.
- **Custo**: dobra o trabalho de corpo no caminho quente, e o FLOOR já é **58% do
  encode** (medido 2026-08-08). Vizinho direto do `T-GATES-ANTES`.
- **Precedente**: o FLOOR por fragmento do ADR-0040 (soldado 2026-08-09) já é um
  micro-seletor dentro de um mesmo corpo, em escala menor.

### E3 · `H-TH-02` / `H-PERF-04`: o índice adaptado

Único dos três que muda **como** os pedaços são achados, não **quais** candidatos
competem. A medição do §4 é evidência nova a favor de reabrir.

- **Custo**: alto (toca o motor de busca do OBAT, sob o GATE byte-canonical).
- **Retorno**: CPU no caso degenerado + possivelmente segmentação melhor.
- **Registro atual**: v2.0 (ADR-0018), não pré-1.0.

## 6. As perguntas que ficam para o owner

1. **E1 entra?** É a mais barata das três e da classe que o projeto já corrigiu duas
   vezes. A pergunta real: vale abrir mais um candidato no `min()` da rota flat, sabendo
   que cada candidato custa CPU no caminho quente?
2. **E2 é `.9` ou é estrutural?** Ele muda *o que o formato consegue expressar* em
   colunas cíclicas, o que soa como completude. Mas o mecanismo (periódico) já existe e
   já é expressável; o que falta é o candidato ser construído. Pela régua do projeto isso
   é otimização. **A classificação é sua.**
3. **A ordem igualdade→proximidade deve continuar implícita?** Hoje ela é consequência de
   onde cada mecanismo mora, não de uma decisão registrada. Se ficar, vale um ADR
   dizendo *por quê*, hoje não há.
4. **O corolário do §3 muda a prioridade dos specs?** Se parte do ganho vem de compensar
   o dedup, o `T-SPEC-PARSE-X-ALVO` e o `T-DATA-ALVO-MENSAL` continuam valendo o mesmo?
   (A resposta provavelmente é sim, 31 B ainda ganha de 700 e de ~35, mas o *motivo*
   muda, e o motivo é o que orienta os próximos tipos.)

## 7. O que **não** está em questão

- Nada disso é `.8`. O ciclo de completude não depende de nenhum dos três.
- Nenhum é pré-requisito do `T-DATA-ALVO-MENSAL` nem do `T-SPEC-PARSE-X-ALVO`.
- O `min()` como arquitetura de decisão **não** está sendo questionado: pelo contrário,
  o achado é que um candidato não chega até ele.
