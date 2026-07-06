# Teoria da cardinalidade no TCF — força, estratégias e redundância [dispositivo/probatório]

**Data**: 2026-07-05 · síntese da peça 7 (dedução) + peça 8 (força/trade, medida) + survey de prior-art
(workflows `cardinalidade-inferencia` + `teoria-cardinalidade`). Guarda-chuva:
[T-STUDY-HIERARCHICAL-TCF](../../../../tickets/T-STUDY-HIERARCHICAL-TCF.md) · mapa:
[estudo-tcf-hierarquico-mapa](estudo-tcf-hierarquico-mapa.md). Marca **[probatório]** onde é medido;
**[dispositivo]** onde é definição/princípio.

## 1. Duas estratégias de encode, mesmo RT

Para uma relação **1:N**, há duas vias que reconstroem o **mesmo** dado (RT lossless):

- **(a) RÁPIDA, guiada-por-estrutura** — usa a cardinalidade CONHECIDA (do JSON) pra fazer **RLE do
  valor-pai** (`*N|pai`). Pega só a **multiplicidade** que a cardinalidade prediz.
- **(b) PLENA, data-driven** — roda **OBAT/HCC** no tabelão desnormalizado. Pega a multiplicidade **+**
  redundância de **afixo/dicionário inter-item**.

**Enquadramento (avaliação parcial / projeções de Futamura)** [dispositivo]: (a) é (b) com a busca
**restrita** ao transform que a cardinalidade prediz. Conhecer o schema pré-resolve o control-flow de
forma estática (onde estão os runs, qual coluna é pai) → encode residual faz **menos trabalho** → mais
**rápido** (O(d) runs vs busca O(N·W)). Especializar **preserva semântica** (mesmo RT) e melhora
**velocidade**, mas **não** melhora a razão por si — melhorar razão exige **mais** busca (o passe pleno).
**Logo velocidade e razão são eixos separados; o trade é intrínseco.**

## 2. A dominância de (b) é FRACA e CONDICIONAL

**Relação de superconjunto** [dispositivo]: o espaço-modelo de (b) **contém** o de (a) — o seq-RLE do HCC
reproduz o `*N|` de (a) e ainda explora afixo/dict cross-item. Um otimizador irrestrito que contém o
restrito nunca perde **para um coder ÓTIMO**. Mas OBAT/HCC são **heurísticas gulosas online, não ótimas**.

**(b) domina estritamente em razão só com as TRÊS condições juntas** [probatório, medido peça 8]:
1. **existe** redundância inter-item (afixo/dict abrangendo ≥2 itens nos campos-filho);
2. o detector **guloso realiza** o padrão (não garantido — anomalia medida: ibge 5000→5571 **não-monotônica**);
3. a **largura-de-valor economizada** supera o overhead das refs extras — no regime **<1KB** o ganho de
   5–20B **some no ruído do brotli** (caveat peça 1).

**(a) Pareto-domina** (mesma razão, mais rápida) quando os filhos são **alta-cardinalidade/únicos** (sem
afixo/dict compartilhado): (b)==(a) em bytes, e (a) é mais rápida. Canônico: 1:N com filho = ID/hash único
(o LIMITE `!cpf raw` do T1). **Medido (peça 8)**: ids opacos → rápido **30B** < pleno **39B** (OBAT super-tokeniza).

## 3. Ortogonalidade: cardinalidade ≠ compressibilidade [probatório]

O achado-chave da peça 8, agora com base teórica:

> **CARDINALIDADE** (multiplicidade → normalização/RLE do valor-inteiro) **⊥** **COMPRESSIBILIDADE**
> (afixo/inter-item → OBAT/HCC). **Eixos independentes.**

Medido: a coluna FRACA (`cliente_`, multiplicidade=1 → nada a normalizar) comprime muito (full 42B <<
fast 144B) — **por afixo**, não por cardinalidade. O gap (b)−(a) é **exatamente** a redundância inter-item,
e ela vive na **largura do valor** (peça 1: a multiplicidade ×N é conservada, RLE↔fk duais; normalização
compra **reconstrução**, não bytes de multiplicidade — o ganho é trocar valor largo repetido por código estreito).

## 4. Camadas de redundância (o que cada via pega)

| camada | o que é | fonte | (a) rápida | (b) plena |
|---|---|---|---|---|
| **0 · multiplicidade** | repeat exato do pai nas N linhas-filho | FORMA (schema/cardinalidade) | ✓ `*N|` | ✓ seq-RLE |
| **1 · afixo/cadência** | prefixo/sufixo compartilhado, cadência | CONTEÚDO (dados) | ✗ | ✓ OBAT/HCC |
| **2 · dicionário cross-item** | valor repetido entre itens diferentes | CONTEÚDO | ✗ | ✓ @dict / OBAT |

A via rápida (a) captura **só a camada 0** (e barato — pula o scan de igualdade e o de afixo). Camadas 1–2
= o "inter-item", só a plena.

## 5. Força de cardinalidade — 2 faixas ortogonais [dispositivo]

Força decompõe em **exatidão** (a FD vale?) × **payoff** (vale bytes?):

