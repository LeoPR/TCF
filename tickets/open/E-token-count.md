---
title: Contagem de tokens LLM — tiktoken + llama tokenizer real
type: experiment
status: OPEN
priority: HIGH
created: 2026-04-10
origin: Dimensao 3 de G-utility-analysis; TCF so conta chars, nao tokens reais
parent: G-utility-analysis
---

# Contagem de Tokens LLM

## Problema atual

Todos os nossos experimentos usam `prompt_chars` (numero de caracteres).
Mas LLMs cobram e processam por **tokens**, nao caracteres.

**Relacao char → token varia por formato:**
- Texto ingles: ~4 chars por token (tiktoken gpt-4)
- Codigo: ~3 chars por token
- Numeros: 1-3 chars por token
- Strings com sequencias repetidas: mais compressivel pelo BPE

TCF tem muitos caracteres especiais (`*`, `:`, `#`) que podem tokenizar
diferente de texto comum.

## Hipotese

**H-token:** O ganho real de TCF em tokens pode ser **menor** que o
ganho em chars, porque:
1. `3*Ana` pode virar 3 tokens (`3`, `*`, `Ana`) em tiktoken
2. Numeros com ponto decimal frequentemente viram 2-3 tokens cada
3. Linhas vazias e newlines sao 1 token cada

**TOON reporta 54% de reducao de tokens (medido com tiktoken).**
TCF precisa ser medido com o mesmo tokenizer para comparacao justa.

## Design

### Tokenizadores a usar

1. **tiktoken (OpenAI):** `cl100k_base` (GPT-4), `o200k_base` (GPT-4o)
2. **Llama tokenizer:** via `transformers` ou `llama-tokenizer-js`
3. **Gemma tokenizer:** via `transformers`
4. **Qwen tokenizer:** via `transformers`

Se muitas dependencias: comecar so com tiktoken (pip install tiktoken).

### Input

Mesmos dados de nossos experimentos:
- retail_sales(50, 200, 500, 1000, 5000)
- Formatos: CSV, JSON, JSONL, MD Table, TCF L0, L1, L2, L3, TOON

### Metricas

| Formato | chars | tokens GPT-4 | tokens Llama | tok/char ratio |
|---------|-------|--------------|--------------|----------------|
| CSV | 21449 | ? | ? | ? |
| JSONL | 60094 | ? | ? | ? |
| TCF L0 | 21653 | ? | ? | ? |
| TCF L2 | 19194 | ? | ? | ? |
| TCF L3 | 12170 | ? | ? | ? |
| TOON | ? | ? | ? | ? |

**Ratio esperado:** CSV ~4, JSONL ~4, TCF ~3.5 (mais caracteres especiais).
Se TCF tiver ratio baixo, o ganho em chars NAO se traduz em tokens.

## Impacto nos findings ja reportados

Todos nossos findings F30-F94 usam `prompt_chars`. Precisamos recalcular
com tokens para o paper.

**Risco:** se gap de tokens < gap de chars, alguns findings ficam mais
fracos.

**Oportunidade:** se gap de tokens > gap de chars (TCF tokeniza melhor
por ser regular), findings ficam mais fortes.

## Custo real em dolares

**Precos OpenAI gpt-4 (2026):**
- Input: $2.50 / 1M tokens
- Output: $10.00 / 1M tokens

**Cenario:** API que retorna 500 rows por request, 1M requests/mes.

Se TCF economiza X tokens por request:
- X * 1M = tokens salvos/mes
- Saving mensal = X * 1M / 1M * $2.50 = X * $2.50

**Exemplo:** se TCF economiza 1000 tokens/request vs JSON:
- 1000 * 1M = 1 bilhao de tokens/mes
- Saving = $2500/mes = $30K/ano

Isso justifica adoption. Se economia e 100 tokens/request → $3K/ano,
pode nao compensar switch cost.

## Relacao com outros tickets

- **G-utility-analysis**: dimensao 3
- **P-competing-formats**: comparar com TOON numeros oficiais
- **E-http-protocol**: input da analise de custo
- **P-rle-vs-gzip**: se RLE nao ajuda bytes, ajuda tokens?

## Tarefas

- [ ] Instalar tiktoken
- [ ] Implementar `tokenize_benchmark.py`
- [ ] Medir tokens para todos formatos × escalas
- [ ] Calcular token/char ratio por formato
- [ ] Comparar com numeros do TOON oficial (sanity check)
- [ ] Recalcular findings F30-F94 em termos de tokens
- [ ] Tabela de custo API mensal por formato
- [ ] Incluir no paper como secao "Real Token Economics"
