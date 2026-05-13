# Relatório de Avaliação Inicial: Formatos de Dados para LLMs

**Data:** 21 de novembro de 2025  
**Modelo avaliado:** `gemma3:12b` (via Ollama local)  
**Dataset:** `vendas` do `consolidated.json` (41 registros, 2 chunks de 40+1 linhas)

---

## 1. Objetivo

Avaliar o desempenho de um modelo de linguagem (LLM) ao interpretar dados tabulares apresentados em diferentes formatos textuais, medindo:

- **Acurácia:** capacidade de responder corretamente perguntas objetivas baseadas nos dados.
- **Latência média:** tempo de resposta por pergunta (em segundos).
- **Tamanho do prompt:** número de caracteres enviados (proxy de "custo" de contexto).

---

## 2. Formatos Testados

Três formatos foram avaliados, cada um com um pequeno cabeçalho de instrução seguido pelos dados:

### 2.1. CSV (Comma-Separated Values)

**Descrição:** Dados em formato tabular clássico, com nomes de colunas na primeira linha e valores separados por vírgula.

**Exemplo (3 primeiras linhas de dados):**

```
# formato: CSV
# A primeira linha contém os nomes das colunas.
# Cada linha subsequente representa um registro separado.
# Use apenas os dados abaixo, nada mais.
id_pessoa,id_produto,vl,id,pessoas.id,pessoas.nome,id_produtos,produtos.id,produtos.nome
1,22,2.50,1,1,Ana,22,1,Caneta
2,33,11.00,2,2,Bruno,33,2,Caderno
1,11,1.00,1,1,Ana,11,1,Lápis
```

**Características:**
- Compacto para humanos, mas requer parsing explícito de strings.
- Ambiguidade com vírgulas em valores textuais (não ocorreu neste dataset).
- Prompt médio: ~2.000 caracteres para 40 linhas.

---

### 2.2. JSONL (JSON Lines / NDJSON)

**Descrição:** Cada linha é um objeto JSON independente, preservando tipos e estruturas.

**Exemplo (3 primeiras linhas de dados):**

```
# formato: JSONL
# Cada linha a seguir é um objeto JSON independente.
# Leia linha por linha sem misturar campos de registros diferentes.
# Use apenas os dados abaixo, nada mais.
{"id_pessoa": "1", "id_produto": "22", "vl": "2.50", "id": "1", "pessoas.id": "1", "pessoas.nome": "Ana", "id_produtos": "22", "produtos.id": "1", "produtos.nome": "Caneta"}
{"id_pessoa": "2", "id_produto": "33", "vl": "11.00", "id": "2", "pessoas.id": "2", "pessoas.nome": "Bruno", "id_produtos": "33", "produtos.id": "2", "produtos.nome": "Caderno"}
{"id_pessoa": "1", "id_produto": "11", "vl": "1.00", "id": "1", "pessoas.id": "1", "pessoas.nome": "Ana", "id_produtos": "11", "produtos.id": "1", "produtos.nome": "Lápis"}
```

**Características:**
- Verboso (nomes de chaves repetidos em cada linha).
- Formato nativo para muitas APIs e ferramentas de dados.
- Prompt médio: ~7.600 caracteres para 40 linhas (maior overhead, mas estrutura explícita).

---

### 2.3. TOON (Token-Oriented Object Notation)

**Descrição:** Objeto JSON único contendo lista de colunas e matriz de valores (similar a DataFrames compactos). Formato compacto que evita repetição de nomes de chaves.

**Exemplo (dados completos em uma estrutura):**

```
# formato: TOKEN_OBJECT
# O bloco abaixo contém um objeto JSON com 'columns' e 'rows'.
# Use os nomes em 'columns' para interpretar cada posição das linhas.
# Use apenas os dados abaixo, nada mais.
{"format": "token_object", "columns": ["id_pessoa", "id_produto", "vl", "id", "pessoas.id", "pessoas.nome", "id_produtos", "produtos.id", "produtos.nome"], "rows": [["1", "22", "2.50", "1", "1", "Ana", "22", "1", "Caneta"], ["2", "33", "11.00", "2", "2", "Bruno", "33", "2", "Caderno"], ["1", "11", "1.00", "1", "1", "Ana", "11", "1", "Lápis"]]}
```

