# Pesquisa 2026-04-14: STATS como checkpoint, perguntas heuristicas, orientacao columnar

Reflexoes do usuario + pesquisa de literatura sobre 3 temas interligados:

---

## 1. STATS como DUPLO proposito (nao so LLM shortcut)

### Proposito 1: Checkpoint de integridade (sem LLM)

STATS lines (`# STATS age: n=5 sum=153 min=18 max=44 avg=30.6`) servem
como **verificacao de integridade** — mesmo sem LLM:

- Decoder pode verificar: "decodifiquei 5 valores de age, soma = 153? Confere."
- Transmissao HTTP: receptor verifica checksum textual sem parsear tudo
- Comparacao rapida: dois TCF sao "parecidos"? Compara STATS sem ler dados

**Analogia:** HTTP Content-Length header. Nao e o conteudo — e um check
que o conteudo chegou inteiro.

### Proposito 2: Referencia de qualidade para LLM

STATS permite que LLM faca **calculos parciais com validacao**:

- LLM calcula sum de um subgrupo → compara com STATS sum global → "faz sentido?"
- LLM conta rows → compara com STATS n → "contei todos?"
- LLM encontra max → compara com STATS max → "e esse mesmo?"

**Hipotese nao testada:** LLMs usam STATS como "sanity check" alem de
shortcut direto. Isso e diferente de "le avg dos STATS e responde" — e
"calcula avg, ve que STATS diz 30.6, confirma que esta proximo".

### O que precisa ser comprovado

| Hipotese | Como testar |
|----------|-------------|
| H-stats-checkpoint: STATS funciona como integridade sem LLM | Implementar verificacao no decoder |
| H-stats-reference: LLM usa STATS como validacao, nao so leitura | Perguntas de filter/group que STATS nao responde diretamente |
| H-stats-autoexplicativo: LLM entende STATS sem explicacao | Variar system prompt: com/sem explicacao de STATS |
| H-stats-scale: STATS ajuda mais em escala grande | Progressive diagnostic com/sem STATS em cada N level |

---

## 2. Perguntas heuristicas, aproximadas e relativas

### O que sao (exemplos do usuario)

- "Temos mais bananas que laranjas?" (comparativo binario)
- "Laranjas vendem mais em marco?" (tendencia temporal)
- "2005 foi uma boa safra?" (julgamento qualitativo)
- "Vendas subiram no ultimo trimestre?" (direcao)
- "Qual produto domina o mercado?" (proporcao relativa)

### Por que importam

Essas perguntas NAO precisam de precisao exata — precisam de
**compreensao de padrao**. Um LLM que erra avg por 7% pode
acertar "males work more hours than females" com 100% de confianca.

Isso e exatamente o que o ticket frozen `E-qualitative-reasoning`
propoe. Mas agora com dados canonicos (Adult):

| Pergunta qualitativa | Ground truth (Adult) | Precisa de calculo? |
|---------------------|---------------------|---------------------|
| "Males work more hours than females?" | Sim (42.4 vs 36.4) | Nao — so comparar |
| "Most people earn <=50K?" | Sim (76%) | Nao — so estimar proporcao |
| "Private sector dominates workclass?" | Sim (69%) | Nao — so olhar frequencia |
| "Education level correlates with income?" | Sim | Precisa de raciocinio |

### O que TCF columnar pode privilegiar

**Observacao do usuario:** "formato colunar poderia privilegiar unicidade,
orientar agrupamento, etc."

Sim! TCF agrupa todos os valores de uma coluna. Isso naturalmente
facilita perguntas sobre:

| Tipo de pergunta | Por que columnar ajuda |
|------------------|----------------------|
| **Frequencia/distribuicao** | Todos os valores da coluna visiveis juntos |
| **Unicidade/distinct** | Valores agrupados → facil ver repeticoes |
| **Comparacao entre colunas** | Blocos separados → "coluna A vs coluna B" |
| **Outliers** | Min/max visiveis no STATS + valores ordenados em L2 |
| **Tendencia** | Valores ordenados em L2 → sequencia visivel |

**Hipotese H-columnar-qualitative:** TCF performa melhor que CSV em
perguntas qualitativas/comparativas porque o agrupamento colunar
facilita a deteccao de padroes.

### Relacao com STATS

STATS podem ajudar em perguntas qualitativas sem dar a resposta direta:

- "Males work more?" → STATS de hours-per-week NAO separa por sex.
  Mas se TCF tem coluna `sex` com `32650*Male 16192*Female` (RLE L2),
  o modelo VE a proporcao sem precisar de STATS.

- "Most people earn <=50K?" → STATS de `class` nao existe (e categorica).
  Mas TCF L2 mostra `37155*<=50K 11687*>50K` → RLE DA a resposta.

**Insight:** RLE em colunas categoricas funciona como "STATS implicito"
para proporcoes. `37155*<=50K` literalmente diz "37155 pessoas ganham
<=50K". Nenhum outro formato faz isso tao explicitamente.

