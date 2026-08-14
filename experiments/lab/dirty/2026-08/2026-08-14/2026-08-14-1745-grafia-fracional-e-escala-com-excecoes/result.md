# Resultado — onde o float ainda tem folga

7 sintéticos + 8 bordas + 5 colunas reais, 4 mecanismos, **0 falhas** no RT estrito.
Linguagem de dirty lab: isto **orienta**, não fecha.

## O que aconteceu, em uma linha

As duas ideias funcionam e **ganham em regimes diferentes** — a fração onde há dízimas
distintas, a escala-com-exceções onde há sujeira rara. Mas a varredura do corpus mostrou que
o regime da fração tem **amostra n=1 no mundo real que temos**, e o levantamento do núcleo
mostrou que o mecanismo de exceção que eu ia propor **já está soldado**.

## Os números

### Sintéticos — casos particulares com par de contra-prova

| caso | hoje | M1 fração | M2 escala | M3 exc | M3b exc-`_` | FLOOR |
|---|---|---|---|---|---|---|
| `owner-sujo-no-meio` | 53 | 52 (1/10) | **79** | **51** | 52 | M3 −2 |
| `owner-sem-o-sujo` | 37 | — | 35 | 35 | 35 | M2 −2 |
| `dizima-uniforme` | 29 | **26** (10/10) | 32 | 32 | 32 | M1 −3 |
| `dizima-variada` | 160 | **94** (10/10) | 145 | 145 | 145 | M1 **−66** |
| `rateio-terco` | 48 | **36** (6/6) | 51 | 51 | 51 | M1 −12 |
| `money-2casas` | 114 | — | 111 | **107** (8/20) | 111 | M3 −7 |
| `money-com-terco` | 124 | 124 (1/20) | **188** | **118** (9/20) | 127 | M3 −6 |

### Reais

| coluna | hoje | M1 | M2 | M3 | M3b | FLOOR |
|---|---|---|---|---|---|---|
| `wine.alcohol` | 2881 | 2853 (9/2000) | **recusa** | **2772** (14) | 2783 (14) | M3 −109 |
| `wine.density` | 10137 | — (0/2000) | 9757 | 9757 | 9757 | M2 −380 |
| `retail.UnitPrice` | 3662 | — | 3378 | 3378 | 3378 | M2 −284 |
| `tpch.l_discount` | 1406 | — | 1389 | 1389 | 1389 | M2 −17 |
| `tpch.l_extendedprice` | 17018 | — | **15591** | 15591 | 15591 | M2 −1427 |

## 1. A escala pura falha de **duas** maneiras, não de uma

Eu só tinha articulado a primeira:

| modo | o que acontece | onde se vê |
|---|---|---|
| **1 — recusa** | nenhum k serve a todos; a coluna perde o candidato inteiro | `wine.alcohol` |
| **2 — pior que nada** | um k serve, mas é **enorme**; o candidato existe e **infla** | `owner-sujo` 79 vs 53; `money-com-terco` **188 vs 124** |

O modo 2 é o mais insidioso porque não aparece como falha: o mecanismo "funciona", devolve um
candidato válido, e o FLOOR só não o usa porque é pior. Um valor sujo em 20 força k=12 e
multiplica **toda** a coluna por 10¹².

**A escala com exceções resolve os dois** — em `wine.alcohol`, onde a escala pura recusa, ela
escala em k=1 com **14 exceções em 2000** e tira 109 B (−3,8%).

## 2. A grafia fracional funciona — e o corpus quase não tem onde usá-la

O mecanismo é sólido: **126/126** dízimas fecham byte a byte, e a verificação por re-emissão
**se protege sozinha** (`2.718281828`, `0.30000000000000004` e `12.3456789` são recusados —
o achador propõe, a re-emissão veta).

E o par de contra-prova fez o serviço dele: em `dizima-uniforme` o ganho é **3 B**, porque o
RLE de linha idêntica já resolvia; em `dizima-variada`, onde o núcleo não tem repetição para
comer, são **66 B (−41%)**. Ou seja, **o ganho não é da grafia curta — é de haver dízimas
distintas**. É a mesma lição da hora, e desta vez ela estava embutida no desenho.

No dado real, porém: **9 conversões em 2000** numa coluna, e **zero** nas outras quatro.

## 3. Por que — a varredura do corpus (9 bancos, 186 colunas, 31 float)

> `wine.alcohol` é a **única** coluna R1 (uniforme-com-sujos) **e** a única R2 (dízima) do
> corpus inteiro. Nas outras 30 colunas float, valores com ≥10 casas: **zero**.

E há mais, tudo verificado na coluna inteira (não na amostra):

- **A patologia é uma só, vista por dois testes.** Os 40 sujos do R1 e as 40 dízimas do R2
  são **o mesmo conjunto**. Multiplicados por 3 dão sempre um número de 1 casa → são
  **médias/divisões por 3** exportadas com `%.15g`; a forma exata é **n/30**.
- **O caso do owner existe no real, em outra escala**: não é `0.2, 0.4` com `0.333333333`, é
  `9.4, 9.8` com `10.0333333333333`. O histograma é bimodal com buraco limpo — 6413 valores
  em 1 casa, 44 em 2, **nada entre 3 e 12**, e 40 em 13–14.
- **Zero notação científica** no corpus inteiro; **zero artefato binário** (nenhum
  `0.30000000000000004` em lugar nenhum). Fora de `alcohol`, o máximo de casas de qualquer
  coluna é 6. Os únicos decimais longos do corpus real são as 40 dízimas legítimas.
