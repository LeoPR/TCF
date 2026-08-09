# Resultado — o núcleo tem DUAS noções de similaridade, e elas não competem

**2026-08-09 · dirty · sondas estruturais, RT verde em todos os encodes.
Números em [`outputs/sondas.json`](outputs/sondas.json).**

Você pediu pra *olhar a estrutura* do fluxo, não otimizar. A estrutura tem um achado —
e ele é exatamente o que sua descrição antecipou, com um endereço concreto.

---

## Antes: uma correção factual que muda a análise

**Não existe Patricia no core.** O que está soldado é um **hash de trigrama** (ADR-0009):
bucket pelos 3 primeiros chars, depois varredura linear com LCP/LCS dentro do bucket. A
Patricia é a `H-TH-02` (*"índice incremental de padrões, Patricia generalizada"*),
**adiada**.

E nas colunas de data esse índice **não indexa nada**:

| coluna | k | buckets | maior bucket |
|---|---:|---:|---|
| **diário ISO** | 600 | **1** | **600 (100% dos únicos)** |
| **úteis ISO** | 600 | **1** | **600 (100%)** |
| mensal ISO | 600 | 5 | 120 (20%) |
| ordinal-dia | 600 | 19 | 33 (6%) |

Todo `2026-…` cai no bucket `202`. O índice vira uma lista, e o "achar o melhor pedaço"
vira O(n) por string. Isso já tem endereço: a `H-PERF-04` foi adiada com a nota *"hash
tradicional não preserva byte-canonical em datas com prefixo popular; solução precisaria
Patricia trie (out of scope agora)"*. **A sua memória do Patricia é o alvo, não o
soldado** — e a coluna de data é justamente o caso que o motivou.

---

## O achado: igualdade e proximidade não disputam o mesmo `min()`

O núcleo tem duas famílias de similaridade, e você nomeou as duas:

| família | o que captura | mecanismos |
|---|---|---|
| **IGUALDADE** — "peças iguais" | o valor já apareceu | `^N` (HCC), bN de domínio, dict V2-B |
| **PROXIMIDADE** — "próximas como deltas" | o valor é o anterior + d | seq-RLE `*N+d\|`, periódico `*N~…\|` |

**Elas não competem.** A igualdade roda **dentro** do OBAT/HCC, antes; a proximidade lê o
que sobrou. É ordem de pipeline disfarçada de escolha — e o `min()` não salva, porque o
candidato aritmético **nunca chega a ser construído**.

### A medição que isola isso

Coluna `mes` = `01,02,…,12,01,02,…` (600 linhas, ciclo perfeito de período 12):

```
corpo canônico, linhas 1-16:
  \01  \02  \03  \04  \05  \06  \07  \08  \09  \10  \11  \12   ← 12 literais
  ^1   ^2   ^3   ^4  …                                          ← daqui em diante, REFERÊNCIA

deltas que o seq-RLE consegue ler:  [1]×11, depois None, None, None… para sempre
runs periódicos detectados: 0
```

**A leitura aritmética morre na linha k**, exatamente onde a primeira repetição aciona o
dedup:

| coluna | k | 1ª referência `^N` | deltas legíveis | runs | custo |
|---|---:|---:|---:|---:|---:|
| mês `01..12` (cicla) | 12 | **linha 12** | **11** | 0 | **423 B** |
| dia `01..28` (cicla) | 28 | **linha 28** | **27** | 0 | **523 B** |
| mesma aritmética sem repetir | 600 | — nunca | 599 | 0 (uniforme) | **20 B** |
| úteis, ciclo `1,3,1,1,1` | 600 | — nunca | 599 | **1** | **30 B** |

**~20× de diferença**, e a causa não é o dado: é que a repetição fez o HCC escolher
*juntar por igualdade*, e essa escolha **apagou** a estrutura que o periódico comeria com
um marcador. É literalmente o que você descreveu: *"o HCC juntar apenas os pedaços de
árvore que, caso seja data, são melhores montados de outra forma"*.

---

## E isto explica por que os specs funcionam

Vale reformular o papel da semântica, porque a medição sugere uma leitura mais precisa
que "semântica ajuda a comprimir":