---

## 3. Orientacoes especificas que TCF columnar pode dar

### 3.1 Unicidade / cardinalidade visivel

TCF L2 sorted agrupa valores repetidos. O modelo ve:

```
education:
10501*HS-grad
7291*Some-college
5355*Bachelors
...
```

**Informacao implicita:** HS-grad e o mais comum (10501 de 48842 = 21.5%).
Em CSV, o modelo teria que CONTAR todas as ocorrencias.

### 3.2 Agrupamento natural

Se a coluna e sorted (L2), os blocos RLE sao **grupos naturais**.
"Quantos niveis de education?" = contar quantos blocos RLE na coluna.

Em CSV: precisa ler TODAS as linhas e fazer distinct.
Em TCF L2: contar blocos visualmente.

### 3.3 Ordenacao explicita

TCF L2 header: `## adult n=48842 sorted_by=education`
O modelo sabe que os dados estao ordenados. Em CSV nao ha essa informacao.

### 3.4 Proposta: column metadata hints

Alem de STATS numericos, poderíamos ter hints categoricos:

```
# DISTINCT education: 16 values
# MODE education: HS-grad (10501, 21.5%)
# DISTINCT workclass: 8 values (2799 null)
```

Isso nao existe hoje. Seria extensao do conceito STATS para colunas categoricas.

---

## 4. Literatura relevante

### TQA-Bench (2024) — Multi-table QA
- 3 categorias: lookup, aggregation, complex calculation
- 7 subcategorias (filter, join, multi-step)
- Template + symbolic computation para ground truth
- Escala de 8K a 64K tokens
- Fonte: [arxiv 2411.19504](https://arxiv.org/abs/2411.19504)

### TableEval (EMNLP 2025) — Real-world benchmark
- Template-Prompted + Role-Prompted question generation
- Clustering + deduplication para qualidade
- LLM consistency checks + human review
- Fonte: [aclanthology.org/2025.emnlp-main.363](https://aclanthology.org/2025.emnlp-main.363.pdf)

### TABLELLM (ACL 2025) — Tabular data manipulation
- 4 operacoes: query, update, merge, chart
- Query subdivide em: filter, aggregate, group, sort
- Fonte: [aclanthology.org/2025.findings-acl.538](https://aclanthology.org/2025.findings-acl.538.pdf)

### SciTaRC (2025) — Error taxonomy
- Comprehension / Localization / Calculation / Memory
- "Earliest point where output becomes unrecoverable"
- Fonte: [arxiv 2603.08910](https://arxiv.org/html/2603.08910)

---

## 5. Impacto nas tarefas

### O que NAO precisa de ticket novo

- Rotular perguntas existentes como `stats_answerable: true/false` → pos-hoc
- Adicionar 2-3 perguntas reasoning-required ao diagnostic → enriquecer ticket 30
- Registrar hipoteses H-stats-* e H-columnar-qualitative → feito aqui neste doc

### O que PODE virar ticket no futuro

| Ideia | Quando | Urgencia |
|-------|--------|----------|
| Column metadata hints (DISTINCT, MODE) | TCF v0.3 | Media |
| Perguntas qualitativas benchmark | Apos diagnostic + Etapa D analise | Media |
| Stats ablation progressiva (por nivel N0-N8) | Apos diagnostic terminar | Alta |
| System prompt variando explicacao de STATS | E-prompt-presentation (frozen) | Baixa |
| Perguntas temporais/tendencia | Apos ter dados com datas | Baixa |

### O que muda na analise do diagnostic atual

Quando o diagnostic terminar, a analise deve separar:

1. **Combos onde STATS responde direto** (avg age → STATS avg)
   → "accuracy by STATS reading"
2. **Combos onde STATS NAO responde** (se tivermos — ainda nao temos no diagnostic atual)
   → "accuracy by real reasoning"
3. **Gap:** (1) - (2) = quanto o modelo depende de STATS

Se o gap for >30pp, confirma F90-F94 em dados canonicos.
Se o gap for <10pp, STATS sao "nice to have" mas modelos raciocinam sozinhos.

---

## 6. A grande visao (do usuario)

> "O TCF poderia privilegiar informacoes de unicidade, orientar
> agrupamento, muitas hipoteses..."

Isso aponta para uma evolucao do TCF alem de compressao:

**TCF v0.2:** compressao textual (RLE, sort, dict) + STATS numericos
**TCF v0.3 (futuro):** + STATS categoricos (DISTINCT, MODE) + column hints
**TCF v0.4 (futuro):** + orientacao de agrupamento (GROUP hints) + tendencia

Cada versao **embute mais conhecimento sobre os dados** que ajuda tanto
LLMs quanto parsers programaticos. O formato evolui de "tradutor de dados"
para "formato auto-descritivo com hints analiticos".

Essa e a proposta de valor UNICA do TCF — nenhum outro formato textual
embute hints analiticos. CSV/JSONL/TOON sao "dados crus". TCF e "dados
+ meta-conhecimento".
