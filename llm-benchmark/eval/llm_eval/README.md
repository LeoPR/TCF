# Avaliação de Formatos de Dados para LLM

Este módulo executa testes de avaliação sobre pedaços (chunks) de dados tabulares em diferentes formatos (CSV, JSONL, TOON, etc.) enviando perguntas simples para modelos locais via Ollama (`/api/generate`). O objetivo é comparar impacto do formato na precisão, latência e tamanho do prompt.

## Método

1. Carregamos `consolidated.json` para obter linhas tabulares.
2. Dividimos em *chunks* de N linhas (`rows_per_chunk`).
3. Para cada chunk renderizamos o bloco de dados em um formato escolhido (`format_name`).
4. Construímos um prompt padronizado: bloco SYSTEM + CONTEXT (dados) + USER (pergunta).
5. Enviamos via POST para `OllamaClient.generate` com `stream=false`.
6. Registramos: resposta, latência, caracteres do prompt, formato e tamanho do chunk.
7. Computamos métricas: acurácia (comparando com gabarito), latência média, tamanho médio do prompt e score composto.

### Perguntas atualmente suportadas
- `count_rows`: número de linhas do chunk.
- `sum_field`: soma numérica de um campo (`--sum-field`).
Outras definidas mas ainda não ativadas no runner: `avg_field`, `category_count`.

## Estrutura do Prompt

Exemplo (TOON + pergunta `count_rows`):

```
<s>SYSTEM> Você receberá dados no formato TOON ... Use a lista 'columns' para interpretar ...</s>
<s>CONTEXT>
# formato: TOON
# Token-Oriented Object Notation (TOON): formato compacto para dados tabulares.
# Arrays uniformes usam [N]{colunas} e linhas indentadas com valores separados por vírgula.
# Use apenas os dados abaixo, nada mais.
dados[5]{id,produto,vl}:
  1,Caneta,3.5
  2,Caderno,12.9
  3,Lapis,1.75
  4,Borracha,2.1
  5,Marcador,5.0
  ...
</s>
<s>USER> Quantas linhas existem no conjunto de dados? Responda apenas com um número inteiro.</s>
<s>ASSISTANT>
```

## Exemplos de Blocos de Dados por Formato (Truncados)

### TOON (Token-Oriented Object Notation)
```
# formato: TOON
# Token-Oriented Object Notation (TOON): formato compacto ...
# Arrays uniformes usam [N]{col1,col2,...}.
# Use apenas os dados abaixo, nada mais.
dados[5]{id,produto,vl}:
  1,Caneta,3.5
  2,Caderno,12.9
  3,Lapis,1.75
  4,Borracha,2.1
  5,Marcador,5.0
  ...
```

Características: evita repetição de chaves; cada linha vira apenas uma lista de valores.

### JSONL
```
# formato: JSONL
# Cada linha a seguir é um objeto JSON independente.
# Leia linha por linha sem misturar campos ...
# Use apenas os dados abaixo, nada mais.
{"id":1,"produto":"Caneta","vl":3.5}
{"id":2,"produto":"Caderno","vl":12.9}
{"id":3,"produto":"Lapis","vl":1.75}
{"id":4,"produto":"Borracha","vl":2.1}
{"id":5,"produto":"Marcador","vl":5.0}
[...]
```

Características: repetição de chaves por linha; mais tokens em modelos sensíveis a repetição.

### CSV
```
# formato: CSV
# A primeira linha contém os nomes das colunas.
# Cada linha subsequente representa um registro separado.
# Use apenas os dados abaixo, nada mais.
id,produto,vl
1,Caneta,3.5
2,Caderno,12.9
3,Lapis,1.75
4,Borracha,2.1
5,Marcador,5.0
...
```

Características: compacto para valores simples; precisa interpretação correta de separadores.

### Markdown (Apenas visual / não usado em testes principais)
```
# formato: MARKDOWN_TABLE
# Representação em tabela Markdown (uso principalmente visual).
# Pode haver perda de tipos para campos complexos.
# Use apenas os dados abaixo, nada mais.
|id|produto|vl|
|---|---|---|
|1|Caneta|3.5|
|2|Caderno|12.9|
|3|Lapis|1.75|
|4|Borracha|2.1|
|5|Marcador|5.0|
|...|...|...|
```

## Exemplo de Payload HTTP Enviado ao Modelo

```jsonc
POST /api/generate
{
  "model": "gemma3:12b",
  "prompt": "<s>SYSTEM> ... </s>\n<s>CONTEXT>\n# formato: TOON\n...\n</s>\n<s>USER> Quantas linhas existem ... </s>\n<s>ASSISTANT>",
  "stream": false,
  "options": {
    // opcional: temperature, top_p, etc.
  }
}
```

## Métricas
- `accuracy`: proporção de respostas corretas.
- `avg_latency_s`: latência média por pergunta.
- `avg_prompt_chars`: tamanho médio do prompt (indicativo de custo de tokenização).
- `composite_score`: heurística interna para ranquear formatos/modelos.

## Fluxo de Uso

> **Nota (reorg 2026-06-02)**: este pacote foi movido de
> `experiments/eval/llm_eval/` para `llm-benchmark/eval/llm_eval/`. O CLI
> `python -m experiments.llm_eval.cli` citado abaixo era stale (nao existe
> `cli.py` neste pacote). Os entrypoints reais sao os `run_*.py` em
> `llm-benchmark/eval/`. Exemplo historico (nao funcional como esta'):
```pwsh
# (historico — sem cli.py; usar os run_*.py em llm-benchmark/eval/)
python llm-benchmark/eval/run_m9_adult.py --naturalness all
```

## Interpretação
- Formatos mais compactos (TOON) tendem a reduzir tokens repetidos.
- JSONL pode aumentar redundância de chaves, aumentando custo.
- CSV é eficiente mas exige atenção do modelo ao cabeçalho e separadores.

## Próximos Passos
- Ativar perguntas adicionais (`avg_field`, `category_count`).
- Testar novos formatos de compressão e comparar contra TOON.
- Ajustar score composto para ponderar variância de latência.