> **O spec não adiciona informação. Ele escolhe um domínio onde a aritmética sobrevive
> ao dedup.**

`ordinal-dia` e `mês-época` têm **k = 600 distintos** — nada repete, nada dedupa, e o
seq-RLE enxerga a coluna inteira. É por isso que o mensal foi de 679 → 31 B: não porque o
TCF passou a "entender data", mas porque o alvo devolveu ao core uma coluna onde o
mecanismo de proximidade consegue trabalhar.

O corolário incomoda um pouco: **parte do ganho dos specs é o núcleo compensando uma
escolha própria.** Onde a proximidade competisse de verdade, o spec ganharia menos — e
ganharia por mérito próprio (o domínio compacto), não por desempate.

---

## Os três encaixes que a estrutura sugere

Nenhum deles é mecanismo novo. Todos são *disponibilizar o que já existe*.

### E1 — o split estrutural não está na rota que a data toma

O ADR-0026 (`%`) **já corta `ano|mês|dia`** — é exatamente "os pedaços da data como
pedaços". Mas ele é candidato só do multi-col (`min(tcf, raw, dict, split)`); a rota
single-col flat não o consulta:

| coluna | split | single-col flat (hoje) | multi-col escolheu split? |
|---|---:|---:|---|
| **mensal** | **700 B** | 1085 B | **sim** (`#TCF.8M%dt`) |
| **úteis** | **903 B** | 2454 B | **sim** |
| diário | 820 B | **414 B** | não (e faz bem) |

O mesmo dado, na rota flat, não alcança um candidato que na rota multi-col vence por
35–63%. **É a terceira ocorrência da classe "o candidato existe e a rota não o
consulta"** — as duas anteriores foram o `T-BN-TIPADO` e o FLOOR da nature que não via o
bN. Ticket: `T-SPLIT-SINGLE-COL`.

### E2 — o candidato "sem dedup", para a proximidade competir de verdade

O micro-seletor que você descreveu. Não é escolher macro entre "modo igualdade" e "modo
proximidade": é **materializar o corpo sem referências como mais um candidato do `min()`
que já existe**, e deixar os dois disputarem por bytes, como todo o resto do projeto faz.

Teto medido: a coluna `mes` sairia de 423 B para a ordem de 35 B (o periódico com
`p=12`); a `dia` de 523 B para ordem semelhante. Ticket: `T-CANDIDATO-SEM-DEDUP`.

Ressalva honesta: isso **dobra o trabalho de corpo** no caminho quente, e o FLOOR já é
58% do encode (medido em 2026-08-08). Vizinho direto do `T-GATES-ANTES`.

### E3 — o índice adaptado (o Patricia que você lembrava)

Resolve o bucket degenerado do S1 e é o único dos três que muda *como* os pedaços são
achados, não *quais* candidatos competem. É `H-TH-02` + `H-PERF-04`, ambas adiadas — e a
medição de hoje é evidência nova a favor delas (1 bucket para 100% dos únicos em duas das
três colunas de data testadas).

---

## O que já anda nessa direção

Vale registrar que a estrutura **não** é toda macro. Dois micro-seletores existem:

- **`obat_shape` hint** (ADR-0011): per-string, decide preservar shape ou não — genérico,
  guiado por cadência detectada, sem semântica.
- **FLOOR por fragmento** (ADR-0040, soldado ontem): dentro de um mesmo corpo, cada
  fragmento não-periódico decide sozinho se aceita a compactação.

O segundo é precedente direto do que E2 propõe, em escala menor.

---

## Onde isso fica

Você mesmo disse que é `.9`, e concordo — nada aqui é completude, tudo é otimização. O
que muda com esta sonda é que **as três direções deixam de ser palpite e passam a ter
número**, e uma delas (E1) é da classe barata: candidato existente, rota que não olha.

E fica o ajuste de perspectiva pro estudo de data: o alvo mensal (31 B) segue ganhando de
todos os encaixes acima (700 do split, ~35 do sem-dedup). **Spec e estrutura não são
redundantes** — o spec escolhe o *domínio*, o encaixe escolhe a *segmentação*. São eixos
diferentes, e o `min()` pode ter os dois.