**Características:**
- Mais compacto que JSONL (nomes das colunas aparecem uma vez).
- Requer que o modelo "desserialize" mentalmente os arrays posicionais.
- Prompt médio: ~3.200 caracteres para 40 linhas.

---

## 3. Metodologia de Teste

### 3.1. Perguntas Avaliadas

Para cada chunk de dados, duas perguntas objetivas foram feitas:

1. **`count_rows`:** "Quantas linhas existem no conjunto de dados? Responda apenas com um número inteiro."
   - **Ground truth:** 40 linhas (chunk 0) e 1 linha (chunk 1).

2. **`sum_field`:** "Some o campo 'vl' de todas as linhas. Responda apenas com um número."
   - **Ground truth:** 215.15 (chunk 0) e 2.40 (chunk 1).

### 3.2. Métricas de Avaliação

- **Acurácia:** proporção de respostas corretas sobre total de perguntas.
  - Para `count_rows`: resposta deve ser o inteiro exato.
  - Para `sum_field`: resposta deve ser o número esperado (tolerância de ±0.000001).
- **Latência média:** tempo de processamento médio por pergunta (segundos).
- **Tamanho do prompt:** número de caracteres do prompt enviado ao modelo (inclui cabeçalho + dados + pergunta).

---

## 4. Resultados

### Resumo Consolidado

| Formato       | Acurácia | Corretas | Total | Latência Média (s) | Prompt Médio (chars) |
|---------------|----------|----------|-------|-------------------|---------------------|
| **JSONL**     | **50%**  | 2/4      | 4     | **120.36**        | ~7.600              |
| **CSV**       | **25%**  | 1/4      | 4     | **172.98**        | ~2.000              |
| **TOON**      | **50%**  | 2/4      | 4     | **187.99**        | ~3.200              |

### Análise Detalhada por Formato

#### 4.1. JSONL
- **Acertos:** 
  - `count_rows` para chunk pequeno (1 linha): ✅ correto.
  - `sum_field` para chunk pequeno: ✅ correto (2.40).
- **Erros:**
  - `count_rows` para chunk grande (40 linhas): ❌ respondeu "100" (esperado: 40).
  - `sum_field` para chunk grande: ❌ listou os valores individuais em vez de somá-los.
- **Observações:**
  - Prompts grandes (~7.6k chars) mas modelo teve menor latência relativa.
  - Respostas incorretas sugerem dificuldade em agregar muitos registros JSON.

#### 4.2. CSV
- **Acertos:**
  - `sum_field` para chunk pequeno: ✅ correto (2.40).
- **Erros:**
  - `count_rows` para chunk grande: ❌ respondeu "30" (esperado: 40).
  - `count_rows` para chunk pequeno: ❌ respondeu "2" (esperado: 1).
  - `sum_field` para chunk grande: ❌ listou valores individuais.
- **Observações:**
  - Pior acurácia (25%) apesar de prompts menores (~2k chars).
  - Latência média alta (173s), possivelmente por confusão no parsing.
  - Modelo parece ter dificuldade em interpretar CSV corretamente (talvez conte linhas de cabeçalho ou ignore instruções).

#### 4.3. TOON (Token-Oriented Object Notation)
- **Acertos:**
  - `count_rows` para chunk pequeno: ✅ correto (1).
  - `sum_field` para chunk pequeno: ✅ correto (2.40).
- **Erros:**
  - `count_rows` para chunk grande: ❌ respondeu "30" (esperado: 40).
  - `sum_field` para chunk grande: ❌ listou valores individuais.
- **Observações:**
  - Acurácia de 50%, empatada com JSONL.
  - Latência mais alta (188s), possivelmente por necessidade de "desserializar" matriz.
  - Prompts intermediários (~3.2k chars).

---

## 5. Análise de Respostas Incorretas

### Padrão observado: "Listagem em vez de soma"

Em todos os três formatos, quando solicitado para **somar** o campo `vl` do chunk grande (40 linhas), o modelo respondeu listando os valores individuais separados por vírgula:

**Exemplo de resposta (CSV):**
```
2.50,11.00,1.00,3.75,2.90,4.50,3.20,5.90,6.50,7.30,12.00,1.80,8.40,1.20,2.70,10.90,2.60,4.10,3.00,5.50,6.10,7.80,11.50,1.40,8.90,1.10,2.30,10.50,2.80,4.30,3.40,5.20,6.20,7.10,12.40,1.60,8.10,1.30,2.20,10.20
```