- **`beijing-pm25.db` tem 0 bytes** — arquivo vazio. É um buraco do corpus, não erro de leitura.
- **Identificador que virou float**: `online_retail.CustomerID`, 406.829 valores, 100%
  inteiros, declarado `REAL` — paga um `.0` por valor em qualquer serialização via `str`.
  Idem `l_quantity`. E um regime **semi-inteiro**: `free_sulfur_dioxide` é 99,11% inteira, com
  o resíduo todo em `.5`.
- **O teste de "money" por casas decimais é quebrado**: `str()` suprime o zero final dos
  centavos (`45523.10` → `"45523.1"`), então "exatamente 2 casas" trava perto de 0,90 por
  construção e **nenhuma** coluna de dinheiro do corpus passaria de 95%. O invariante real é
  **"é múltiplo exato de 0,01"**.

**Consequência para a fila**: qualquer spec calibrado em R1/R2 está apoiado em **uma coluna
de um dataset**. Não é base para decidir.

## 4. O achado que mais muda o desenho: o núcleo já faz isto

Eu ia propor um mecanismo de exceção. **Ele já está soldado**, e é o mesmo do ALP:

- `MARKER_LITERAL = '_'` (`natures/templated_checked.py:38`), usado idêntico pelas **quatro**
  natures — desambiguado por **exclusão de alfabeto** (o `_` sai do BASE94 e os payloads são
  digit-only), não por escape.
- `int_pad.py:73-74` — `length_wrong`: **o valor que não cabe na largura da coluna vira
  literal sozinho, sem alargar nem recusar a coluna.** É literalmente o patching do ALP.
- E `int_pad.py:75-78` já faz **canonicidade por re-emissão** (`'007' != '7'`) — a mesma
  disciplina que este lab teve de descobrir sozinho para a escala.

A arquitetura **já absorve exceções**: o `encode_value` decide por valor, os literais entram
no corpo misturados, e o FLOOR decide a coluna por bytes totais. O que falta não é mecanismo
— é a **grafia econômica** da exceção.

Medido: o `_` custa **11 B** em 14 exceções (`wine.alcohol` 2772 → 2783). Barato, e vem com
RT byte-exato e telemetria já prontos.

## 5. Os três defeitos que o próprio lab pegou

Todos meus, todos da mesma família — **um mecanismo que não verifica engana**:

1. **A escala testada com tolerância** (`< 1e-9`) aceita `0.30000000000000004` em k=1 e
   devolve `0.3`. Um "lossless" que perde, calado. → verificar por re-emissão (`Decimal`).
2. **A tag-união `int|float` quebra a escala**: escalar apaga o tipo (`1` → `1000000000000`
   → volta `1.0`), e se o int virar exceção, a grafia literal `1` fica **idêntica** à de um
   escalado. → a escala recusa coluna de tipo misto. É a peculiaridade #1 do fechamento do
   float, cobrando.
3. **Sem guarda de maioria, `k=0` "vence"** em `wine.alcohol` marcando 1716 de 2000 como
   exceção — mas em k=0 **não há escala nenhuma**, e quem decide os bytes ali é o bN de
   domínio (`#TCF.8B77d0`, 111 distintos). Um mecanismo que ganha por não fazer o que promete
   está medindo outra coisa. → exceções têm de ser minoria.

## 6. O loss (M4) — **gateado**, só medido

Contrato **exato-no-agregado**, não RT. Nada aqui é proposta.

| coluna | d | bytes | soma exata? | drift do ingênuo |
|---|---|---|---|---|
| `wine.density` | 2 | 10137 → **708** (−93,0%) | sim | **+48 passos** |
| `retail.UnitPrice` | 1 | 3662 → 2979 (−18,7%) | sim | −12 passos |
| `rateio-terco` | 2 | 48 → 28 (−41,7%) | sim | 0 |

O maior resto preserva a soma exata em todos; o round ingênuo drifta. **O preço, que o PoC de
junho não declarou**: o maior resto erra até **1 passo** por linha, o ingênuo até **0,5** —
preservar a soma custa erro por-linha.

E uma ressalva sobre o PoC de junho, verificada hoje: ele **reportou bytes sem RT validado**
(importou `decode` e nunca chamou), o que viola o §RT do projeto; e seus números
*single-column* estão obsoletos em 2,5×–13× porque a rota single-col melhorou desde então. Os
números desta tabela têm a checagem que faltava — os valores já arredondados atravessam
encode/decode idênticos.

## O que isto orienta (não fecha)

1. **A escala com exceções tem mérito estrutural**, e o caminho é reusar o `_` do core, não
   inventar grafia. Ganho medido é modesto (−3,8% na coluna que a motivou); o valor é a
   coluna **deixar de perder o candidato**, e o modo 2 deixar de existir.
2. **A grafia fracional é sólida e quase não tem onde morar** neste corpus (n=1). Fica
   registrada com o mecanismo provado; decidir por ela pede corpus com rateio/divisão — o que
   o próprio owner descreveu como origem (parcelamento).
3. **A guarda da maioria e a verificação por re-emissão são pré-requisitos**, não detalhes:
   sem elas os dois mecanismos mentem.
4. **Antes de expandir, vale medir onde o corpus é magro**: `beijing-pm25.db` vazio, e float
   real só em 2 dos 9 bancos (o resto é TPC-H sintético, contado em dobro).
