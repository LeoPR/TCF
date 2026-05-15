---
type: summary
status: HISTORIC (Phase 1 LLM benchmark — ciclo v0.5)
last_updated: 2026-04-23
source: docs/archive/theory_methodology_v05/F-findings.md (arquivada)
---

> **🔎 Status (2026-05-17)**: Phase 1 LLM benchmark — ciclo v0.5,
> **acessorio** ao foco v0.6 (algoritmo OBAT + HCC).
> Manter como historico. Para resumo TCF v0.6 atual ver
> [`algorithms/TCF-format.md`](algorithms/TCF-format.md).

# TCF — Achados principais (Phase 1 — resumo paper-ready)

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

### A0 `{A}` — Linha A local é VIÁVEL para agregações simples; INVIÁVEL para filter+agg

**O que (refinado em F-Q28, 2026-04-25):** Modelos 7-14B locais em Linha A
(LLM lê TCF e calcula) atingem **52% global em Adult Census canonical**, mas
o número global esconde **decomposição dramática**:

| Tipo de question | Acc local | Mecanismo |
|------------------|-----------|-----------|
| Stats agregadas diretas (count/sum/avg/max sobre tabela inteira) | **100%** | LLM lê STATS hint pré-computada |
| Lookup categórico | ~50% | LLM conta ocorrências |
| **Filter + agregação** (WHERE + COUNT/AVG) | **0-11%** | LLM precisa **operar** sobre dados |
| Distinct count manual | **0%** | LLM precisa coletar valores únicos |

**Por que importa:**
1. **Refina F-Q12 antigo** (que dizia "60-70% ceiling"): em verdade é
   bimodal — 100% em alguns casos, 0% em outros, tudo depende se a
   question precisa de filter ou não.
2. **Motivação cientificamente afiada para Linha B:** se 100% das queries
   forem full-table agg, Linha A funciona. Para qualquer query com WHERE,
   Linha B (SQL) é necessária. Linha B no mesmo dataset = **100%** (F-Q25).

**Evidência:** F-Q12 antigo (synthetic), F-Q28 novo (canonical Adult, 63
combos, 3 modelos × 7 questions × 3 seeds).

**Referência:** F-Q12 + F-Q28 em [F-findings.md](methodology/F-findings.md)

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

### A7 `{B}` — Style hints SQL: isolados recuperam; combinações interferem

**O que (M8 — flags isolados):** Diretiva de estilo SQL pura (sem exemplo de
código) recupera q_having de **15% → 85%** (`safe_having` flag). Style hint
zero-shot comparável a fewshot com exemplo concreto (M6b: 89%).

**O que (M8b — flags combinados):** Combinar flags RARAMENTE soma ganhos.
11 de 12 combinações testadas ficam abaixo do modelo aditivo (interferência).
`all_flags` (4 hints combinados) REGRIDE q_having para 52% — pior que
`safe_having` sozinho (85%). Modelo volta ao padrão errado pré-fix quando
recebe muitos hints conflitantes.

**Exceção — 1 sinergia confirmada:** `safe_having + safe_name_join` em
q_top_e1_best_e2 atinge **96.3%** (previsto aditivo: 81.5%, sinergia +14.8pp).
Ocorre quando duas pressões de estilo se alinham com a estrutura da query.

**Por que importa (3 resultados publicáveis):**
1. Style hints = mecanismo válido de recuperação zero-shot — comparável a
   fewshot com exemplo concreto
2. Style hints **não são composicionais** — prompt noise degrada a instrução
   principal; "camada de robustez acumulável" é falsa
3. Seleção ideal de hint é **per-question-type**, não universal; abordagem
   produção correta é router-based (identificar padrão → ativar hint alinhado)

**Evidência:** M8 (405 combos) + M8b (405 combos) = 810 combinações.

**Referência:** F-Q22 (isolados), F-Q23 (combinações)

### A8 `{B}` — H-TCF2 generaliza universalmente (synthetic, canonical, single-table)

**O que:** O paradigma "schema carrier + LLM gera SQL + SQLite executa" alcança
**100% accuracy** em Adult Census (single-table real, cols hifenadas), mantendo
o resultado de 95-100% em TPC-H canonical e 96% em synthetic retail.

**Robustez confirmada em 4 dimensões:**
- Topologia: star 3-table OU single-table
- Origem: synthetic gerado OU canonical industrial
- Naming: PT (cliente, vendas) OU EN (supplier) OU hifenado (hours-per-week)
- Schema complexity: 3 colunas simples OU 14 colunas mistas

**Evidência:** M3 (189 combos), M9-TPCH (63 combos), M9-Adult (63 combos).
Total ~315 combos × 3 modelos confirmam o paradigma.

**Stratification metrics no manifest:** Adult vol=100 sample tem TVD=0.0007
vs população de 48k (representatividade quase perfeita).

**Para o paper:** M9-Adult é a evidência **mais forte** — dataset 100% real,
naming industrial, accuracy perfeita, stratification auditável.

**Referência:** F-Q25 (com link para F-Q16, F-Q24)

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
