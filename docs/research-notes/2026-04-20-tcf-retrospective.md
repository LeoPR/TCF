---
title: Retrospectiva crítica — TCF Phases 0/1/5 sob óptica da qualification
date: 2026-04-20
type: research-note
status: RETROSPECTIVE
related:
  - docs/methodology/llm-research-rigor.md
  - docs/research-notes/2026-04-20-qualification-findings.md
  - experiments/results/frontier_search/manifest.jsonl
  - infra/model-qualification/results/qualified_models.json
---

# Retrospectiva crítica — Phase 0/1/5 do TCF

Depois de construir a qualification suite e descobrir vários vieses
(ver `2026-04-20-qualification-findings.md`), este documento faz um
inventário crítico do que rodamos no TCF, identificando:
1. **Conclusões que se mantêm válidas**
2. **Conclusões que estavam poluídas** (precisam invalidar)
3. **Dados que precisam ser re-rodados** (identificar novos findings)
4. **Dados que ficam como histórico/contexto** (não re-rodar)

## Escopo do que foi rodado

### Phase 0 (Pilot)
- 13 modelos × 2 perguntas (q_count, q_top_product) em n_orders=20 L3 integer
- Flags: `--cpu-only --num-thread 12 --no-think`
- Output: ranking por pass/fail canário

### Phase 1 (Model sweep)
- 14 modelos × 5 perguntas (q_count, q_top_product, q_distinct, q_lookup, q_lookup_value)
  em n_orders=50 L3 integer
- Flags: `--num-thread 12 --no-think` (GPU)
- Output: ranking detalhado; identificou tier "100% = phi4/deepseek-r1:14b/gpt-oss"

### Phase 5 (Thinking ablation) — ABORTADO
- 6 thinking-capable × 5 perguntas com `think=ON` (default)
- Flags: `--cpu-only --num-thread 12` sem `--no-think`
- Abortado após 7/30 combos (qwen3 pequenos travando 95min por call)
- Dados parciais de qwen3:0.6b (5/5) e qwen3:1.7b (1/5)

## Análise por fase

### Phase 0 — veredicto: **parcialmente válida**

**Válido** (mantém):
- Capacity floor observado: qwen3:0.6b responde mal L3 (consistente com
  qualification F-Q5 — abaixo do threshold para factual recall complexo)
- Tiers dos top-performers (phi4, deepseek-r1:14b, gpt-oss em 100%) —
  consistente com a tier-hierarchy identificada

**Invalidado** (precisa re-rodar):
- Scores de `deepseek-r1:14b` e `gpt-oss` em Phase 0 são **subestimados**
  porque rodaram com `--no-think`. Para deepseek-r1 (intrinsic), o
  comportamento com think desativado é artificial.
- Especificamente: deepseek-r1:14b teve 100% em Phase 0 **apesar** do
  `--no-think` — indica que o 14B tolera, mas o 7B (nunca testado no TCF)
  provavelmente falharia.

**Ação**: re-rodar Phase 0 usando o catálogo de thinking (thinking default
por modelo, não global). Esperativa: deepseek-r1:7b qualificará; 14B
mantém; outros sem mudança.

### Phase 1 — veredicto: **parcialmente válida, mais solida que Phase 0**

**Válido** (mantém):
- Top 3 (phi4 / deepseek-r1:14b / gpt-oss) = 100%: sólido, N=5 perguntas,
  consistente com qualification que confirma os 3 como modelos estáveis
- qwen3:8b = 40% (4 pontos abaixo de onde capacity sugeriria): pode ser
  formato L3 fazendo mismatch, consistente com nossa hipótese de que L3
  exige capacity **além** do canonical
- qwen3:14b = 60% (não 100%): canonical mostra 5/5, mas TCF mostra 3/5 —
  o gap TCF vs canonical indica **L3 é o limitador**, não o modelo
- gemma2:9b = 60% (surpresa positiva mas obsoleto): descartar como signal
  ambíguo

**Potencialmente invalidado** (re-verificar):
- deepseek-r1:14b Phase 1 = 100% (5/5) com `--no-think` é legítimo, MAS
  deepseek-r1:7b (não testado) agora qualifica canonical — vale adicionar
