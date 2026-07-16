---
title: LEVANTAMENTO DA ATIVIDADE — P4a (array-em-array via count recursivo) — PARA INSPEÇÃO
type: report
status: welded
created: 2026-07-16
related:
  - tickets/T-CODE-TCF8H-JSON-PARITY.md
  - docs/adr/0033-hierarchical-codec-weld.md (§Update P4a)
  - experiments/lab/dirty/2026-07-16-0213-p4a-array-em-array-estudo/
  - experiments/lab/dirty/notas/p4-replevel-nroots-levantamento.md (a revisão crítica que orientou — marcada lá como opinião, não decisão)
  - tickets/T-API-BOUNDARY-CONTRACTS.md (limitações inerentes)
---

# Levantamento da atividade — P4a. Para inspeção do owner.

**[probatório]** Relato do que FOI FEITO no P4a (não é plano). Fatos verificados no repo em
`191babf` (pushado). Escopo: `.8` = funcionalidade; otimização/limpeza = `.9`.

> ## Errata 2026-07-16 (achados do owner, todos procedentes)
>
> **(1) O lab não tinha evidência.** Este levantamento foi escrito sobre um lab **sem nenhum `.tcf`**:
> o protótipo devolvia dicionários em memória e nunca serializou wire, então as conclusões se apoiavam
> em print, não em artefato inspecionável — violando a convenção do dirty lab. Corrigido: `run.py`
> passa pelo core e emite **24 `.tcf`** + roundtrip byte-idêntico ao canônico (`assert` + `diff`).
> Foi regressão minha num padrão já estabelecido (P1=3, P3a=9, P3b=9, P2=11 `.tcf`; P4a=0).
>
> **(2) A tabela de custo estava confundida.** A versão anterior (28/45/67/101/160 B) variava
> profundidade **e** número de folhas ao mesmo tempo (folhas dobram por nível), e o "~7 B/nível" era
> *interpretação* minha, não leitura da tabela. Refeito com carga constante (§3): o **valor 7 B/nível
> se confirma exato**, mas a evidência anterior não o sustentava. Tabela corrigida abaixo.
>
> **(3) Atribuição errada.** Onde este documento dizia "**seu** parecer"/"o gate do **seu** parecer",
> o texto citado é a seção *Revisão crítica independente* de `p4-replevel-nroots-levantamento.md`,
> que **você mesmo marcou** `[probatório→opinião; não é decisão do owner]`. Ela virou operativa por
> **sua adoção explícita** ao aprovar o lab — não por ser um parecer seu. A distinção é material
> para o **P4b**, onde nada foi adotado e portanto **nada está decidido**.

## 1. Cronologia (4 commits, todos pushados)

| commit | ato |
|---|---|
| `e01a15d` | **(owner)** revisão P2 + decomposição da investigação P4 (STATUS, checkpoint, diários, parecer) |
| `702868f` | fecho do **residual do P2** que o owner achou (tag desconhecida após size → `[]` calado) |
| `c9d9ce7` | **ESTUDO P4a** (lab `2026-07-16-0213`) — count recursivo, gramática, gate 12/12 |
| `191babf` | **WELD P4a** no core + hardening da auditoria adversarial |

Sequência seguiu o ritual da ordem recomendada na revisão crítica: *estudo em lab próprio → inspeção/aprovação do owner →
weld → gates → auditoria*.

## 2. O que foi decidido e implementado

**Mecanismo**: count recursivo (recomendado na revisão crítica; adotado por você ao aprovar o lab). Cada nível de aninhamento
tem coluna de **counts** (e **element-mask**) próprias; counts do nível k+1 = 1 entrada por elemento
**não-null** do nível k (denso). Novo kind `arr_arrays`, cujo `kids` é o **nó anônimo** do nível interno.

**Gramática** (a que você inspecionou e aprovou): `campo#:c0?:e0[#:c1?:e1[...]]` — cada `#` abre um
nível; `?` após o `#` = element-mask **daquele** nível; o elemento entre `[...]` é a spec recursiva
(`#`=array interno · `{campos}`=objetos · `[]<tag>`=escalares).

**Colunas**: nível 0 = `count`/`emask` **sem sufixo** (byte-compat); internos = `count1`/`emask1`, …

