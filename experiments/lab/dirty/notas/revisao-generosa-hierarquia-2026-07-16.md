---
title: REVISÃO GENEROSA DA HIERARQUIA — parecer S0-S3, fluxo de expansões, matriz por regime
type: report
status: aberta
created: 2026-07-16
related:
  - tickets/T-STUDY-DATASETH-COMPLETE-SEMANTICS.md
  - tickets/T-STUDY-HIERARCHY-LINK-ALGEBRA.md
  - tickets/T-EXP-DATASETH-S0-S3.md
  - experiments/lab/dirty/2026-07-16-1708-dataseth-s0-s3-semantica-vinculos/
  - tickets/T-CODE-TCF8H-JSON-PARITY.md
  - experiments/lab/dirty/notas/contrato-externalizado-e-aceleradores.md
  - experiments/lab/dirty/notas/estrutura-sem-dado-levantamento.md
  - experiments/lab/dirty/notas/tcf-camadas-arquitetura.md
---

# Revisão generosa da hierarquia — 2026-07-16

**[probatório→opinião]** Revisão pedida pelo owner: (1) parecer sobre o S0-S3; (2) re-traçar o
FLUXO contra o princípio "não sobrecarregar o núcleo com sequências especiais, nem demorar
preparando entrada com coisas obviamente repetidas — mesmo repetidas em vazio"; (3) o que está bem
fechado por regime (níveis comuns/pequenos → telemetria/transmissão); (4) o que o novo (S0-S3 +
contrato/aceleradores) revisa nas estratégias iniciais. Fatos abaixo verificados por 4 leitores
com execução (workflow `wf_48acc0fe`); wires e medidas citados foram rodados de verdade.

## 1. Parecer sobre o S0-S3 — está OK, e não é desvio

**Veredito: aprovar como está.** O lab `2026-07-16-1708` cumpre a convenção inteira (pastas por
estágio, 20 `.tcf`, roundtrip **byte-idêntico** confirmado por `cmp` externo, `assert` no run,
determinístico — md5 idêntico em re-execução, 0.36s), **zero** import/alteração de `src/tcf`, e o
oráculo usa magic próprio `#PROTO.DATASETH.S1` declarado no README (não se confunde com `.8H`).
Os 3 tickets usam `confirmada-conceitual` (não empírica) com viés sintético declarado — o rótulo
certo. Duas ressalvas cosméticas: os 7 arquivos da raiz do lab estão CRLF no working tree (o
`.gitattributes` normaliza no commit) e os tickets não repetem a distinção do magic (1 linha
adicionada no T-EXP).

**Sobre "não quero desviar do projeto demais": o S0-S7 não é desvio — é a formalização do que o
projeto já decidiu.** Três convergências verificadas:

1. **O problema que o S3 isolou é a razão da decisão já welded.** A contraprova
   (`first-child` sem skip: `[0,2,2]` e `[0,1,1]` → mesmos bits; pai vazio some) é exatamente o
   que counts+masks resolvem: no caso `18-empty-parent-gap`, `counts=[1,3,1,1,1,0,1,2]` carrega o
   `0` do pai vazio; a emask carrega o pai null. O `.8H` welded usa **counts por nível + máscaras**
   — um dos 4 portadores válidos da sua álgebra, e um que preserva a fronteira que o S3 provou ser
   perdível. O experimento independente **sobe a confiança** da decisão do Ciclo 4.
2. **IR lógico → planos físicos = L2/L3 + perfil.** A separação do programa (semântica fechada
   antes da forma física, forma decidida por medição) é a mesma de `tcf-camadas-arquitetura`
   (L2 relacionamento / L3 otimização) e de [[H-PROFILE-01]] (default por medição em massa).
3. **Mega-tabela**: o trace confirma seu argumento — o codec hierárquico é **cliente** do
   `encode()` por coluna; a hierarquia inteira vive em header + colunas de controle. Capacidade
   nunca foi o problema; a disputa é só a forma da ENTRADA. É o S4.

## 2. O fluxo re-traçado — onde a hierarquia expande hoje (medido)

### 2.1 O que JÁ obedece o princípio (não expandir o óbvio)