**Causa possível:**
- Modelo não executou a operação de agregação (soma).
- Pode ter interpretado a instrução como "listar valores do campo vl".
- Contexto grande (40 linhas) dificulta rastreamento de operações aritméticas.

### Padrão observado: "Contagem incorreta"

- CSV e TOON responderam "30" para 40 linhas.
- CSV respondeu "2" para 1 linha.
- Possíveis causas:
  - Modelo pode estar contando tokens, palavras, ou linhas de prompt em vez de registros de dados.
  - Instrução pode não ter sido clara o suficiente ou foi ignorada.

---

## 6. Conclusões Preliminares

### 6.1. Formato Recomendado (até o momento)

**JSONL** apresentou o melhor equilíbrio entre acurácia (50%) e latência (120s), apesar de ter os maiores prompts. Isso sugere que:
- Estrutura explícita (chaves nomeadas) facilita compreensão do modelo.
- Overhead de caracteres é compensado por melhor parsing interno.

### 6.2. Desafios Identificados

1. **Agregações numéricas:** Modelo teve dificuldade consistente em somar valores (todos os formatos falharam no chunk grande).
2. **Contagem de linhas:** Erros frequentes sugerem ambiguidade na interpretação de "linhas" vs "registros" vs "tokens".
3. **Sensibilidade ao tamanho do contexto:** Chunk pequeno (1 linha) teve 100% de acerto em todos os formatos; chunk grande (40 linhas) teve ~0% de acerto.

### 6.3. Próximos Passos

1. **Melhorar prompts de sistema:**
   - Adicionar exemplos de cálculos esperados.
   - Reforçar instrução de "não listar, apenas somar".
   
2. **Testar modelos alternativos:**
   - Repetir bateria com `deepseek-r1:8b`, `llama3.2`, ou `qwen2.5-coder` para ver sensibilidade específica do modelo.
   
3. **Adicionar perguntas intermediárias:**
   - `avg_field`: média de um campo numérico (detectar se modelo divide corretamente).
   - `category_count`: contar registros por categoria (testar agregação não-numérica).
   
4. **Implementar formato customizado de compressão:**
   - Adicionar à lista de formatos testados.
   - Comparar com baseline TOON e JSONL.

5. **Métricas adicionais:**
   - Medir tokens reais (input/output) se API expuser contadores.
   - Calcular "compressão efetiva" (bytes transmitidos vs bytes originais).
   - Testar variabilidade com seeds diferentes (temperatura > 0).

---

## 7. Anexos

### 7.1. Ground Truth Completo

```json
{
  "vendas:0000": {
    "count_rows": 40,
    "sum_field": 215.15
  },
  "vendas:0001": {
    "count_rows": 1,
    "sum_field": 2.40
  }
}
```

### 7.2. Exemplo de Resposta Correta (chunk pequeno, JSONL)

**Pergunta:** "Quantas linhas existem no conjunto de dados?"  
**Resposta do modelo:** `1`  
**Status:** ✅ Correto

**Pergunta:** "Some o campo 'vl' de todas as linhas."  
**Resposta do modelo:** `2.40`  
**Status:** ✅ Correto

### 7.3. Exemplo de Resposta Incorreta (chunk grande, CSV)

**Pergunta:** "Quantas linhas existem no conjunto de dados?"  
**Resposta do modelo:** `30`  
**Esperado:** `40`  
**Status:** ❌ Incorreto

---

## 8. Configuração do Experimento

- **Comando CLI:**
  ```bash
  python -m experiments.llm_eval.cli eval \
    --model gemma3:12b \
    --format <csv|jsonl|token_object> \
    --consolidated consolidated.json \
    --rows-per-chunk 40 \
    --sum-field vl \
    --out-dir results/gemma_<formato>
  ```
  
  **Nota:** O formato `token_object` corresponde à implementação de TOON (Token-Oriented Object Notation).

- **Servidor Ollama:** `http://localhost:11434`
- **Temperatura:** 0.0 (determinístico)
- **Modelo:** `gemma3:12b` (Gemma 3 com 12.2B parâmetros, quantização Q4_K_M)

---

**Fim do relatório.**