**Firmado** (o item que o gate pedia explícito): **null entre arrays = P3b∘P4a** (element-mask
por nível cobre `[[1],null,[2]]` e `[[1,null,2]]`) — **não é P5**; P5 segue sendo tipo-misto
(array+escalar no mesmo nível = fail-loud).

**Código** (`src/tcf/hierarchical.py`, +337/−133): `_array_node` · `_sfx` · `_array_leaves` ·
`_emit_array_value` · `arr_meta` · `parse_array` · `_read_array` — recursivos, em **blocos legíveis**
(diretriz `.9`/port Rust do 1.0).

## 3. O gate (da revisão crítica, adotado por você ao aprovar o lab) — item a item

| item do gate | status |
|---|---|
| matriz rasa | ✅ RT |
| profundidade > 2 | ✅ RT (prof. 3 didático; fuzz até nível 4; cap em 128) |
| arrays internos vazios | ✅ RT (`[[],[1],[]]`; `[]`≠`[[]]`≠`[[1]]`) |
| array de arrays de objetos | ✅ RT (`turmas#[#[nome]]`) |
| **null entre arrays** — decidir se P3b cobre | ✅ **decidido: P3b∘P4a cobre**, não é P5 |
| count interno truncado/excedente | ✅ fail-loud (exaustão por coluna) |
| fechamento/tag inválidos | ✅ fail-loud (`]` deletado, tag desconhecida) |
| **custo por profundidade, sem limite arbitrário antes da evidência** | ✅ **medido** (abaixo); cap 128 introduzido **só** após evidência de `RecursionError` cru na auditoria |

**Custo medido** — desenho corrigido (ver Errata (2)). "Profundidade" e "nº de folhas" são variáveis
**separadas**; medi-las juntas confunde framing com carga. Artefatos: `outputs/02a-framing-prof{1..6}.tcf`
e `outputs/02b-arvore-prof{1..5}.tcf`.

**(a) Framing ISOLADO** — carga constante (`[1,2]`), só a profundidade varia. É este o custo do nível:

| prof. | `.tcf` | json | Δ/nível | header |
|---:|---:|---:|---:|---|
| 1 | 28 B | 13 B | — | `m#:3[]:8n` |
| 2 | 35 B | 15 B | **+7 B** | `m#:3[#:3[]:8n` |
| 3 | 42 B | 17 B | **+7 B** | `m#:3[#:3[#:3[]:8n` |
| 4 | 49 B | 19 B | **+7 B** | `m#:3[#:3[#:3[#:3[]:8n` |
| 5 | 56 B | 21 B | **+7 B** | `m#:3[#:3[#:3[#:3[#:3[]:8n` |
| 6 | 63 B | 23 B | **+7 B** | `m#:3[#:3[#:3[#:3[#:3[#:3[]:8n` |

→ overhead **+7 B/nível, exato e constante**: o framing (a coluna de count daquele nível). Os counts
em si colapsam por RLE. É o que sua preocupação "muitos marcadores" aponta — registrado (§5).

**(b) Árvore binária cheia** — realista, **confundido de propósito** (folhas dobram junto): 28/38/48/68/80 B
(Δ +10/+10/+20/+12). **Não** é custo de nível; está no lab justamente para não sugerir que o framing cresce.

## 4. Evidência (3 camadas)

**Estudo — a IDEIA** (lab `2026-07-16-0213`, `study.py`+`proto.py`, pré-weld): didático **12/12** ·
fuzz de profundidade seedado (níveis 1–4, ~20% null/nível, n/b/s) **4000/4000** · adversarial de frame
(count truncado/excedente, folha faltando/sobrando) **fail-loud 4/4**. O protótipo **não serializa
wire** — seus metas são pedagógicos (sem sizes). Foi essa a origem da Errata (1).

**Wire — o ARTEFATO** (mesmo lab, `run.py`, pós-weld, pelo core): **24 `.tcf` inspecionáveis**, um por
caso do gate + 11 de profundidade + base adversarial; cada roundtrip é **arquivo byte-idêntico** ao
canônico de `intermediates/` (`assert` no run + `diff` externo conferido); adversarial no wire real
(tag desconhecida, `]` deletado, bytes apendados, corpo esvaziado) **fail-loud 4/4**. Exemplo legível
inteiro — `[{"m":[[1,2],[3]]}]`:

