---
title: ESTRUTURA SEM DADO — levantamento de hipóteses (formas opacas, compressão de estrutura)
type: report
status: aberta
created: 2026-07-16
related:
  - experiments/lab/dirty/notas/p4b-levantamento.md (problema B — contagem irrepresentável)
  - experiments/lab/dirty/notas/contrato-externalizado-e-aceleradores.md (irmão — H-STRUCT-AMORT depende dele)
  - experiments/lab/dirty/2026-07-16-0213-p4a-array-em-array-estudo/ (a medição do framing +7 B/nível)
  - tickets/T-FMT-OMIT-OR-DECLARE.md
  - experiments/lab/dirty/notas/futuras-otimizacoes-formato.md (O-FMT-20 registro-'0')
  - experiments/lab/dirty/notas/tcf-camadas-arquitetura.md (L1/L2/L3)
  - experiments/lab/dirty/notas/roadmap-hipoteses.md (H-STRUCT-DEF/AMORT/META/ASDATA)
---

# Estrutura sem dado — levantamento de hipóteses. Para estudo do owner.

## 0. A colocação do owner (2026-07-16) — [dispositivo→registro]

Sobre o gate de 8 formas do P4b: *"podemos testar e alguns podemos pensar em fazer simplesmente
DEFINIÇÕES pois são formatos opacos e que não têm relação com o dado em si, mas com a estrutura.
A gente não pensou no TCF fazendo compressão real de ESTRUTURA: ele simplifica a estrutura e
comprime o DADO. Mas se não tem nem dado na estrutura, a estrutura é otimizada como? Temos que
criar um lab disso também."*

Este doc é o levantamento de hipóteses pedido. Lab ainda **não criado** (aguarda o estudo).

## 1. Precisão primeiro: onde a "estrutura" vive no wire hoje — [probatório]

"O TCF não comprime estrutura" é meia-verdade. A estrutura vive em **3 lugares** com regimes
diferentes, e o levantamento só é honesto separando-os:

| lugar | regime HOJE | evidência |
|---|---|---|
| **(a) Meta/header** (L2) | texto plano, **NÃO comprimido** | framing medido: **+7 B/nível exato** (lab P4a, `02a-framing-prof{1..6}.tcf`); o header profundo repete literal — `m#:3[#:3[#:3[#:3[#:3[#:3[` |
| **(b) Colunas de controle** (counts/emasks) | **JÁ comprimidas via L1** (RLE/seq-RLE) | wire real: counts `2,1` → `*2-1|\2`; matriz retangular → counts constantes colapsam `*N|` |
| **(c) Representabilidade** (formas sem coluna) | **irrepresentável** — não há onde pendurar contagem | P4b: `[{}]`/`[{},{}]` fail-loud ("nenhuma coluna derivável"); `[]` fail-loud na guarda de lista-vazia; `total` vem de `len(1ª coluna)` |

E uma fronteira importante: **no CAMPO, estrutura vazia JÁ tem representação** — array vazio =
count `\0`; objeto vazio `{}` = marcador `{}` no meta e, quando a presença/null varia entre
registros, mask/msize por registro (o F1 do P3b fechou exatamente esse caso). O buraco real de
representabilidade é **só na RAIZ e no dataset-sem-colunas** — exatamente o problema B do
[p4b-levantamento](p4b-levantamento.md).

## 2. A tese do owner (definições) — análise — [probatório→opinião]

**Concordo com a tese, com uma precisão.** As formas opacas formam um **alfabeto FINITO de
FORMAS** (shapes): `[]` · `{}` · `[{}]…` · `null`-raiz · escalar-raiz. Para um alfabeto finito, o
ato certo é **DEFINIÇÃO** (token de wire fixo, tabela fechada — como o discriminador de 1 char já
faz para codecs), não mecanismo de compressão: não há entropia a remover, há só **nomeação**.

