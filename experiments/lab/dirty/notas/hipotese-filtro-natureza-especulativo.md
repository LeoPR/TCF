# Hipótese: filtro de natureza especulativo / híbrido (detect-during-compress) [aberta]

**Data**: 2026-06-25. **Origem**: proposta do owner (revisão do auto-detect com novos dados).
**Status**: `aberta` — levantada pra estudo no dirty lab. **Confiança**: A-revalidar.
Análise crítica completa: ver abaixo + a resposta da sessão. **NÃO implementar antes de
medir (I).**

## A proposta (owner)
Filtro de natureza **especulativo e pipelinizado**: detecta o formato na 1ª ocorrência
(via `classify_value`), e em dois modos —
- **imediato** (formato fácil): encolhe já (`111.222.333.444-66`→`111222333444`), entrega
  ao OBAT a string menor; se um valor contradiz depois → **rollback** (restaura ref original)
  e desliga o filtro;
- **tardio** (formato "difícil de reorganizar"): OBAT trabalha no valor INTEIRO; o filtro
  analisa **em paralelo** e encolhe as **referências** entre OBAT↔HCC (ou após o HCC).
Tudo como fila produtor-consumidor com buffer (latência / streaming).

## Decomposição (3 ideias distintas)
- **(I) COMPRESSÃO**: aplicar a nature DEPOIS do OBAT (nas refs) vs ANTES (pré-transform
  base94, como hoje). É a pergunta nova e central.
- **(II) PERFORMANCE**: detecção especulativa + fila paralela + rollback. Execução
  especulativa → resultado DEVE ser idêntico (perf, não muda bytes). Alinha c/ streaming
  (V2-J/K).
- **(III) AUTO-DETECÇÃO**: reconhecer formato sem declaração. Auto-APLICAR muda output →
  opt-in obrigatório (byte-canônico, ADR-0015); auto-DETECTAR/sugerir é byte-neutro.

## Análise crítica
- **(I) REFINADA (debate 2026-06-25)**: a tensão de fragmentação que eu levantei vale só
  pro modo TARDIO (aplicar pós-OBAT no valor já partido em refs). No modo IMEDIATO
  (normalizar ANTES do OBAT — `111.111.111-11`→`111111111`), NÃO há fragmentação: o OBAT
  recebe strings limpas/curtas e acha padrão normal. Dedup do OBAT (`^1`) resolve repetição
  — aplica a nature 1x no nó único, refs apontam. Conceito do owner: correto.
  - O eixo real NÃO é "OBAT fragmenta" — é **"normalizar-e-deixar-o-pipeline-comprimir vs
    codificar-denso (base94)"**.
  - **vs RAW**: normalizar (tirar máscara constante interleaved) + pipeline → plausivelmente
    SEMPRE ajuda, sem desvantagem (afirmação do owner sustenta-se aqui).
  - **vs base94 ATUAL**: data-dependente — base94 é mais denso pra ALEATÓRIO-ÚNICO (5 chars
    vs 11 dígitos); normalizar+pipeline GANHA pra CADENCIADO (seq-RLE `*N+1|template`, que
    base94 de inteiros consecutivos não ativa). NÃO é estritamente melhor.
  - **PRECEDENTE VIVO**: a nature de IP (`TemplatedPaddedSpec`) JÁ faz isto — normaliza
    digit-only pra ATIVAR seq-RLE (ganho vem do pipeline, não do tamanho cru; IP-subnet
    1.71%). Só CPF/CNPJ (`TemplatedCheckedSpec`) vai pra base94. **A proposta destilada**:
    CPF/CNPJ ganham a OPÇÃO de normalizar-e-comprimir (como IP) vs base94. Mecanismo já existe.
- **(II) é perf, não resultado**: especulação tem que dar bytes IDÊNTICOS (senão
  não-determinismo). Custo alto (2 filas, rollback, 2 modos, concorrência determinística)
  pra ganho de LATÊNCIA, num regime onde natures pagam estreito (revisão de capacidade:
  CPF/CNPJ/IP real, some sob brotli). **Prematuro construir antes de (I) pagar.**
