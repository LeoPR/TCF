---
type: summary
status: LIVING DOCUMENT — atualizado conforme M-series avança
last_updated: 2026-04-23
source: docs/methodology/F-findings.md (fonte canônica completa)
---

# TCF — Achados principais (resumo para publicação)

Este documento concentra os **achados de alto impacto** que serão o núcleo
do paper. Não é exaustivo — o catálogo completo está em
[F-findings.md](methodology/F-findings.md).

O projeto tem **duas linhas de pesquisa** (ver
[research-lines/README.md](research-lines/README.md)):
- **Linha A** — LLM lê TCF diretamente e calcula a resposta
- **Linha B** — TCF como schema carrier, LLM gera SQL, SQLite executa

Cada achado abaixo é rotulado com sua linha.

---

## O que foi testado

**Linha A (consolidada):** phase1..6, stats_ablation, diagnostic_3layer, scale_progression, frontier_search.
12 modelos, 4 formatos, escalas 50-5000 linhas, STATS com/sem.

**Linha B (ativa, M-series 2026-04):**
- 3 domínios: retail, medical, financial
- 3 modelos locais open-source: qwen3:14b, phi4:latest, qwen2.5-coder:7b
- 5 seeds por configuração (IC estreito)
- Escalas: 50–500 linhas; schemas 3 tabelas (star schema)
- Executor: SQLite (in-memory)

---

## Achados de alto impacto — Linha A (LLM como analista direto)

### A0 `{A}` — Aritmética sobre colunas longas tem teto em ~60-70% para modelos locais

**O que:** Modelos 7-14B locais não ultrapassam ~60-70% de accuracy em perguntas
que exigem somar/contar colunas com >100 valores — nem com TCF L3 compacto,
nem com STATS hints embutidos. A limitação é de *capacity aritmética* do
modelo, não do formato de entrada.

**Por que importa:** É o achado que **motiva cientificamente a Linha B**. Se o
modelo não consegue ser o calculador confiável, precisa ser o gerador de plano
— daí H-TCF2 (Linha B) onde SQLite faz o cálculo.

**Evidência:** phase1-6, scale_progression, frontier_search.

**Referência:** F-Q12 em [F-findings.md](methodology/F-findings.md)

### Achados secundários da Linha A

| ID | Achado | Impacto |
|----|--------|---------|
| (shared) F-Q13 | STATS hints dão +25-62pp de accuracy | Principal vetor de melhoria em Linha A |
| (shared) F-Q3 | PT ≈ EN em accuracy | Libera escolha operacional de idioma |
| (shared) F-Q5 | Capacity floor < 1B | Threshold mínimo de modelo |

---

## Achados de alto impacto — Linha B (schema carrier + SQL)

### A1 `{B}` — TCF como schema carrier: hipótese confirmada (H-TCF2)

**O que:** Usar TCF como *portador de schema* (não dos dados completos) e pedir
ao LLM que gere SQL resolve perguntas de BI com **96%+ de acurácia** — contra
~40% quando o LLM tenta ler os dados diretamente.

**Por que importa:** Inverte o problema. TCF não precisa ser legível por LLMs
linha a linha; ele precisa ser um schema carrier eficiente. O SQLite executa
a consulta com precisão exata — sem erros aritméticos.

**Evidência:** M1-M3, 3 domínios, 3 modelos, 5 seeds.

**Referência:** F-Q6 a F-Q9, F-Q16 em [F-findings.md](methodology/F-findings.md)

---

### A2 `{B}` — Fewshot é obrigatório; sem ele o sistema falha por completo

**O que:** Sem um exemplo de JOIN no prompt, acurácia cai para ~0% em perguntas
que requerem relações entre tabelas. Com 1 exemplo: 96%+.

**Por que importa:** O fewshot não é "ajuste fino" — é a diferença entre
funcionar e não funcionar. Isso define a fronteira de aplicação do sistema.

**Evidência:** M2, ablação fewshot vs zero-shot.

**Referência:** F-Q6

---

### A3 `{B}` — TCF ≈ JSON > CSV para geração de SQL (diferença pequena, mas robusta)

**O que:** TCF: 96.8%, JSON: 96.3%, CSV: 93.7% de acurácia (N=567 combinações).
A diferença TCF-CSV é de ~3pp — pequena mas consistente.

**Por que importa:** TCF não é drasticamente melhor que JSON para SQL generation.
A vantagem do TCF está na **eficiência de tokens** + **escalabilidade do schema**
quando o dataset cresce. Para tabelas pequenas, as diferenças são marginais.

**Nuance:** A inferioridade do CSV ocorre em perguntas que requerem JOINs
explícitos — o CSV não deixa a topologia FK visível.

**Evidência:** M4, 567 combinações, 3 domínios.

**Referência:** F-Q17

---

### A4 `{B}` — SQL >> Pandas >> Polars para execução via LLM

**O que:** SQL: 90%+, Pandas: ~70%, Polars: ~40% de acurácia média. CoT-SQL
(chain-of-thought antes do SQL) não melhora acurácia e custa 2.4× mais tempo.

