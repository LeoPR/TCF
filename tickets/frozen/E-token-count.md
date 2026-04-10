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

## Por que tokens e nao chars — razoes concretas

### 1. Cobranca real e em tokens
OpenAI GPT-4: $2.50/1M **tokens** input. Se medimos em chars, nao temos
como estimar custo real. Uma economia de 30% em chars pode ser apenas
15% em tokens — ou 45%, dependendo do formato.

### 2. BPE agrupa de forma nao-linear
Byte Pair Encoding pre-computa merges de pares frequentes durante o
treinamento do tokenizer. Consequencias:
- Palavras comuns em ingles: **1 token**
- `Ana`, `Bruno`, `Carla`: provavelmente **1 token cada** (nomes comuns)
- `2.50`: **2-3 tokens** (`2`, `.`, `50` ou `2.5`, `0`)
- `3*Ana`: **3 tokens** (`3`, `*`, `Ana`) — pior que esperado
- `# STATS total: n=509`: **~8 tokens** — tokens de marcacao sao caros
- `8*Ana\n12*Bruno`: pode tokenizar melhor que `Ana\nAna\nAna\n...` **OU PIOR**

### 3. Contexto e medido em tokens
`num_ctx=4096` = 4096 tokens, nao caracteres. Quando dizemos que "TCF
cabe no contexto a 200 rows", isso precisa ser verificado em tokens
reais para cada tokenizer (GPT vs Llama vs Gemma).

### 4. Cada familia de modelo usa tokenizer diferente
- **GPT-4/GPT-4o:** tiktoken `cl100k_base` / `o200k_base`
- **Llama 2/3:** SentencePiece com vocab de 32K
- **Gemma:** SentencePiece com vocab de 256K
- **Qwen:** tokenizer proprio com vocab ~150K
- **Phi:** tiktoken adaptado

Mesmo texto → contagens diferentes. Um formato pode ser otimo em GPT
e ruim em Llama. **Nao ha um "numero universal de tokens"**.

### 5. Caracteres especiais tokenizam mal
TCF usa `*`, `#`, `:`, `\n` com frequencia. Muitos tokenizers nao
aprenderam merges para essas sequencias → 1 token por caractere.
CSV usa principalmente `,` e `\n` — padroes super comuns, super
otimizados no BPE.

**Possivel resultado:** CSV pode ter ratio token/char melhor que TCF,
anulando parte da compressao textual.

### 6. Numeros sao instaveis
Numeros podem tokenizar como:
- 1 token (inteiros pequenos: `1`, `2`, `100`)
- 2-3 tokens (floats: `2`, `.`, `5`)
- 4+ tokens (numeros grandes: `147`, `445`, `.`, `47`)

E aqui e o ponto critico: `147445.47` vira muitos tokens mesmo
sendo so 9 chars. Se TCF tem valores numericos grandes em STATS,
paga caro em tokens.

## Riscos concretos para findings F30-F94

Todos nossos findings usam `prompt_chars`. Quando medirmos em tokens:

| Finding | Risco | Por que |
|---------|-------|---------|
| F30-F34 (escala) | Baixo | Gap e grande (62% vs 12%) |
| F50 (TCF 2.5x CSV) | **Medio** | Pode reduzir gap |
| F70-F73 (transport) | Baixo | gzip ja passa por bytes, nao tokens |
| F85-F89 (scale curve) | **Alto** | Numeros exatos de crossover mudam |
| F90-F94 (STATS) | Baixo | Comparacao interna (mesmo formato) |

**Possibilidades invertidas (TCF pode ganhar mais):**
- Se `3*Ana` tokenizar bem (nomes repetidos comprimem), TCF ganha
- Se L3 dict (`# dict pessoa: Ana,Bruno,Carla`) tokenizar eficientemente
- Se as linhas curtas do TCF tokenizarem melhor que as longas do JSONL

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