- **(III) byte-canônico**: auto-apply opt-in (default = hoje, D1-D9=1523B intacto);
  detect-sem-aplicar byte-neutro (SideOutputs).

## Reavaliação 2 (debate 2026-06-25) — o FLUXO de duas vias é o ponto, não o CPF
Owner: CPF é UUID-like (aleatório, sem similaridade parcial) → base94+drop-DV é certo; o
modo *depois* não muda bytes pra CPF (CPF é "desperdício" do OBAT). CPF é só ILUSTRATIVO
do mecanismo de **duas vias** (mapear-ANTES vs reservar-pra-DEPOIS).
- **Modo ANTES**: as 2 natures welded JÁ usam (CPF→base94, IP→normaliza). 100% coberto.
- **Modo DEPOIS** (a inovação): deixar o OBAT achar similaridade parcial, substituir refs.
  Benefício de compressão SÓ pra formatos com **similaridade parcial**. **Sem consumidor
  atual**: CPF aleatório não tem; IP precisa do normaliza-antes. A fragmentação volta aqui
  (valor parcialmente-similar fica partido no OBAT → nature só atua no resíduo inteiro).
- **Veredito**: fluxo é generalização arquitetural limpa + alinha com streaming (V2-J/K),
  mas o modo *depois* resolve um problema que NENHUM formato atual tem. **Gate empírico
  antes do código**: existe, em dado real, formato nature-elegível COM pedaço parcial que o
  OBAT pegaria E onde `OBAT→nature-no-resíduo` bate `nature→ANTES`? Se não → YAGNI (ou só
  perf: aplicar nos nós únicos, que não muda bytes). H5 abaixo.

## Sub-hipóteses pro lab (ordem: barato→caro, medir antes de construir)
- **H5 (consumidor do modo-depois, read-only)**: varrer os datasets canônicos atrás de
  colunas nature-elegíveis COM similaridade parcial (pedaços que o OBAT pegaria) — i.e., um
  formato onde o modo *depois* bateria o *antes*. Se zero candidatos → o modo *depois* é
  YAGNI. É o GATE que justifica (ou não) construir o fluxo de duas vias.
- **H1 (compressão, read-only) — NORMALIZAR vs BASE94 vs RAW**: em CPF/CNPJ reais (Receita,
  br-identidades) em DOIS regimes — aleatório-único e sequencial/cadenciado —, comparar
  bytes de: (a) **base94** (nature atual `TemplatedCheckedSpec`); (b) **normalizar** (tirar
  máscara, manter dígitos)→OBAT→HCC (= o que o IP `TemplatedPaddedSpec` já faz); (c) **RAW**
  (sem nature). Hipóteses: (b)≤(c) sempre; (b)<(a) no cadenciado (seq-RLE); (a)<(b) no
  aleatório (base94 denso). Mede a fronteira.
- **H2 (fragmentação)**: medir o quanto o OBAT fragmenta valores de ID formatado (afixos
  compartilhados) — quantifica a tensão "valor partido vs nature precisa do inteiro".
- **H3 (detecção)**: acurácia da detecção na 1ª ocorrência + taxa de falso-positivo (= taxa
  de rollback). Read-only sobre colunas reais.
- **H4 (pipeline/perf)**: só se (I) pagar — latência da especulação vs sequencial. Aqui sim
  a fila/streaming.

## Veredito / próximo passo
Coração = (I), **medível read-only sem construir nada**. (II)/(III) são caros/gated e só
depois de (I) provar a composição. **Próximo**: montar o mini-experimento H1/H2 no dirty
lab (comparar as 3 vias em ID formatado real). Não construir a fila especulativa antes.

## Cross-links
- [ADR-0015](../../../../docs/adr/0015-natures-templated-checked-weld.md) (natures, rejeição do
  auto-apply), [specs-capacity-map.md](specs-capacity-map.md) (regime estreito), OBAT
  ([docs/algorithms/OBAT.md](../../../../docs/algorithms/OBAT.md)), streaming V2-J/K
  ([ADR-0018](../../../../docs/adr/0018-v2-format-roadmap.md)).
- Registry de hipóteses: adicionar entrada (H-NAT-SPEC).
