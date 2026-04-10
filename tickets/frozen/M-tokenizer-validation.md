---
title: Metodologia rigorosa de tokenizacao — groundtruth vs estimativa
type: methodology
status: OPEN
priority: CRITICAL
created: 2026-04-10
origin: Critica do usuario — TOON benchmarks sao parcialmente calculados, nao empiricos. Precisamos metodologia solida.
see_also: docs/research-notes/2026-04-10-critical-review.md
---

# Metodologia de Tokenizacao Rigorosa

## Problema

Muitos benchmarks comparando formatos para LLMs usam tokenizacao
**calculada** (tiktoken offline) em vez de **medida** (LLM real).
Isto inclui:

- **LogRocket TOON article:** so tiktoken, sem LLM real
- **TOON GitHub benchmarks:** parcialmente empiricos (accuracy medida),
  mas token counts nao especificam o tokenizer usado
- **Nosso TCF ate agora:** so `prompt_chars` (nem tokens)

O usuario questionou: **"Preciso de uma metrica muito solida pra ter
certeza absoluta que comprimir por coluna e uma boa estrategia."**

## Tres fontes de verdade para tokens

### Fonte 1: Ollama generate response (GROUND TRUTH real)

```python
response = client.generate(model="gemma3:12b", prompt=text, options={"num_predict": 1})
real_tokens = response["prompt_tokens"]  # do ollama_client, ja captura prompt_eval_count
```

**Vantagens:**
- Tokenizer do proprio modelo que vai processar
- Valor exato que o modelo cobraria (se fosse API paga)
- Ja disponivel no nosso `ollama_client.py`

**Desvantagens:**
- Requer 1 chamada LLM por medicao (~1-3s)
- So funciona para modelos instalados
- Nao e reproduzivel entre setups diferentes

**Status no codigo:**
- `ollama_client.py:54` JA captura via `prompt_eval_count`
- Runners (etapa1, etapa2, g30, etc) **nao gravam** no manifest
- **Correcao trivial:** adicionar `"prompt_tokens": gen["prompt_tokens"]`

### Fonte 2: transformers local (reprodutivel)

```python
from transformers import AutoTokenizer
tok = AutoTokenizer.from_pretrained("google/gemma-2-9b")
tokens = tok.encode("pessoa: Ana Bruno Carla")
count = len(tokens)  # offline, exato, gratis
```

**Vantagens:**
- Offline (sem Ollama rodando)
- Reprodutivel (mesma versao do tokenizer = mesmos tokens)
- Pode comparar dois formatos sem precisar LLM
- Gratis computacionalmente

**Desvantagens:**
- Requer `transformers` instalado (~500MB)
- Tokenizer HF pode diferir ligeiramente do usado pelo Ollama (GGUF)
- Alguns tokenizers (Llama) requerem autorizacao HF

**Tokenizers a usar:**
| Familia | HF model | Bytes |
|---------|----------|-------|
| Gemma3 | `google/gemma-2-9b` | ~2MB |
| Qwen3 | `Qwen/Qwen2.5-7B` | ~10MB |
| Llama3 | `meta-llama/Llama-3.1-8B` | requer acesso |
| Phi4 | `microsoft/phi-4` | ~2MB |

### Fonte 3: tiktoken (benchmark de comparacao com TOON)

```python
import tiktoken
enc = tiktoken.encoding_for_model("gpt-4")
tokens = enc.encode("pessoa: Ana Bruno Carla")
count = len(tokens)
```

**Vantagens:**
- Padrao da industria para GPT-4/OpenAI
- Mesmo tokenizer que TOON usa em benchmarks oficiais
- Offline, gratis
- Permite comparacao apples-to-apples com TOON

**Desvantagens:**
- Nao representa modelos que USAMOS (open source)
- Pode dar resultados muito diferentes de gemma/qwen
- Mas e essencial para comparar com TOON

## Metodologia proposta

### Principio: TRES medidas por combo

Para cada medida de tokens que reportarmos no paper, fornecer:

1. **Tokens REAIS (do modelo):** `prompt_eval_count` do ollama
2. **Tokens offline (reprodutivel):** transformers tokenizer da mesma familia
3. **Tokens tiktoken (baseline):** GPT-4 tokenizer