| classe | critério | exemplo | estratégia admissível |
|---|---|---|---|
| **FORTE** | FD exata (g3=0) **E** pai coarse (d≪n) | `categoria→@dict`, email repetido | guiada segura + payoff real |
| **FRACA** | **chave** (d=n, FD trivial, 0 repetição) OU multiplicidade~1 | `cpf` chave = 1:1 | nada a fatorar (distinguir chave de grupo!) |
| **QUASE** | FD **aproximada** (0<g3≤ε) | `cpf→nome` c/ linha suja | **plena** é mais segura (não afirma a FD) |
| **INDUZIDA** | a entrada **DITA** (árvore JSON, g3=0 por construção) — **[dispositivo]** | response aninhado | guiada **de graça**, sem descoberta de FD |

**A força GATEIA a estratégia**: INDUZIDA (o JSON é a fonte, g3=0) → **guiada rápida é segura**;
DEDUZIDA de CSV (probatório, revalida) → real-world tem near-FD → a guiada exige verificação + tratamento
de exceções, estreitando a vantagem, e a **plena domina em risco-de-correção**. Refinamento crítico:
**chave (d=n) ≠ grupo-coarse (d≪n)** — chave dá FD trivial SEM repetição = zero ganho; distinguir ANTES.

## 6. Ordem (Order Dependency) — o terceiro eixo [dispositivo]

Realizar o RLE do pai exige o pai **AGRUPADO**. Descobrir a FD é **necessário, não suficiente**:
- **ordem livre** → ordenar+RLE paga O(d) runs (estritamente melhor que O(N) refs do fk);
- **ordem semântica** → materializar os runs custa um **side-channel de permutação** (= os
  repetition/definition levels do Dremel). Quem declara que reordenar é lossless? (liga com `sort_by` order-free).

## 7. A reconciliação: as duas vias são um CASCADE, não rivais [dispositivo]

**Parquet/ORC são o arquétipo**: aplicam encoding leve **schema-aware primeiro** (RLE_DICTIONARY,
bit-packing, delta = a via rápida estrutural) e **só então** um compressor de bloco geral (Snappy/zstd = a
via data-driven no resíduo). Não confiam ao LZ geral achar a estrutura de dicionário (a janela do LZ pode
não abranger a coluna toda) + o dict habilita **predicate pushdown / lazy-query** (o valor do TCF: query
toca 0,2–7,9% do blob).

**Lição para o TCF**: cardinalidade (rápida, camada 0) e OBAT/HCC (plena, camadas 1–2) são
**complementares em cascata**, não rivais. Um dial seria: pré-passe de cardinalidade → OBAT/HCC → brotli.
Isso reconcilia "as duas coisas que o TCF naturalmente dá" (owner).

## 8. Hipóteses (registradas em [roadmap-hipoteses](roadmap-hipoteses.md))

- **H-CARD-01** (a) e (b) coincidem em RT; divergem em (velocidade, razão). — medir por-coluna.
- **H-CARD-02** dominância de (b) é fraca e FALHA no encoder guloso real (medido +9B em opaco).
- **H-CARD-03** força (multiplicidade+g3) prevê o ganho de NORMALIZAÇÃO, não o de compressão (grid 2×2).
- **H-CARD-04** sob QUASE (g3>0), a guiada exige side-channel de exceções; a plena é lossless de graça.
- **H-CARD-05** distinguir CHAVE (d=n) de GRUPO-COARSE (d≪n) é pré-requisito da via guiada (zero ganho em chave).
- **H-CARD-06** Order Dependency gateia o custo da guiada (ordem livre grátis; semântica paga permutação).
- **H-CARD-07** o ganho inter-item pode NÃO sobreviver ao brotli a jusante — medir {fast,full}+brotli real-world.

## 9. Agenda de pesquisa (lentes futuras)

FD aproximada real-world (distribuição de g3 nas colunas 1:N dos 8 canônicos) · determinante composto
({A,B}→C, TANE/HyFD) · Order Dependency formal (custo permutação vs O(N) fk vs O(d) runs) · **two-stage
medido** (o inter-item sobrevive ao brotli?) · nested-TCF adapter como instância da via guiada · SideOutputs
como pré-passe do seletor (d_i de graça) · N:N/link posicional (Inclusion Dependency, SPIDER/BINDER) ·
modelo de custo do trade speed(a) × ratio(b).

## 10. Referências

Partial evaluation / Futamura · Parquet/ORC (RLE_DICTIONARY+delta → Snappy/zstd; dictionary-fallback;
predicate pushdown) · LZ77/78 (janela deslizante limitada) · Dremel rep/def levels (Melnik 2010) ·
factorized DBs (Olteanu & Zavodny) · FD discovery: TANE (Huhtala 1999), HyFD (Papenbrock 2016), Pyro,
Metanome (Papenbrock VLDB 2015) · g3-error (Kivinen & Mannila 1995) · Order Dependency · Heath. Internos:
peças 1/7/8 do grupo hierárquico; T1 (limite high-card); ADR-0025 (@dict V2-B); lazy-query.