A precisão: o alfabeto é de **formas**, as **contagens continuam numéricas**. `[{},{}]`×1M não se
enumera — se declara: *forma* (dataset-sem-colunas) + *count* (1M). Ou seja, a definição é
`root_kind + count`, nunca literal por instância. Isso conecta as pontas:

- é o **problema B do P4b** (contagem sem coluna portadora) resolvido por declaração;
- é o **O-FMT-20** (registro-'0'/schema-declare) no flat — mesmo problema, trilho armazenamento;
- é a régua do **T-FMT-OMIT-OR-DECLARE**: o resto do wire não deduz a contagem → declaração
  obrigatória.

## 3. Hipóteses (→ [roadmap-hipoteses.md](roadmap-hipoteses.md))

- **[[H-STRUCT-DEF-01]]** — **formas opacas → definições de wire** (tabela fechada `root_kind` +
  count explícito quando não há coluna portadora), não compressão. Interlock: as definições SÃO
  parte do espaço de decisão do P4b (problema A+B) — estudar junto, decidir junto.
- **[[H-STRUCT-AMORT-01]]** — **estrutura repetida em massa amortiza via contrato**: num stream de
  N docs com o MESMO schema, a "compressão de estrutura" mais efetiva é **não transmiti-la N
  vezes** ([[H-CONTRACT-EXTERN-01]]). Medível hoje: bytes de header × N vs 1×. É onde a pergunta
  "estrutura é otimizada como?" tem a resposta de maior alavanca.
- **[[H-STRUCT-META-01]]** (`.9`) — **o próprio meta é comprimível?** A repetição literal
  `#:3[`×6 no framing profundo sugere meta-RLE p/ níveis uniformes. **Trade declarado**: o header
  é a parte human-readable do pilar explicabilidade — comprimi-lo só sob perfil
  ([[H-PROFILE-01]]), nunca default. Medir antes: em que regime o header domina o payload?
- **[[H-STRUCT-ASDATA-01]]** — **estrutura-como-dado**: regime onde a shape É a informação
  (árvores, malhas, matrizes; folhas triviais) e as colunas de CONTROLE dominam os bytes. Elas já
  passam pelo L1 — medir se RLE/seq-RLE basta pros padrões de counts reais (retangular já colapsa)
  ou se counts pedem natureza própria (ex.: fan-out fixo, progressões). É a versão estrutural da
  pergunta que as natures respondem pra valores.

## 4. Proposta de lab (não criado — aguarda estudo)

`YYYY-MM-DD-HHMM-estrutura-sem-dado/`, convenção obrigatória (inputs/intermediates/outputs, `.tcf`
reais, roundtrip diffável):

- **inputs**: (i) alfabeto de formas opacas ENUMERADO (as 8+ do gate P4b); (ii) matrizes
  retangulares e ragged; (iii) árvores profundas com folhas triviais (estrutura-como-dado);
  (iv) N docs mesmo-schema (amortização). Sintético declarado (construído pra testar).
- **medição-chave**: decompor cada wire em **3 buckets** — meta / colunas-de-controle / folhas —
  e reportar a proporção (a pergunta do owner é sobre o regime em que bucket-folhas → 0).
- **gate**: definições RT-exatas pro alfabeto (quando P4b decidir a forma); contra-prova JSON;
  nenhum weld — os resultados alimentam a DECISÃO do P4b, não a antecipam.

## 5. Fronteira

- **Não é P5**: união/polimorfismo continua fora.
- **Não é `.8` por si**: as definições de raiz entram SE e COMO o P4b decidir; a amortização é
  eixo do contrato (`.9`/2.0); H-STRUCT-META e ASDATA são medição/`.9`.
- **Não medido ainda**: proporção meta/controle/folhas em dado real aninhado (não existe no hub —
  [T-SHAPER-NESTED-OUTPUT](../../../../tickets/T-SHAPER-NESTED-OUTPUT.md)).
