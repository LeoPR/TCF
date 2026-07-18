---
title: MATRIZ DE CAMINHOS — combinações entre dados (hierarquia): fechar / avaliar / marcar
type: report
status: aberta
created: 2026-07-17
related:
  - tickets/T-CODE-TCF8H-JSON-PARITY.md
  - experiments/lab/dirty/notas/p4b-levantamento.md
  - experiments/lab/dirty/notas/escala-implementacao-paridade-json.md
  - experiments/lab/dirty/notas/revisao-generosa-hierarquia-2026-07-16.md
  - experiments/lab/dirty/notas/funil-fechamento-json-language-2026-07-17.md
  - tickets/BUG-SEQRLE-RANGE-EMPTY-B.md
  - tickets/T-SHAPER-NESTED-OUTPUT.md
  - docs/adr/0033-hierarchical-codec-weld.md
---

# Matriz de caminhos — hierarquia/combinações: o que fechar, avaliar e marcar

**[probatório + recomendação]** Pedido do owner (2026-07-17): avaliar os caminhos pra fechar (ou
avaliar-e-marcar) a questão das combinações entre dados, com o melhor custo/benefício. Estado
verificado no repo em `da1aa73`.

## 0. Onde estamos (o que JÁ não é mais caminho)

**D_json em nível de DATASET: 100% fechado.** P1 ragged · P2 tipos · P3a/P3b null · P4a
array-em-array · escaping de nome · escape D_json (chave `""`, LF em valor, LF em nome). O critério
`J-RT-TX ⟹ T-RT` não tem exceção de dataset — pinado em `test_json_flow_parity.py`. Suíte 821.
O que resta da paridade JSON é **um único eixo**: a RAIZ.

## 1. A matriz

| caminho | custo | benefício | veredito |
|---|---|---|---|
| **P4b · raiz generalizada** | **médio** — levantamento PRONTO (decomposição A/B/C, opções de discriminador); falta: **5 decisões suas** + estudo + weld | **7 lacunas de uma vez** → D_json **COMPLETO** (a frase "paridade com o fluxo JSON" fica sem asterisco estrutural); fecha junto: null-na-raiz, formas vazias (H-STRUCT-DEF-01, root_kind+count), e dá o lugar da decisão de ordem-de-chaves | **FECHAR — melhor custo/benefício do tabuleiro** |
| **BUG-SEQRLE (+BUG-BRACKET, mesma família)** | **médio** — toca HCC core (L1): exige **sua aprovação** + gate byte-canônico real-world | destrava **validação em POPULAÇÃO real inteira** (hoje o PW3 da receita-cnpj está travado; teto 25%); conserta R0 que afeta o flat de qualquer usuário (`"ETC & TAL..."` crasha) | **FECHAR (com sua aprovação)** — é o que separa "validado em amostra" de "validado em população" |
| **E3 · SideOutputs no `.8H`** | baixo-médio — aditivo, não muda wire | destrava o **warning** que você pediu (política json-like do adaptador reporta desvios), profiler (H-ACCEL-SIDECAR) e schema-tool sobre hierarquia | **FECHAR em seguida** — barato e destrava família |
| **Real aninhado nativo (T-SHAPER-NESTED-OUTPUT)** | médio — tooling em `scripts/` (não é core) | preenche as **2 células vazias** da matriz de evidência (real nativo; telemetria em escala) — a validade externa de TUDO acima | **AVALIAR** — vale antes/junto de qualquer S4 |
| **S4–S7 (forma física: rep-level×counts, emask esparsa, fanout-split, tabelão)** | médio-alto — lab grande; oráculo S1 e corpus JÁ existem (lab 1708) | decide FORMA por medição (não adiciona capacidade); hipóteses já mapeadas estágio-a-estágio | **AVALIAR/MARCAR** — é otimização; sua diretriz é funcionalidade primeiro (`.8`), forma no `.9` |
| **P5 · union (tipo misto)** | alto — gramática nova (def-level de tipo) | fecha "qualquer JSON" literal; hoje a fronteira declarada + fail-loud protege | **MARCAR** — depois do P4b; sem P4b o P5 nem tem onde morar (raiz polimórfica) |
| **Combinações AMPLAS (N:N/snowflake/grafo)** | médio p/ ESTUDO (não p/ weld) | o seu sentido largo ("ligações diversas"). Já registrado: H-HIER-MULTITABELA-01 (fronteira do ADR-0033); o modelo S0 é ÁRVORE por construção (CycleError; IR de contenção). **Dado real JÁ no hub**: br-identidades `socio_cpf`→`pessoas.cpf` (30.133 FK, 0 órfãos) — dá pra estudar super-hierarquia (árvore + tabela de referências) sem baixar nada | **MARCAR com estudo curto** — o menor passo honesto é estender o IR do S0 de árvore→DAG-com-refs num lab, medindo com o FK real; decide-se no v1.0 como você já registrou |
| **E1 residual + dívidas de mensagem** (surrogate `UnicodeEncodeError` cru; `KeyError` cru do flat; leniência `\X`→`X` do L1) | baixo — mas toca `src/tcf` (aprovação) | higiene fail-loud; zero capacidade | **MARCAR** — carona no próximo weld aprovado (ex.: junto do fix SEQRLE) |
| **Auditoria do escape (ritual)** | ~0 — relançada, rodando | gate obrigatório do weld `da1aa73` | em andamento; reporto ao fechar |

## 2. A leitura de custo/benefício (recomendação)

**O tabuleiro tem UM lance dominante: P4b.** Tudo que era barato e independente já foi feito nesta
sequência (E0/E1-parcial/E2/E4/E6). O que sobrou de paridade está 100% concentrado na raiz, o
levantamento está pronto, e as 7 lacunas caem juntas. Depois dele, "hierarquia em árvore = fechada"
é frase inteira — e o P5/amplas viram fronteiras declaradas, não pendências.

**O segundo lance não é de capacidade, é de VALIDADE: o par de bugs L1.** Sem ele, toda validação
real-world do `.8H` fica em amostra (teto 25% na receita). É o único item que exige sua aprovação
explícita pra tocar o HCC — e o gate byte-canônico existe exatamente pra esse tipo de fix.

**Sequência recomendada** (cada passo destrava o seguinte):

1. **Suas 5 decisões do P4b** (§5 do [p4b-levantamento](p4b-levantamento.md): escopo no `.8`;
   separar problema B; discriminador (1) char sempre vs (2) só-quando-≠dataset; contrato de API;
   terminologia) → estudo P4b em lab → weld. **Fecha D_json completo.**
2. **Sua aprovação pro par SEQRLE+BRACKET** → fix com gate byte-canônico + real-world → PW3
   população inteira da receita no `.8H`. **Fecha a validade.**
3. **E3 SideOutputs** → destrava warning/profiler. Aí o adaptador json-like (perfil `strict`/
   `json_like`) tem onde reportar desvios.
4. Marcados com dono: P5 (pós-P4b) · S4-S7 (`.9`, oráculo pronto) · amplas (estudo IR→DAG com o
   FK real de br-identidades, v1.0) · shaper-nested (quando a validação em escala apertar).

## 3. O que este documento NÃO decide

As 5 decisões do P4b são suas; a aprovação do L1 é sua; o timing do estudo-amplas é seu (você já
registrou: JSON é o alvo prático, a estrutura ampla é v1.0/v2.0 — nada aqui contradiz isso).

Régua de fechamento sugerida, sem ampliar o gate deste documento:
[funil JSON-language → datasets → estruturas gerais](funil-fechamento-json-language-2026-07-17.md).