**Validacao cruzada:** se os tres valores coincidem (ate 5% de diferenca),
o numero e solido. Se divergem > 10%, investigar.

### Protocolo para experimentos futuros

#### Etapa A: correcao trivial (hoje)

1. Editar runners para gravar `prompt_tokens`:
```python
result = {
    ...
    "prompt_chars": len(prompt),
    "prompt_tokens": gen["prompt_tokens"],  # NOVO
    ...
}
```

2. Commit + experimentos futuros ja terao dado.

#### Etapa B: re-medir manifests existentes (hoje/amanha)

Script offline que le cada manifest.jsonl, regenera o prompt usando
as mesmas configs, e mede tokens com:
- transformers (tokenizer da familia do modelo)
- tiktoken (como referencia)

E adiciona colunas `prompt_tokens_hf` e `prompt_tokens_gpt4` ao manifest.

**Nao requer re-rodar LLM** — so tokenizacao offline.

#### Etapa C: validacao cruzada (1h de compute)

Amostra de 20 combos. Para cada um:
1. Tokens reais (novo campo no manifest, futuro)
2. Tokens HF transformers (offline)
3. Tokens tiktoken (offline)

Gerar tabela de diferencas. Se HF ~ real (< 5%), HF e bom proxy.
Entao podemos usar HF para re-medir manifests historicos com confianca.

#### Etapa D: paper cita TRES numeros

Na tabela de resultados:
```
Format  | chars | tokens (model) | tokens (tiktoken) | ratio |
TCF L0  | 21653 |          5342  |             5720  |  1.06 |
CSV     | 21449 |          5298  |             5621  |  1.06 |
JSONL   | 60094 |         14820  |            15180  |  1.02 |
TOON    |     ? |             ?  |                ?  |     ? |
```

Leitor ve que numeros sao consistentes entre tokenizers, aumenta confianca.

## Experimento de validacao (curto)

**Dataset:** retail_sales(200) → 509 vendas
**Formatos:** CSV, JSONL, TCF L0/L2/L3, TOON (quando implementado)
**Tokenizers:**
- Gemma3 via Ollama (real)
- Gemma3 via transformers (offline)
- GPT-4 via tiktoken (referencia)

**Saida:** tabela 6 formatos × 3 tokenizers = 18 celulas + validacao
cruzada.

Se os 3 tokenizers concordam na direcao (TCF menor que CSV, ou maior,
ou empate), o resultado e solido e publicavel.

## Resposta honesta para o usuario

A critica do usuario e **metodologicamente correta**. Temos ate agora:

1. **Chars** (o que reportamos) — **fraco** para comparacao com TOON
2. **Tokens via Ollama** — **disponivel mas nao usado** (trivial de corrigir)
3. **Tiktoken offline** — **nao instalado** (1 comando)
4. **HF transformers** — **nao instalado** (dependencia maior)

Nossa metodologia ate agora era fraca na dimensao "tokens". Vamos
corrigir. Resultado sera tabela com TRES fontes de verdade, permitindo
validacao cruzada.

## Tarefas

- [ ] Editar todos os runners (etapa1, etapa2, g30, diagnostic, stats, scale)
      para gravar `prompt_tokens`
- [ ] Testar que o dado aparece corretamente em manifest novo
- [ ] Instalar tiktoken (`pip install tiktoken`)
- [ ] Script `retoken_manifest.py` que le manifest, regenera prompts,
      e adiciona tokens tiktoken
- [ ] Opcionalmente: instalar transformers e tokenizer gemma3
- [ ] Rodar validacao cruzada em amostra de 20 combos
- [ ] Documentar metodologia no paper (secao Methodology)
- [ ] Re-rodar plots F30-F89 com tokens em vez de chars onde faz sentido

## Relacao com outros tickets

- **E-token-count:** este ticket e a METODOLOGIA; E-token-count e o EXPERIMENTO
- **P-competing-formats:** precisa de tokens reais para comparar TOON honestamente
- **H-token-friendly-format:** otimizar formato requer medir tokens
- **G-utility-analysis:** dimensao 3 (tokens) desta analise