**Por que importa:** Pandas falha principalmente por geração de código multiline
(sintaxe quebrada em modelos 7B-14B). Polars sofre de escassez de exemplos no
treinamento. CoT é custo sem benefício para modelos locais de 7-14B.

**Evidência:** M5, 1260 combinações, 4 variantes, 5 seeds.

**Referência:** F-Q18

---

### A5 `{B}` — HAVING = falha universal em aggregação de dois níveis (7%; fix via fewshot → 89%)

**O que:** Perguntas que requerem `GROUP BY + HAVING + COUNT externo` (padrão
de dois níveis) falham em 93% dos casos em todos os modelos testados.
A falha é sistemática, não aleatória: modelo gera SQL sintaticamente correto
mas semanticamente errado (nível único em vez de dois).

**SQL errado:**  `SELECT COUNT(DISTINCT fk) FROM fact GROUP BY fk HAVING COUNT(*) > N`
**SQL correto:** `SELECT COUNT(*) FROM (SELECT fk FROM fact GROUP BY fk HAVING COUNT(*) > N)`

**Por que importa:** Revela um limite de capacidade composicional dos modelos
locais 7-14B — não de formato (TCF, CSV, JSON falham igualmente).

**Status:** Fix sendo testado em M6b (adição de exemplo de subquery ao fewshot).

**Evidência:** M6, 108 combinações, q_having universal.

**Referência:** F-Q19

---

### A7 `{B}` — Style hints recuperam falhas SQL zero-shot; flags têm interferência

**O que:** Diretiva de estilo SQL pura (sem exemplo de código) recupera
q_having de **15% para 85%** (`safe_having` flag). Mas flags têm
interferência cruzada — combinar todos **degrada** algumas perguntas:
`safe_explicit_fk` regride q_top_e1_best_e2 em -11pp.

**Por que importa:** Dois resultados em um:
1. Style hints = mecanismo válido de recuperação zero-shot (sem fewshot
   específico de cada padrão); comparável a efeito de exemplos concretos
2. Flags DEVEM ser granulares — "safe-sql universal" é contraproducente
   para modelos 7B; qwen2.5-coder regride para 0% em flags off-target

**Evidência:** M8, 405 combinações, 3 modelos × 3 domínios × 3 questions × 5 variantes.

**Referência:** F-Q22

### A6 `{B}` — Generalização cross-domain confirmada (F-Q16)

**O que:** Modelo treinado (fewshot) em retail generaliza para medical e financial
sem retraining. Acurácia mantida em 90%+ para perguntas L1-L2 em todos os domínios.

**Por que importa:** Valida que o sistema não está overfit no domínio de treino
do fewshot. O schema carrier funciona para qualquer star schema de 3 tabelas.

**Evidência:** M3, 3 domínios × 3 modelos × 7 perguntas × 3 seeds.

**Referência:** F-Q16

---

## Achados secundários (relevantes para o paper)

| ID | Achado | Seção sugerida |
|----|--------|---------------|
| F-Q1 | Thinking intrínseco ≠ hiperparâmetro (deepseek-r1) | Metodologia — seleção de modelos |
| F-Q3 | PT ≈ EN em acurácia (F-Q3) | Ameaças à validade |
| F-Q5 | Modelos <1B não passam no gate de compreensão | Metodologia — threshold |
| F-Q10 | Painel de qualificação como pré-requisito | Metodologia — protocolo |
| F-Q13 | RLE com N: notação mais compacta, sem perda de acurácia | Formato TCF |
| F-Q15 | Thinking mode: sem ganho para queries simples; ganho marginal para complexas | Limitações |

---

## O que ainda não foi testado (lacunas conhecidas)

| Dimensão | Impacto esperado | Experimento |
|----------|-----------------|-------------|
| M6b: HAVING + subquery fewshot | Alto — fix de A5 | Em andamento |
| M7: subquery/CTE/COUNT DISTINCT | Alto — limites de complexidade SQL | Em andamento |
| Modelos comerciais (Claude, GPT-4o) | Alto — credibilidade do paper | M8 pendente |
| Mais domínios (4-5 total) | Médio — IC mais estreito | M9 pendente |
| Dados com conteúdo em EN vs PT | Baixo-médio | Não iniciado |
| Schema 5+ tabelas | Médio | Não iniciado |
| Null rate 30%+ | Médio | Não iniciado |
| Wording robustness | Médio | Não iniciado |
| Benchmark de timing dedicado | Baixo (pre-publicação) | M_perf pendente |

---

## O que NÃO vamos publicar como achado

- Detalhes de infraestrutura (como o Ollama foi configurado)
- Iterações de debugging (ex: "tentamos X que não funcionou, depois Y")
- Timing measurements de M1-M5 (single-run, não isolado — ver research-note de timing)
- Resultados de variantes que nunca alcançaram threshold (ex: sql_schema sem fewshot)
