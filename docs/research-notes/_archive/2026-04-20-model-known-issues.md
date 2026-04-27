---
title: Known model issues — bugs e comportamentos anômalos observados
date: 2026-04-20
type: research-note
status: OPEN
related:
  - experiments/results/frontier_search/manifest.jsonl
  - docs/research-notes/2026-04-18-cpu-bench-findings.md
  - tickets/frozen/P-G35-modelos-llm.md
---

# Known model issues

Problemas reproduzíveis observados durante Phase 0/1 do frontier search.
Objetivo: registrar para não repetir investigações + sinalizar casos que
não devem entrar no dataset principal sem caveat.

## llama3.2:3b — loop de geração em q_count L3 (specific prompt)

**Sintoma**: request `/api/generate` com prompt L3 + system L3 + pergunta q_count
(`"Quantas linhas existem nos dados? Responda apenas com um numero inteiro."`)
trava em estado de geração ativa (GPU 89-91% util, CPU runner 122%) por
mais de 2h sem retornar resposta. Timeout no client (7200s) é a única
forma de interromper.

**Reprodução** (2 vezes, 2026-04-19 e 2026-04-20):
- Model: `llama3.2:latest` (3.2B, Q4_K_M, family=llama)
- Backend: Ollama 0.21 em Docker (GPU RTX 3060, também em CPU-only)
- Prompt: ~900 tokens (n_orders=50 L3 integer), Portuguese system prompt
- Options: temperature=0, seed=42, keep_alive=30m, think=False

**O que NÃO é**:
- Não é thinking (think=False explícito, modelo nem suporta thinking)
- Não é timeout de rede (Ollama runner processa ativamente)
- Não é OOM (VRAM estável em 6.3GB, modelo fits easy)
- Não é context overflow (prompt ~900 tokens, KV cache 8K+)
- Não é servidor morto (responde outras requests normalmente)

**Outras perguntas do mesmo modelo respondem em 2-3s**:
- q_top_product OK ans='Grampeador'
- q_distinct OK "Para responder a essa pergunta..."
- q_lookup NO ans='O cliente...'
- q_lookup_value OK

**Hipótese**: geração degenerada (repetitive sampling state) disparada por
combinação específica do prompt q_count com o formato L3. llama3.2:3b é
sabidamente mais sensível a prompts estruturados que modelos maiores.

**Ação tomada**: marcar como known-bug permanente. `q_count` de `llama3.2:3b`
não entra no dataset. Os outros 4 scores (4/5 = 80%) são válidos.

**Ablation futura**: testar se o bug reproduz com:
- llama3.1:8b (mesmo bug?) — NÃO testado ainda
- llama3.2:1b (versão menor) — NÃO testado
- Mesmo prompt em CSV/JSONL (é específico do L3?) — NÃO testado

## Padrões anômalos (não-bugs, mas relevantes)

### Modelos verbose que respondem "certo mas longo"

Alguns modelos ignoram `"Responda apenas com um numero inteiro"` e começam
com explicação. Exemplos:
- **phi4:latest**: sempre começa com `"Para determinar o numero de linhas..."`
- **deepseek-r1:14b**: mesmo padrão `"Para determinar quantas..."`

Não é bug: o scoring via `extract_number()` pega o número na resposta,
então verbose + certo = OK. Mas aumenta token count/latency.

### qwen3 família — frequency heuristic em q_lookup

qwen3:0.6b/1.7b/8b/14b respondem "Rodrigo" em q_lookup (a maioria dos seeds)
sem realmente fazer o join max(total) → id_cliente → nome. Evidência:
q_lookup_value (numeric) falha enquanto q_lookup (name) "acerta".

Interpretação: modelo vê que Rodrigo é o cliente mais frequente e chuta.
Confound documentado pelo nosso q_lookup_value disambiguator (Phase 1 data).

### qwen3:8b/14b — aritmética sem join

Caso especial: **acham** o valor max correto em q_lookup_value (760.91)
mas **não** conseguem relacionar com id_cliente em q_lookup (respondem
"Isabela" ao invés de "Rodrigo"). Mostra capability gap:
max-extraction OK, cross-column join falha.

### gemma3:12b — regressão vs histórico

P-G35 documentou como "MELHOR (88% TCF L0)", mas em Phase 1 L3
(n_orders=50) obteve 20% (1/5). Hipótese: L3 dict+int indices são menos
amigáveis para gemma3:12b que L0 textual direto. Diferença entre nível
L0 vs L3 pode ser o fator dominante, não o modelo.

### llama3.2-vision:11b < llama3.2:3b em parsing estruturado

**Achado contra-intuitivo**: o variante multimodal 11B (base llama + vision
encoder via cross-attention, família `mllama`) obteve **40% (2/5)** em
Phase 1 L3 integer, enquanto o llama3.2:3b puro obteve **60% (3/5 das
questões não-bug)**. O modelo maior e mais recente é pior.

Perguntas:
- q_count: 35 (esperado 115) — não lê header corretamente
- q_top_product: "Livro" — chute não-informado
- q_distinct: 5 ✓ (verbose mas correto)
- q_lookup: "Vitoria" — nem frequency-heuristic acertou (esperado Rodrigo)
- q_lookup_value: correto ✓

**Hipótese**: adicionar o vision encoder + cross-attention (fine-tuning
multimodal) degradou capacidade de parsing estruturado em texto. O modelo
foi treinado pra integrar tokens visuais, o que pode ter interferido com
representações internas de estrutura textual compacta (L3 dict+RLE).

**Implicação**: família Llama é fraca pra TCF parsing, e vision não
melhora. Nenhum Llama testado atinge tier 1 (100%). Top performers
(phi4, deepseek-r1, gpt-oss) são não-Llama.

### gemma2:9b — incompatibilidade com TCF persistente

F53 histórico (archive_v01): "0% em TCF E2". Phase 0 atual: 0% (0/2 em
L3 integer). Phase 1: 60% surpreendente (3/5) — mas q_count errado (100
em vez de 115) e q_lookup_value errado (77.77 em vez de 760.91). Os
acertos são q_top_product, q_distinct, q_lookup — os dois últimos
respondidos com heuristic de frequência.

Mantém status "unstable" — não incluir no dataset primário sem caveat.