- qwen3 família (0.6b-14b) testada com `--no-think` — qualification mostra
  que estes são **toggle-capable** (podem ligar/desligar thinking), então
  `--no-think` é válido, não incorreto. Mantém.
- Entretanto: **thinking ON pode elevar scores** de qwen3:8b (40%) e
  qwen3:14b (60%) — ablation planejada em Phase 5 foi abortada

**Ação**: (a) adicionar deepseek-r1:7b em Phase 1 para completar painel;
(b) Phase 5 rebooted com qualification-aware settings.

### Phase 5 — veredicto: **invalidada, precisa refazer**

**Problemas identificados**:
1. Rodou em CPU com 12 threads — thinking em small qwen3 = 95min/call patológico
2. `qwen3:0.6b` não é qualificado — não deveria estar no painel de qualquer forma
3. Dados parciais só do 0.6b (5/5 completos) e 1.7b (1/5) não cobrem os casos
   interessantes (qwen3:8b/14b, deepseek-r1:14b, gpt-oss)

**Ação**: refazer Phase 5 com:
- **GPU** (não CPU)
- **Apenas qualified thinking-capable**: qwen3:1.7b, qwen3:8b, qwen3:14b,
  deepseek-r1:7b, deepseek-r1:14b, gpt-oss:latest
- **Thinking default per catálogo** (intrinsic: None; toggle: True;
  graded: "medium")
- Expected runtime em GPU: 6 modelos × 5 perguntas × ~1-3min = 30-90min

## Outros resultados pré-TCF (archive_v01)

Nos tickets e docs antigos existem referências como:
- F51: "gemma3:12b é o melhor modelo (88% em TCF L0)"
- F53: "gemma2:9b 0% em TCF E2"

Estes foram em **TCF L0** (não L3) e usando protocolos antigos. A qualification
atual mostra:
- gemma3:12b: 5/5 canonical (capacity boa), 20% em TCF Phase 1 L3 (capacity
  boa **para L0** mas L3 é hostil)
- gemma2:9b: 4/5 canonical com tolerance (mas é obsoleto, descartar)

**Conclusão**: findings antigos eram em nível L0 e continuam válidos para L0.
Phase 1 L3 é um regime diferente — hipótese reforçada: **o nível TCF (L0 vs
L3) é variável tão importante quanto o modelo**.

## Ações consolidadas

### Curto prazo (próximo sprint)

1. **Re-rodar Phase 0** com qualification (12 modelos corretos + thinking
   policy do catálogo). **Esperado**: ~15-20min GPU.
2. **Expandir Phase 1** para incluir deepseek-r1:7b (não testado antes).
   **Esperado**: ~10-15min (só o 7b).
3. **Re-rodar Phase 5** com GPU + thinking-capable qualified subset.
   **Esperado**: 30-90min.
4. **Re-baseline das conclusões**: após re-runs, consolidar nova tabela de
   rankings em `docs/research-notes/2026-04-20-tcf-rerun-results.md`.

### Médio prazo

5. **Phase 2 (data sweep)** com pilot correto (provavelmente phi4 ou 
   gpt-oss) — testar n-boundary real.
6. **Phase 3 (notation sweep)** incluindo `N:val` e variantes.
7. **Phase 4 (task sweep)** full questions.

### Não re-rodar

- Canonical tests (qualification já é suficiente)
- Obsoletos (phi3, mistral, qwen2.5:*, llama3.1:8b, gemma2:9b, qwen2.5-coder)
- qwen3-vl:8b (não-qualificado por instabilidade text-only)

## Mudança cultural

Antes de 2026-04-20, fizemos 3 iterações do frontier search declarando
findings em 1-2 observações. Isso precisa mudar:

- **Todo finding novo**: só entra em documentos/artigo após N≥3 replicação
- **Toda falha de modelo**: investigação de camada (hardware/infra/modelo) antes
  de concluir sobre formato
- **Todo prompt**: testado contra canonical antes de medir TCF

Ver `docs/methodology/llm-research-rigor.md` para o framework permanente.