| ponto | evidência |
|---|---|
| campo sempre-presente e nunca-null: **nenhuma coluna de mask** | `masked = optional or has_null` (`hierarchical.py:215`); `_leaves` só emite mask se masked (`:275-276`). Telemetria 200 regs: zero mask no wire |
| **corpo DENSO** — "repetição de vazios" NÃO existe no body | ausente/null dão `continue` antes das colunas de dado (`:330-331`, `:336-337`). Campo presente em 1 de 50 regs → coluna de dado `len=1`; a ausência vive só na mask (`*7|-\n.\n*42|^1` = 14 B) |
| counts uniformes colapsam no wire | 200 regs fan-out 3 → `*200|\3` = **8 B** |

Ou seja: no eixo BYTES, o desenho já é "denso + controles que colapsam". A preocupação se aplica
a dois pontos específicos, abaixo.

### 2.2 Onde o princípio é violado — 3 achados, por eixo

**(a) PREPARAÇÃO (CPU/memória, não bytes) — o L1 re-detecta o que o emit já sabia.** Counts, mask
e emask são materializados 1-por-instância em listas Python (`:355`, `:330/336/339`, `:357-363`)
mesmo quando uniformes — 200 strings `"3"` idênticas que o L1 então re-descobre como run. E a
derivação de schema faz ≥2 passadas com 4 pontos de cópia O(N) (`:202, :227, :242, :249`) +
scan completo por coluna pra 1 tag (`:140-150`). É exatamente o seu "demorar preparando a entrada
com coisas obviamente repetidas". **Não muda 1 byte de wire** → `.9` puro
([[H-HIER-PREP-RUNS-01]]: emitir runs direto do emit, fundir derive+emit).

**(b) BYTES — a emask densa é a "repetição de vazios" que sobrou (achado MATERIAL).**
`elem_null` é flag **GLOBAL por campo** (`:241`): **um único null em um array liga emask
O(total-elementos) pro dataset inteiro**. E null periódico não-adjacente não colapsa (RLE é
adjacente): medido, 50 regs com `v=[1.5,None,3.5]` → emask **449 B > 307 B da própria coluna de
dados**. Candidatas (S4, não weld): emask por-instância, emask esparsa (índices dos nulls — o
trade máscara×índice do Ciclo 4 reaparecendo em elemento), ou tratamento L1 de padrão periódico.
→ [[H-HIER-EMASK-SPARSE-01]].

**(c) BYTES — folha periódica não colapsa; o fan-out FIXO esconde colunaridade.** Telemetria
200×`{'t':i,'v':[1.5,2.5,3.5]}`: counts e `t` colapsam lindamente (8 B + 31 B), mas as folhas de
`v` viram `^1^2^3` linha a linha = **1804 B = 96,5% do wire** (seq-RLE só pega adjacentes; TCF
ainda fica 66% menor que JSON, mas o headroom é óbvio). A leitura certa do seu argumento da
mega-tabela: `v` com fan-out fixo 3 **é** 3 colunas irmãs disfarçadas — desaninhado, seriam 3
colunas constantes que o L1 mata em `*200|...` cada. Fan-out constante é **dedutível** na entrada
→ a "entrada inteligente" que você pediu. → [[H-HIER-FANOUT-SPLIT-01]] — e é literalmente a forma
"tabelão/RLE" que você já listou pro S4.

**(d) DECODE/VIEW — sem caminho lazy hierárquico.** `decode_hierarchical` materializa tudo
(`:596-647`, zero yield); `LazyTCF` aceita só `#TCF.8M` (`view.py:67-70`). Pro eixo
O(1)/stream/view do Ciclo 4, o `.8H` ainda não tem view — é exatamente o **S5** do seu programa
(DAG de decode/busca/lazy). Registrado como mapeamento, não como ticket novo.

## 3. O que está bem fechado, por regime (matriz honesta)

