---
title: Rigor científico em pesquisa com LLMs locais
date: 2026-04-20
status: ACTIVE
audience: operadores do projeto TCF e futuros consumidores
---

# Rigor científico em pesquisa com LLMs locais

Este documento consolida a metodologia adotada (2026-04-20) após descobertas
que mostraram que várias "conclusões" anteriores estavam poluídas por
erros de setup, não por propriedades do formato TCF. Existe para que o
próximo ciclo de pesquisa não repita esses erros.

## 1. As três camadas de falha

Toda observação "X não funciona" precisa ser atribuída a UMA das três camadas:

```
[ Hardware/Infra ]  →  [ Modelo ]  →  [ Formato/Task ]
   RTX 3060 12GB,       bugs do próprio    O que estamos
   Ollama 0.21,         modelo em          pesquisando
   Docker config        edge cases         (TCF)
```

**Erro-padrão observado no TCF V0**: concluir sobre a 3ª camada sem isolar as
duas primeiras. Exemplos reais:
- "llama3.2:3b falha em q_count" → era bug isolado (não reproduzia em canônicas)
- "qwen3:0.6b com thinking é patológico" → era `think=False` incompatível em
  reasoning-native (não a capacidade do modelo)
- "deepseek-r1:7b fabrica respostas" → `think=False` força echo-loop;
  com thinking default acerta 5/5 em canônicas

## 2. Princípios operacionais

### 2.1 Qualification first
Antes de rodar experimentos de pesquisa (TCF) com qualquer modelo, ele
precisa **passar a qualification suite**
(`infra/model-qualification/`). Esta valida:
- Carregamento sem hang (<5min)
- Accuracy em perguntas canônicas (≥2/3 em 4 das 5 categorias)
- Latência característica documentada
- Zero exceptions sob flags corretos

A saída (`results/qualified_models.json`) é **single source of truth** para
todo script do projeto que escolhe modelos.

### 2.2 Replicação mínima
**N=1 não é conclusão.** Políticas:
- **Qualification**: N=3 seeds por pergunta (42, 7, 123). Critério para
  declarar "pass" = concordância em ≥2/3 seeds.
- **Findings científicos**: antes de reportar uma observação como
  fact (no paper ou notas), exigir:
  - N≥3 repetições sob mesma config
  - Validação em modelos adjacentes da família (ex: se X falha em 7B,
    testar 14B e 3B antes de concluir "X é ruim")

### 2.3 Respeitar thinking policy
Modelos dividem-se em 4 categorias segundo o catálogo em
`infra/model-qualification/model_thinking_catalog.json`:

| Categoria | Comportamento | Default flag |
|-----------|---------------|--------------|
| `none` | Sem thinking | `think` é ignorado |
| `toggle` | On/off independente | Configurável |
| `intrinsic` | Thinking é obrigatório | **NUNCA** `think=False` |
| `graded` | Níveis low/medium/high | `reasoning_effort` param |

**Nunca** definir `think=False` globalmente. Consultar o catálogo por modelo.

### 2.4 Investigar causalidade, não correlação
Antes de declarar "X causa Y":
- Controle: variar X fixando o resto, obter N≥5 amostras
- Confirmar: com X=False todos falham; com X=True todos passam
- Só então: "X causa Y"

Exemplo do deepseek-r1:7b: `think=False` × 5 seeds → **5/5 echo**;
`think=True` × 5 seeds → **5/5 "Brasília"**. Causalidade determinística.
Antes disso (1 observação), era só suspeita.

## 3. O que qualifica como evidência

### Fraca (não cita no paper):
- Observação única, sem replicação
- Comparação entre modelos com configs diferentes
- Conclusão baseada em 1-2 questões

### Moderada (pode citar com caveats):
- N=3+ com mesma config
- Padrão consistente em 2+ perguntas relacionadas
- Suportado por literatura publicada

### Forte (pode citar como fact):
- N=5+ sob controle rigoroso
- Reproduzível em múltiplos modelos/famílias
- Teoria causal identificável

## 4. Vieses conhecidos deste setup

### 4.1 PT vs EN (sem viés de accuracy, viés de cold-start)
Testado em 5 top performers × 7 canônicas × PT+EN = 70 calls:
- **Accuracy**: 100% idêntica em ambos
- **Response length**: equivalente
- **Latency**: primeira chamada PT é 20-60s mais lenta (cold-start da KV cache
  com tokens PT raros); subsequentes ficam equivalentes
- **Conclusão**: formato pode ser PT sem perda de qualidade

### 4.2 Linguistic interpretation
"Quantas palavras em 'A raposa marrom pula'?" → 4 (lexical) OU 3 (content
words, sem artigo). Ambas defensáveis. O scoring aceita ambas e anota qual
o modelo deu — sinaliza modelo "rigoroso" vs "lexical".

### 4.3 Multilingual ambiguity em prompts
"cores" em PT = colors OU CPU cores (multilingual confusion). Desambiguar
com exemplos ("como vermelho, azul") OU usar EN.

### 4.4 Vision encoder pode degradar text-only
- `llama3.2-vision:11b` — vision não degradou; performance text-only OK
- `qwen3-vl:8b` — **degradou severamente**; timeouts de 45-150s em prompts
  simples. **Não usar** para tarefas text-primary.

### 4.5 Reasoning models são sensíveis ao think flag
- DeepSeek-R1 é **intrinsic**: `think=False` quebra totalmente
- Qwen3 pequenos (0.6B/1.7B): thinking em CPU entra em loops patológicos
- phi4 (base): não tem reasoning; `think` é inócuo
- gpt-oss: thinking graded, usa `reasoning_effort`

### 4.6 Modelos obsoletos têm histórico confuso
`phi3, mistral:latest, qwen2.5:*, llama3.1:8b, gemma2:9b` são obsoletos
face aos sucessores modernos. **Não testar** em rodadas principais; apenas
manter para ablações históricas se necessárias.

## 5. Workflow recomendado

Para qualquer pesquisa nova envolvendo LLMs locais neste projeto:

```
1. python infra/model-qualification/qualify.py --audit-only
   └── Confirmar estado do ambiente

2. python infra/model-qualification/qualify.py (ou subset)
   └── Qualificar modelos novos / revalidar existentes

3. Consultar qualified_models.json para escolher panel
   └── NÃO hardcodar lista de modelos

4. Consultar model_thinking_catalog.json para flags corretos
   └── NUNCA setar think=False sem checar categoria

5. Rodar experimento com N≥3 seeds
   └── Registrar tudo em manifest JSONL

6. Validar findings com modelos adjacentes antes de concluir
   └── 1 observação = suspeita; N=3 mesmo modelo = moderada;
       N=3 em 2+ modelos similares = forte
```

## 6. Atualizações deste documento

- **2026-04-20 v1**: documento criado após descobertas da qualification suite
  V2.2 que invalidaram conclusões anteriores do TCF Phase 0/1/5.
- Próximas revisões: quando novos vieses forem identificados.
