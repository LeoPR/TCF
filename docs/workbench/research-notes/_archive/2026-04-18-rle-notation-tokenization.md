---
title: Tokenização empírica de notações RLE — achado do separador-espaço
date: 2026-04-18
type: research-note
status: FINDINGS
related:
  - docs/research-notes/2026-04-15-compression-tokenization-strategy.md
  - tickets/open/H-advanced-compression-v03.md
---

# Tokenização empírica de notações RLE

## Contexto

A nota de 2026-04-15 concluiu que todas as notações RLE custam "o mesmo"
(4 tokens), medindo apenas `3*Ana` com newline. Esta nota estende o teste
a todas as combinações razoáveis de separador × tipo de valor × tamanho.

Tokenizer: `tiktoken cl100k_base` (GPT-4/3.5). Ver caveat no final.

## Achado principal — separador-espaço vence em strings

Em coluna de strings, `N val` (espaço) é 25-40% mais barato que `N*val`.

```
Nome         N*val   N val   diff
"Ana"           4       3    -25%
"Alice"         4       3    -25%
"Alexandre"     5       3    -40%
"ITEM_001"      6       5    -17%
"São Paulo"     5       4    -20%
"new-york"      6       5    -17%
```

**Mecanismo BPE**: o merge "Ana" aparece no corpus sem espaço-prefixo
quando precedido por separador non-word (`*`, `x`), mas quando precedido
por espaço o tokenizer merge para " Ana" (token único com leading space),
economizando 1 token por run.

## Em valores numéricos — empate total

Para colunas numéricas todos os separadores ficam iguais:

```
Valor          3*val  3 val  3xval
"42"             4      4      4
"3.14"           6      6      6
"12345.67"       7      7      7
"100000"         5      5      5
```

O tokenizer sempre divide `1234` em `[1, 234]` ou `[123, 4]`, e a fronteira
prévia (separador) não muda isso.

## Impacto real no TCF

Decomposição das colunas típicas:

| Nível TCF | Colunas strings | Colunas numéricas |
|-----------|----------------|-------------------|
| L0-L2 | RLE em strings | RLE em números |
| L3 (dict) | RLE em índices int | RLE em números |

- **L1/L2**: tem colunas string com RLE — aqui `N val` economiza 25-40%
- **L3**: strings viram índices int, volta ao empate numérico

Então o ganho real de trocar `N*val` por `N val` é:
- **Significativo em L1/L2** (quando há colunas string com repetição)
- **Nulo em L3** (dict já fez o trabalho)

Em nosso benchmark L3 atual (que é o melhor) isso não muda nada.
Em L1/L2 pode dar +10 a +20% de ganho em tokens.

## Notações testadas — ranking completo

```
nome "Ana", newline terminal:

 notação     tokens   decomposição
 N val          3     ['3', ' Ana', '\n']
 N*val          4     ['3', '*', 'Ana', '\n']
 Nxval          4     ['3', 'x', 'Ana', '\n']
 N xval         4     ['3', 'x', ' Ana', '\n']
 val xN         4     ['Ana', ' x', '3', '\n']
 val*N          4     ['Ana', '*', '3', '\n']
 val(N)         5     ['Ana', '(', '3', ')', '\n']
 (N)val         5     ['(', '3', ')', 'Ana', '\n']
 N-val          5     ['3', '-An', 'a', '\n'] # dash quebra o nome!
```

Nota: separador dash (`-`) é o pior — quebra o merge do nome em 2 tokens.

## Conflito: token-barato vs cognitivamente-claro

`N val` (espaço) é o mais barato em tokens, mas:
- **Ambíguo**: "3 Ana" pode ser lido como "3 coisas chamadas Ana" OU
  como um par "3, Ana" sem relação.
- **Sem marcador explícito**: LLMs podem confundir com dados tabulares
  normais de duas colunas.

`N*val` (atual) tem:
- Marcador claro (`*` = multiplicação)
- Risco de ambiguidade com literais matemáticos em textos (`3*4`)

`N xval` tem:
- `x` = "vezes" natural em inglês ("3x speedup")
- Separador visível
- Mesmo custo que `N*val` (4 tokens)

## Proposta para TCF v0.3

**Não mudar o default.** `N*val` tem um histórico de 3 meses de experimentos
— mudar agora invalida comparações. Mas:

1. **Adicionar `EncodeConfig.rle_notation: str = 'N*val'`** (default mantido)
2. **Suportar `'N val'`, `'N xval'`, `'val xN'`** como alternativas
3. **Testar cognitive cost** com `gemma3:4b`, `qwen2.5:7b`, `qwen2.5-coder:7b`
   quando GPU liberar — mesmo dataset, mesmas perguntas, 4 notações
4. **Documentar**: se alguma notação for significativamente melhor em
   accuracy, tornar default; senão manter `N*val` e oferecer escolha

## Teste pendente (GPU ocupada)

Script preparado: `experiments/rle_notation/micro_bench.py`

Design:
- 3 modelos: `gemma3:4b`, `qwen2.5:7b`, `qwen2.5-coder:7b`
- 4 notações: `N*val`, `N val`, `N xval`, `val xN`
- 3 perguntas factual sobre dados com RLE
- 36 combos, ~1h estimado (sem thinking mode)

## Caveat — tokenizer diferente

`tiktoken cl100k_base` = GPT-4/3.5. Gemma/Qwen usam tokenizers próprios
(SentencePiece/BBPE). O padrão "espaço-prefixo vira token único" é geral
em BPE, então os **rankings** relativos devem se manter, mas os **valores
absolutos** podem variar ±10%.

Para confirmar no tokenizer do Qwen, seria preciso instalar `transformers`
e carregar só o tokenizer (CPU, sem GPU) — deferido para quando necessário.

## Conexão com achado anterior

A nota de 2026-04-15 afirmou "+1 token para STATS CI". Re-medindo com
tiktoken, o custo real é:

- Verbose (`err=7.8% full_n=48842`): **+10 tokens** por STATS line
- Compact (`avg=49.5~8%`): **+3 tokens** por STATS line

Correção já refletida no commit 53d2fbe que implementou o feature.
