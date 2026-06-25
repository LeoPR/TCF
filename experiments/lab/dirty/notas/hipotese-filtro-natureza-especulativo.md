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
- **(I) é o mais valioso E tem tensão real**: a base94-antes-do-OBAT DESTRÓI a estrutura
  compartilhada (pontos/traço/posições) que o OBAT comprimiria. O modo tardio deixa o OBAT
  achar estrutura, depois encolhe. **MAS** o OBAT FRAGMENTA o valor por afixo, e a nature
  precisa do valor INTEIRO (recomputar DV, dropar máscara). Logo: onde o OBAT ajuda
  (estrutura compartilhada), a nature pós-OBAT fica difícil (valor partido); onde não
  fragmenta (alta entropia), o OBAT não acrescentou. **Não é ganho óbvio — só medição
  resolve.** (É o "formato difícil de reorganizar" do owner.)
- **(II) é perf, não resultado**: especulação tem que dar bytes IDÊNTICOS (senão
  não-determinismo). Custo alto (2 filas, rollback, 2 modos, concorrência determinística)
  pra ganho de LATÊNCIA, num regime onde natures pagam estreito (revisão de capacidade:
  CPF/CNPJ/IP real, some sob brotli). **Prematuro construir antes de (I) pagar.**
- **(III) byte-canônico**: auto-apply opt-in (default = hoje, D1-D9=1523B intacto);
  detect-sem-aplicar byte-neutro (SideOutputs).

## Sub-hipóteses pro lab (ordem: barato→caro, medir antes de construir)
- **H1 (compressão, read-only)**: em colunas reais de ID formatado (CPF/CNPJ/IP — Receita,
  br-identidades), comparar bytes de: (a) `nature→OBAT→HCC` (atual), (b) `OBAT→HCC` puro
  (sem nature), (c) `OBAT→HCC` + nature-shrink nas refs/literais (tardio, onde aplicável).
  Pergunta: a base94 pré-OBAT está jogando fora estrutura? (b) vence (a) em algum caso?
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