| regime | evidência | estado |
|---|---|---|
| **didático/pequeno** (níveis comuns) | P1/P3a/P3b/P2/P4a welded, RT+wire+adversarial por incremento, suíte 754, byte-compat nível-0, +7 B/nível medido | **forte** — é o mais bem fechado do projeto |
| **massa sintética** | fuzz seedado 8000+6000+6000+4000 RT, auditorias 30k-150k, 0 corrupção silenciosa | **forte dentro do gerador** (viés declarado) |
| **massa real, aninhada À MÃO via FK** | TPC-H 1500 docs/75k filhos + 15000 docs; receita-cnpj 51k raízes/200k estab., fan-out real máx 396, null real até 25% (teto = BUG-SEQRLE xfail) | **capacidade provada; bytes NÃO são claim**; 1 topologia de espinha |
| **real aninhado NATIVO** | — | **ZERO** (célula vazia da coverage-matrix; T-SHAPER-NESTED-OUTPUT open/P3) |
| **telemetria/séries em escala** | só 2 casos didáticos minúsculos no `.8H`; beijing-pm25/wine medidos SÓ no flat (lab bN) | **descoberto** — e o wire da telemetria sintética (2.2c) mostra onde dói |

Precisão a registrar: o ADR-0033 cita "telemetria" entre os clássicos cobertos — verdadeiro para
a FORMA (didático), sem evidência em escala. As duas células vazias (real nativo; telemetria em
escala) são as entradas do **S4 com dado real** — e o T-SHAPER-NESTED-OUTPUT é o desbloqueador.

## 4. O que o novo revisa nas estratégias iniciais — mapa hipótese→estágio

O programa S0-S7 vira o guarda-chuva natural das medições pendentes. Em vez de labs soltos:

| estágio | o que ele decide | hipóteses que ELE absorve |
|---|---|---|
| **S4** wires lado a lado | forma física dos vínculos | [[H-REPLEVEL-FLAT-VS-PORNIVEL-01]] (rep-level flat × counts-por-nível — o duelo central do S4) · [[H-HIER-EMASK-SPARSE-01]] · [[H-HIER-FANOUT-SPLIT-01]] (a forma "tabelão") · [[H-STRUCT-ASDATA-01]] (counts pedem natureza?) |
| **S5** DAG decode/busca/lazy/paralelismo | custo de leitura por forma | view lazy hierárquico (gap 2.2d) · [[H-ACCEL-SIDECAR-01]] (dicas de view/índice são os sidecars do S5) · paralelismo predefinido |
| **S6** header | forma do meta | [[H-STRUCT-META-01]] (meta-RLE) · [[H-STRUCT-AMORT-01]]/[[H-CONTRACT-EXTERN-01]] (estrutura declarada 1× no contrato = a amortização) · [[H-STRUCT-DEF-01]]+P4b (root_kind/definições) |
| **S7** default/fallback | perfil | [[H-PROFILE-01]] (o guarda-chuva que decide o default por medição) · [[H-ENCODE-DEADLINE-01]] (modo pulsos como perfil) |

Duas consequências práticas: (i) **nenhuma dessas hipóteses precisa de lab avulso** — o S4-S7 as
mede juntas, com o oráculo S1 como comparador; (ii) o welded atual (counts+masks) já é um
candidato DENTRO do S4, não um concorrente do programa — se outra forma vencer em algum perfil,
vira forma alternativa sob [[H-PROFILE-01]], sem re-litigar a capacidade.

## 5. Recomendações (nenhuma é weld)

1. **Commitar o S0-S3 como está** (com as 3 restaurações de conteúdo feitas nesta revisão — ver
   diário: as edições tinham sobrescrito, por buffer antigo, o bloco DIREÇÃO do STATUS, ~119
   linhas do diário e o bloco P4b do ticket de paridade; tudo restaurado empilhando, nada seu
   foi perdido).
2. **S4 com dado real**: destravar T-SHAPER-NESTED-OUTPUT antes/junto do S4 — as duas células
   vazias da matriz (§3) são a validade externa do programa inteiro.
3. **Levar pro S4** as 3 hipóteses novas do trace (§2.2) — a emask densa é a mais material
   (bytes hoje); o fan-out-split é a que mais conversa com a sua "entrada inteligente".
4. **`.9` fica anotado, não feito**: prep-runs/fusão de passadas ([[H-HIER-PREP-RUNS-01]]).
5. **P4b continua na fila própria** (5 decisões abertas — restauradas no ticket); o S6 vai
   consumi-las, não substituí-las.