```
#TCF.8Hm#:3[#:8[]:8n
\2          <- 1 registro, 2 elementos no nível externo
*2-1|\2     <- counts internos: 2, 1   (seq-RLE)
*3+1|\1     <- folhas: 1, 2, 3
```

**Weld** (core real): 14 casos P4a + fuzz seedado + tipo-misto + 6 de hardening → **117 passed** no
módulo; **suíte 754 passed, 2 skipped, 2 xfailed**; **flat byte-canônico intacto**; **byte-compat de
nível-0** (wire de nível único idêntico ao pré-P4a — 14/14 verificado pela auditoria).

## 5. Auditoria adversarial (`wf_5fa61459-a9e`) — o que resistiu e o que foi consertado

**RESISTIU** (o núcleo do design): alinhamento entre níveis correto e simétrico; codificação
**injetiva** (counts por nível desambiguam `[[1,2],[3]]` vs `[[1],[2,3]]`); **0 corrupção silenciosa**
na mecânica; **0 hang**; ~50k+9k iterações de fuzz RT; compose total (P1+P2+P3a+P3b+P4a) RT;
byte-compat 14/14. **A associação entre níveis nunca se perde calada** (sua preocupação central).

**14 claims → 8 consertos** (todos de blob **adulterado/estrangeiro**; nenhum afetava blob emitido
pelo encoder), aplicados em `191babf`:

| # | furo | conserto |
|---|---|---|
| 1 | `RecursionError` **cru** (header hostil ~4 KB; encode profundo) | cap de 128 níveis, `HierarchicalError` |
| 2 | meta truncado perdendo a **tag** → int decodava como string **calado** | size-explícito-na-última-string = não-canônico → fail-loud |
| 3 | corpo perdido → `[]` **calado** | `total==0` → fail-loud |
| 4 | **nome duplicado** no meta → coluna descartada **calada** | `seq` rejeita duplicado |
| 5 | **bytes apendados** (all-sized) → registro fantasma | exaustão de bytes → fail-loud |
| 6 | `]` deletado (nível interno) aceito calado | exige `]` ou fim-de-meta |
| 7 | coluna de **DADO** corrompida vazava exceção crua | guard re-tipa dado também |
| 8 | `int()` leniente (`+2`, `1_0`, dígito unicode); `UnicodeDecodeError` cru | ASCII estrito + re-tipagem |

**Limitações INERENTES** (indetectáveis sem checksum — registradas no
[T-API-BOUNDARY-CONTRACTS](../../../../tickets/T-API-BOUNDARY-CONTRACTS.md), trilha tcfx/pré-1.0):
meta truncado **até** uma forma canônica all-string; truncamento de cauda unsized; `]` final
omit-closed em `arr_objects`; apêndice quando a última coluna é unsized.

## 6. Sua preocupação, registrada (não fechada — é `.9`)

**H-REPLEVEL-FLAT-VS-PORNIVEL-01** (roadmap): reuso entre níveis / "tratar tudo como **colunas com
buracos**", sem perder a associação entre níveis; risco de "muitos marcadores só pra satisfazer o
preenchimento". Minha opinião crítica registrada junto: real mas limitada (o custo é o framing fixo
~7 B/nível, medido acima; os counts colapsam por RLE); a forma "flat" ≈ **rep-level do Dremel** —
menos marcadores, **mas** perde a separabilidade por-nível (responder "nível k" exigiria varrer o
stream) → conflita com o eixo O(1)/stream/view do Ciclo 4 → é trade de **perfil**
([[H-PROFILE-01]]), revisável no `.9` como você decidiu.

## 7. Estado da paridade JSON e o que falta

✅ objetos · arrays · strings · escaping · aninhamento · **P1** presença · **P3a/P3b** null ·
**P2** tipos · **P4a** array-em-array.
❌ **P4b raiz generalizada** (próximo; **nada decidido** — a revisão crítica RECOMENDA envelope/discriminador `root_kind` explícito, a
ordem de arrays **não é livre**, gate deve distinguir `[]`/`[{}]`/`{}`/escalar/`""`/`null` na raiz) ·
**P5 union** (fronteira; não usar "qualquer JSON" antes dele) · congelar contratos de borda.

Dívida core registrada (independente): `BUG-SEQRLE-RANGE-EMPTY-B`, `BUG-BRACKET-CELL-LOSS` (R0,
`xfail`, fix exige aprovação + gate byte-canônico).
