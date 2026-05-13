---
title: Formato token-friendly — otimizar TCF para BPE tokenizers
type: hypothesis
status: OPEN
priority: HIGH
created: 2026-04-10
origin: TOON mostra que otimizar PARA tokens (nao chars) pode dar 54% de economia
see_also: docs/research-notes/2026-04-10-compression-tokens-streaming.md
---

# Formato Token-Friendly

## Motivacao

TOON consegue **54% de reducao de tokens** vs JSON nao por ser columnar
(nao e), mas por ter sido **otimizado empiricamente para BPE tokenizers**
(especificamente tiktoken do GPT-4).

Nosso TCF foi otimizado para **caracteres**, nao tokens. Podemos estar
deixando economia na mesa porque:
- `3*Ana` pode virar 3 tokens (nao 1)
- Newlines no inicio de cada coluna sao tokens extras
- Caracteres especiais (`#`, `*`, `:`) frequentemente sao 1 token cada

## Pergunta central

**Existe uma variante do TCF que seja token-friendly em tiktoken cl100k_base
(GPT-4) sem sacrificar legibilidade humana ou ratio de caracteres?**

## Hipoteses especificas

### H-tk-1: Delimitador de linha impacta tokenizacao

Atual TCF usa `\n` entre valores. Cada `\n` e tipicamente 1 token.

Alternativas:
- Space separation: `Ana Bruno Carla` em vez de `Ana\nBruno\nCarla`
- Semicolon: `Ana;Bruno;Carla`
- Comma (CSV-like): `Ana,Bruno,Carla`

**Teste:** tokenizar mesma lista com cada delimitador. Qual ganha?

**Risco:** separadores diferentes podem confundir a detecao de runs RLE.

### H-tk-2: Notacao RLE alternativa

Atual: `3*Ana`
Alternativas:
- `Ana x3` (x minusculo e palavra comum em ingles, pode ser 1 token)
- `Ana(3)` (parenteses sao token unicos)
- `3Ana` (sem separador — nao e legivel)
- `Ana*3` (inversao — nao ajuda muito)

**Teste:** qual tokeniza melhor em GPT-4? Em Llama? Em Qwen?

### H-tk-3: Column headers mais curtos

Atual: `pessoa:\n`
Alternativas:
- `p:` (1 char + colon)
- `#p` (hashtag + char)
- `[pessoa]` (brackets — unicos?)

Pequenos ganhos que podem se acumular em muitas colunas.

**Risco:** perde legibilidade humana.

### H-tk-4: STATS inline em vez de separado

Atual:
```
## vendas n=509 sorted_by=pessoa
# STATS total: n=509 sum=147445.47 min=9.01 max=759.8 avg=289.68
# STATS qtd: n=509 sum=2767 ...
```

Alternativa:
```
## vendas n=509 stats=total:sum=147445.47,min=9.01,max=759.8;qtd:sum=2767
```

Uma linha em vez de varias. Menos newlines, potencialmente menos tokens.

### H-tk-5: Valores numericos normalizados

Atual: `147445.47`
Alternativa: `147445` (inteiro) com factor declarado no header
```
## vendas n=509 precision=total:2
...
total:
14744547  # representa 147445.47
```

Numeros inteiros tokenizam mais consistentemente que floats.
Relaciona-se com **H-smart-rounding**.

### H-tk-6: Column order baseado em tokens

Dentro de uma coluna, alguns valores tokenizam melhor que outros.
Ordenar pela ordem alfabetica pode ser melhor ou pior que ordem de
frequencia.

**Teste:** duas orderings do mesmo dado → qual tem menos tokens?

## Estrategia de otimizacao empirica

Ao inves de adivinhar, rodar um **search** sobre variantes:

1. Definir 10-20 variantes do formato (combinacoes das hipoteses acima)
2. Gerar retail_sales(500) em cada variante
3. Tokenizar com tiktoken (cl100k_base, o200k_base)
4. Tokenizar com llama tokenizer (se disponivel)
5. Medir tokens/row para cada variante × tokenizer
6. Identificar a variante minima e a variante mais consistente
   cross-tokenizer

## Implementacao

Nao modificar encoder principal. Criar `variants.py`:

```python
from tcf.variants import encode_token_optimized

text = encode_token_optimized(
    meta, data,
    delimiter="space",      # H-tk-1
    rle_notation="x_suffix",  # H-tk-2
    short_headers=True,     # H-tk-3
    stats_inline=True,      # H-tk-4
    scale_integers=True,    # H-tk-5
)
```

## Relacao com outros tickets

- **E-token-count:** este ticket e a aplicacao — gera variantes, E-token-count mede
- **H-smart-rounding:** inteiros escalados ajudam ambos
- **P-competing-formats:** comparacao final com TOON no mesmo eixo
- **T-multi-lang:** variantes complicam decoders cross-language

## Caveat importante

Otimizar para tiktoken pode **piorar** em outros tokenizers:
- GPT-4 tem vocabulario diferente de Llama
- Qwen tokeniza chinês melhor que ingles
- Gemma tem vocab maior que GPT-4

**Decisao:** otimizar para o conjunto maior dos modelos que usamos no
benchmark (qwen3, gemma3, phi4, llama3.2, gpt-oss). Reportar variancia
por tokenizer.

## Risco: TCF pode perder identidade

Se otimizarmos demais para tokens, TCF pode virar "um TOON columnar"
sem identidade propria. **Equilibrio:** manter legibilidade humana
como restricao dura. Se variante X economiza 20% tokens mas e
ilegivel, rejeitar.

## Tarefas

- [ ] Implementar 6 variantes em `src/tcf/variants.py`
- [ ] Implementar tokenizacao com tiktoken
- [ ] Rodar grid: 6 variantes × 3 tokenizers × 3 escalas
- [ ] Tabela de tokens/row por variante
- [ ] Eleger variante otima (ou combinacao)
- [ ] Testar accuracy LLM da variante otima (nao pode piorar vs L2 atual)
- [ ] Se nao pior em accuracy e melhor em tokens: adotar como L2-token
- [ ] Documentar em paper como "empirical tokenizer optimization"
