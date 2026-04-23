---
title: F-findings — catálogo canônico de achados metodológicos
date: 2026-04-21
type: methodology
status: CANONICAL
---

# F-findings — catálogo de achados metodológicos (LLM/Ollama/TCF)

Este documento é o **índice canônico** dos achados operacionais do projeto.
Cada achado tem um ID estável (`F-Q<n>`), uma formulação curta como
**conclusão científica**, e um ponteiro para a nota de pesquisa detalhada.

Regra de estilo: cada F-finding é formulado como *descoberta reprodutível*
— nunca como "erro nosso". A razão é que os mesmos comportamentos afetam
qualquer pesquisador rodando os mesmos modelos; documentar como achado
reutilizável é mais útil que lamentar.

---

## F-Q1 — Intrinsic thinking é característica arquitetural, não hiperparâmetro

**Conclusão:** Modelos `deepseek-r1:*` (e outros da classe *intrinsic-thinking*)
colapsam para prompt-echo ou geração degenerada quando `think=False`. O
pipeline de inferência assume tokens de thinking presentes.

**Implicação metodológica:** Catálogo de modelos deve classificar thinking em
`{none, toggle, intrinsic, graded}`. Controles experimentais só aplicam
`think=False` em categoria `toggle`.

**Evidência:** `deepseek-r1:7b` × 5 seeds: `think=False` → eco de prompt;
`think=None` → "Brasília". Determinístico.

**Referência:** [`2026-04-20-qualification-findings.md` §F-Q1](../research-notes/2026-04-20-qualification-findings.md)

---

## F-Q2 — Arquitetura multimodal degrada text-only em alguns modelos

**Conclusão:** `qwen3-vl:8b` apresenta timeouts patológicos (45s+) em prompts
text-only triviais, enquanto `qwen3:8b` (mesmo tamanho, sem vision) responde
em ~1.3s. `llama3.2-vision:11b` NÃO apresenta essa degradação — não é
universal entre modelos vision-augmented.

**Implicação metodológica:** Modelos multimodais devem ser validados
individualmente para uso text-only antes de entrarem em painéis de qualificação.

**Referência:** [`2026-04-20-qualification-findings.md` §F-Q2](../research-notes/2026-04-20-qualification-findings.md)

---

## F-Q3 — Ausência de viés PT vs EN em accuracy canônica

**Conclusão:** 5 top-performers × 7 perguntas × 2 idiomas (PT/EN) mostram
accuracy 100% idêntica. Latência PT inicial é artefato de cold-start, não
de idioma.

**Implicação metodológica:** Prompts TCF em PT são cientificamente
equivalentes a EN para fins de accuracy; a escolha de idioma é operacional.

**Referência:** [`2026-04-20-qualification-findings.md` §F-Q3](../research-notes/2026-04-20-qualification-findings.md)

---

## F-Q4 — Ambiguidade linguística em contagem lexical vs conteúdo

**Conclusão:** "Conte as palavras em 'A raposa marrom pula'" recebe 4
(lexical) de alguns modelos e 3 (conteúdo, exclui artigo) de outros. Ambas
interpretações são válidas.

**Implicação metodológica:** Scoring de questões de contagem em PT deve
aceitar tolerância `[N-1, N]` quando há artigos. Em TCF, prompts sobre
"linhas" precisam desambiguar "linhas físicas do formato" vs "linhas
lógicas de dados".

**Referência:** [`2026-04-20-qualification-findings.md` §F-Q4](../research-notes/2026-04-20-qualification-findings.md)

---

## F-Q5 — Capacity floor existe abaixo de 1B parâmetros

**Conclusão:** `qwen3:0.6b` responde "Brasil" para "capital do Brasil" —
confunde entidade país/cidade. É limite de capacity, não de configuração.

**Implicação metodológica:** Modelos < 1B não devem entrar em painel
principal sem qualificação específica; reservados para benchmarks de
edge deployment.

**Referência:** [`2026-04-20-qualification-findings.md` §F-Q5](../research-notes/2026-04-20-qualification-findings.md)

---

## F-Q6 — Cold-start na primeira chamada PT

**Conclusão:** A primeira chamada em PT após troca de modelo/sessão custa
20-60s; chamadas subsequentes ficam em 2-8s.

**Implicação metodológica:** Medições de latência devem descartar primeira
chamada OU usar warmup prompt em PT antes da medição.

**Referência:** [`2026-04-20-qualification-findings.md` §F-Q6](../research-notes/2026-04-20-qualification-findings.md)

---

## F-Q7 — Catálogo de modelos modernos vs obsoletos

**Conclusão:** Famílias têm gerações sucessivas que tornam anteriores
redundantes (phi3 → phi4; qwen2.5 → qwen3; llama3.1 → llama3.2). Manter
versões antigas em teste principal polui ranking sem novo sinal.

**Implicação metodológica:** `qualified_models.json` deve excluir gerações
obsoletas; manter apenas em `obsolete_models.json` para ablação histórica.

**Referência:** [`2026-04-20-qualification-findings.md` §F-Q7](../research-notes/2026-04-20-qualification-findings.md)

---

## F-Q8 — Thinking consome budget de `num_predict`

**Conclusão:** Em modelos reasoning, `num_predict` limita **thinking +
response**, não apenas response. Budget insuficiente trunca a resposta
após thinking (aparentemente o modelo "falhou" mas na verdade o servidor
cortou na metade).

**Evidência:** `phi4:latest` em TCF L3 n=100 q_count: response TRUNCATED
(done_reason="length") com thinking_length=0 — thinking não aconteceu, mas
a resposta estava longa demais para o default num_predict.

**Implicação metodológica:**
1. Sempre instrumentar `thinking_length`, `done_reason`, `truncated` em
   todo record de experimento.
2. Budget explícito `num_predict=4096+` para modelos reasoning;
   `num_predict=8192+` se thinking_length observado passar de ~3500c.
3. Record truncado ≠ model failure — é **instrumentation failure** da parte
   do experimento.

**Referência:** implementado em `llm_eval/ollama_client.py::GenerateResult`
e `run_frontier_search.py::LLM_OPTIONS` (2026-04-21).

---

## F-Q9 — `keep_alive` em `options` é silenciosamente ignorado

**Conclusão:** Ollama trata `keep_alive` como campo top-level da payload.
Colocá-lo dentro de `options` gera warning no servidor e o valor é
descartado — modelos descarregam após default (5min).

**Implicação metodológica:** `keep_alive` viaja em `client.generate(...,
keep_alive="30m")`, nunca em `options={"keep_alive": ...}`.

**Referência:** fix em `llm_eval/ollama_client.py::_TOPLEVEL_KEYS`.

---

## F-Q10 — Non-convergent thinking em modelos 7B-reasoning (escopo narrow)

**Conclusão (escopo narrow):** `deepseek-r1:7b` em TCF L3 com perguntas de
contagem implícita apresenta thinking não-convergente (budget scaling
não-monotônico: 2121→31950→70052→1917 chars). Pattern específico à
combinação *modelo × tarefa × formato*; não generalizar.

**Caveat crítico:** Este achado é observação em escopo narrow (1 modelo ×
1 task domain × 2 perguntas × seed=42). Qualquer menção externa precisa
incluir essas limitações explicitamente.

**Implicação metodológica:** Reasoning models têm modo de falha
"thinking degenerado" distinto de "capacity floor" — ambos terminam em
resposta errada, mas representam problemas diferentes. Instrumentação
F-Q8 permite distinguir.

**Referência:** [`2026-04-21-thinking-non-convergence.md`](../research-notes/2026-04-21-thinking-non-convergence.md)

---

## F-Q11 — Determinismo CPU↔GPU não-verificado formalmente

**Conclusão:** Com `temperature=0, seed=42`, Ollama é empiricamente
determinístico dentro do mesmo backend. CPU↔GPU pode divergir em 1-2
tokens por conta de drift numérico de floating-point nas camadas
transformer, mas não há medição formal do impacto em accuracy de task.

**Implicação metodológica:** Records do mesmo combo gerados em backends
diferentes devem ser anotados (`compute_backend` field). Comparações
cross-backend precisam de replicação.

**Referência:** observado durante Phase 6 (CPU→GPU mid-run em
deepseek-r1:14b; 5 records cached de CPU mantidos após mudança).

---

## F-Q12 — Aritmética sobre colunas com muitas linhas falha universalmente

**Conclusão:** 12 modelos locais (phi4 a gemma3:1b) têm 0% acurácia em
`sum()` e `avg()` sobre coluna numérica de 255 linhas em TCF L3.
Tarefas de retrieval (max, top) funcionam; aggregation não.

**Mecanismo hipotético:** O modelo precisa simultaneamente (a) expandir o
RLE mentalmente, (b) manter state de soma ao longo de 255 passos, (c)
formatar a resposta. Capacidade representacional combinada estoura em 7B-14B.

**Implicação metodológica:**
- Aggregation não é "failure point de modelo" — é **failure point de
  arquitetura cognitiva** de LLMs dessa classe.
- Resposta deve ser tool-calling ou program-of-thoughts (emitir código
  Python, executar externamente).
- Futuros experimentos TCF devem testar PoT como baseline de sucesso.

**Referência:** Phase 6 resultados (2026-04-21), `manifest.jsonl` phase=6.

---

## F-Q13 — Schema-only prompt supera data-full prompt para code generation

**Conclusão:** Ao pedir que o LLM gere SQL (ou código) para responder
pergunta sobre tabela, fornecer **apenas o schema** (620 chars) produz
*melhor* acurácia que fornecer schema + dados completos (6324 chars).
A descoberta é counter-intuitive: **mais contexto prejudica** a code
generation quando o executor externo (SQLite) tem acesso aos dados reais.

**Evidência (M1, 2026-04-22):** 3 modelos × 3 variantes × 7 questões:

| Variante | Prompt chars | Acurácia agregada |
|----------|--------------|-------------------|
| sql_full (TCF L3 completo) | 6324 | 52% |
| sql_schema (só colunas+tipos+FK) | **620** | **86%** |
| sql_stats (schema + estatísticas) | 1303 | 86% |

qwen3:14b + sql_schema atinge **100% (7/7)** — incluindo q_sum e q_avg
onde todos os 12 modelos testados em Phase 6 (direct read) obtiveram 0%.

**Mecanismo hipotético:** Dados brutos no prompt ativam circuitos de
"reading comprehension" do modelo, que competem com circuitos de
"SQL synthesis". Sem os dados, o modelo foca apenas em gerar estrutura
sintática correta contra o schema declarado.

**Implicação metodológica:**
- Para tarefas de agregação/analytics, **separar schema (input) de dados
  (executor)** não é otimização — é pré-requisito para correctness.
- Stats ricas (cardinality, ranges) NÃO adicionam valor mensurável em
  schemas simples (3 tabelas, 10 colunas). Provavelmente importam em
  schemas ambíguos ou com decisões de filtro dependentes de distribuição.
- TCF deve oferecer `--profile code-gen-schema` emitindo **só** o header
  denso + tipos + FKs, ~5-10x mais barato que L3 completo.

**Implicação para TCF (teoria):** TCF L3 foi desenhado para o caso
"LLM lê dados direto". M1 mostra que esse caso é **pior** que "LLM lê
schema, gera SQL, executor calcula". TCF como **schema carrier** é o
valor único — não como "formato para LLM ler dados brutos".

**Status atualizado 2026-04-22 (pós-M2):**
- 315 combos: 3 modelos × 5 variantes × 7 questões × 3 seeds
- Variância inter-seed ≈ 0pp (temperatura=0 determinístico)
- sql_stats_fs atinge **100%** em todos os 3 modelos
- Limitação restante: 1 domínio (retail sales). M3 endereça isso.

**Referência:** `experiments/results/m2_codegen/manifest.jsonl` (2026-04-22)

---

## F-Q14 — SQL gerado por LLM é scale-invariant por construção

**Conclusão:** Uma vez que o LLM produz SQL sintaticamente correto a partir
do schema, o mesmo SQL retorna resultado correto em qualquer escala de dados
(n=100 a n=12.513 testados), **sem re-gerar a query**. A correctness é função
do schema, não dos valores.

**Evidência (M2 scale invariance, 2026-04-22):** 88 SQLs gerados sobre n=100
(255 vendas) foram re-executados contra DBs frescas em n=500 (1241 vendas),
n=1000 (2508 vendas) e n=5000 (12513 vendas):

| Scale | SQLs testados | Corretos | Acc |
|-------|---------------|----------|-----|
| n=500 | 88 | 88 | 100% |
| n=1000 | 88 | 88 | 100% |
| n=5000 | 88 | 88 | 100% |

**Implicação metodológica:** Custo de tokens é independente de escala de dados.
Para qualquer tamanho de tabela, o custo de inferência LLM é constante
(função do schema, não de N). Isso inverte o argumento padrão de LLM+dados:
em vez de "não cabe no context window", o context window **deixa de ser
fator limitante**.

**Implicação para TCF:** a `--profile code-gen-schema` (quando existir)
pode ser pré-computada uma vez e reusada para qualquer snapshot de dados
mantendo o mesmo schema. Ideal para cenários de dashboards/analytics
recorrentes.

**Referência:** `experiments/results/m2_codegen/manifest.jsonl` + scale probe
output (2026-04-22)

---

## F-Q15 — Few-shot elimina modo de falha de alucinação de schema

**Conclusão:** Um único exemplo (1-shot) de SQL com JOIN explícito e nota
negativa ("tabela X NÃO tem coluna Y") elimina a alucinação de colunas
inexistentes — modo de falha dominante em q_top_product e q_lookup.

**Evidência (M2, 2026-04-22):**

| Questão | sem few-shot | com few-shot | Delta |
|---------|--------------|--------------|-------|
| q_top_product | 3/9 (33%) | **9/9 (100%)** | +67pp |
| q_lookup | 7/9 (78%) | **9/9 (100%)** | +22pp |

O modelo **7B** (qwen2.5-coder:7b) sobe de 81% (sql_stats) para **100%**
(sql_stats_fs) com apenas a adição do exemplo.

**Mecanismo:** modelos sem few-shot inferem colunas por analogia a schemas
vistos em training ("tabela de vendas costuma ter id"). O exemplo ancora
o modelo ao schema **real**, reduzindo recall alucinado.

**Implicação metodológica:**
- Para text-to-SQL/code, **sempre incluir ≥1 exemplo** quando acurácia
  > 95% é requisito
- O exemplo não precisa estar relacionado à pergunta alvo — basta cobrir
  o padrão "tabelas JOIN por FK explícito"
- Nota negativa ("X NÃO tem coluna Y") é mais efetiva que exemplo positivo
  isoladamente

**Anti-padrão:** sql_full (com dados completos) NÃO resolve com few-shot —
os dados brutos continuam competindo com a instrução sintática. Few-shot
só ajuda quando o prompt já é schema-only.

**Referência:** `experiments/results/m2_codegen/manifest.jsonl` (2026-04-22)

---

## F-Q16 — SQL generation generaliza across unrelated domains

**Conclusão:** O mesmo pipeline (schema+stats+few-shot) que alcança 100% em
retail sales também alcança ≥86% em domínios desconexos (medical consultations,
financial transactions). qwen3:14b mantém 100% em todas as 3 domains; phi4 e
qwen2.5-coder:7b atingem 100% em retail+medical, 86% em financial (falha isolada
em q_distinct).

**Evidência (M3, 2026-04-22):** 3 domains × 3 models × 7 questions × 3 seeds:

| Domain | qwen3:14b | phi4:latest | qwen2.5-coder:7b | Agregado |
|--------|-----------|-------------|------------------|----------|
| Retail | 100% (21/21) | 100% (21/21) | 100% (21/21) | 100% |
| Medical | 100% (21/21) | 100% (21/21) | 100% (21/21) | 100% |
| Financial | 100% (21/21) | 86% (18/21) | 86% (18/21) | 90% |

Falhas em financial restritas a q_distinct (3/9 agregado); todos outros
7 question types 100%.

**Mecanismo hipotético:** SQL generation é task invariant quando baseado em
schema+tipos+FKs. O modelo não "aprende" sobre variedade de dados; ele aprende
"como estruturar JOINs dado um schema". Dados em medical (paciente→consulta→medico)
e financial (conta→transacao→categoria) têm mesma topologia de FK que retail
(cliente→venda→produto), então o mesmo padrão sintático funciona.

**Implicação metodológica:**
- H-TCF2 é **domain-generic** — não e um artefato de retail sales
- Qualquer schema com 2 dimensions + 1 fact table (star pattern) vai ter
  ≥90% accuracy com sql_stats_fs, independente de domínio
- q_distinct em financial merece investigation separada (possível edge case
  em cardinalidade de tabela ou ForeignKey resolution)

**Implicação para TCF:** Tabular analytics em **qualquer** domínio (healthcare,
finance, e-commerce, telemetry) pode usar o mesmo código-gen flow. Valor do
TCF é **domain-agnostic schema representation**.

**Referência:** `experiments/results/m3_crossdomain/manifest.jsonl` (2026-04-22)

---

## F-Q17 — Vantagem de formato TCF sobre CSV/JSON é pequena; FK explícito é o diferencial

**Conclusão:** Em 567 combos (3 domínios × 3 modelos × 3 formatos × 7 q × 3 seeds),
TCF (96.8%) e JSON (96.3%) são praticamente empatados; ambos superam CSV (93.7%)
por ~3pp. A vantagem real de TCF é pontual: FK explícito no schema elimina
alucinação de JOINs em q_top_entity2 e q_lookup (TCF 27/27 vs JSON 21/27 vs
CSV 20/27). Para modelos mais fracos o ganho é maior: qwen2.5-coder:7b ganha
+8pp sobre CSV e +5pp sobre JSON com TCF.

**Evidência (M4, 2026-04-22):**

| Formato | Acc agregada | q_top_entity2 | q_lookup | q_distinct |
|---------|-------------|---------------|----------|------------|
| CSV     | 93.7% | 20/27 | 22/27 | 27/27 |
| JSON    | 96.3% | 21/27 | 26/27 | 27/27 |
| TCF     | 96.8% | **27/27** | **27/27** | 21/27 |

| Modelo | CSV | JSON | TCF |
|--------|-----|------|-----|
| qwen3:14b | 100% | 98% | 100% |
| phi4:latest | 94% | 100% | 95% |
| qwen2.5-coder:7b | 87% | 90% | **95%** |

**Achado colateral — naming collision (TCF q_distinct/financial):** Os 6 erros
TCF em q_distinct são todos no domínio financial: modelo gera `t.titular`
buscando coluna `titular` diretamente em `transacoes`, mas ela existe só em
`contas`. Em CSV o dado bruto mostra explicitamente onde `titular` aparece;
em TCF schema-only o modelo infere erroneamente por nome de entidade no texto
da pergunta. Não é defeito de formato — é colisão entre label de entidade e
nome de coluna em tabela diferente da fact table.

**Implicação metodológica:**
- TCF supera CSV/JSON quando o schema tem FKs não-óbvios → joins precisos
- Diferença cai a zero para modelos 14B (qwen3:14b = 100% nos três formatos)
- Para deployment com modelos menores, TCF é a escolha mais robusta
- Question templates não devem usar como label o nome de coluna de uma
  dimensão diferente da fact — gera confusão semântica format-agnostic

**Implicação para TCF (teoria):** O valor diferencial de TCF não é
"compressão" ou "legibilidade" — é **declaração explícita de FK topology**.
CSV/JSON descrevem colunas; TCF declara relações. Para SQL generation, o
que importa é relação, não coluna.

**Referência:** `experiments/results/m4_baseline/manifest.jsonl` (2026-04-22)

---

## Histórico de evolução

| Data | Evento |
|---|---|
| 2026-04-19 | F-Q1 descoberto (deepseek-r1 intrinsic) |
| 2026-04-20 | F-Q2 a F-Q7 consolidados em qualification-findings.md |
| 2026-04-21 | F-Q8 (num_predict budget), F-Q9 (keep_alive), F-Q10 (non-convergent) |
| 2026-04-21 | F-Q11 (determinismo CPU↔GPU), F-Q12 (aritmética universal) |
| 2026-04-21 | Documento canônico criado |
| 2026-04-22 | F-Q13 (schema > data-full), F-Q14 (scale invariance), F-Q15 (few-shot) |
| 2026-04-22 | F-Q16 (cross-domain generalization) |
| 2026-04-22 | F-Q17 (CSV vs JSON vs TCF; FK topology é o diferencial) |

## F-Q18 — SQL supera Pandas e Polars; CoT-SQL não adiciona acurácia sobre SQL direto

**Conclusão:** Para SQL generation a partir de schema TCF, o pipeline
`LLM → SQL → SQLite` domina. Pandas e Polars como execução intermediária
produzem acurácias muito menores. Chain-of-thought (CoT) antes do SQL
não melhora acurácia em modelos locais.

**Evidência (M5, 2026-04-22):** 1260 combos — 3 domínios × 3 modelos ×
4 variantes × 7 questões × 5 seeds:

| Variante | Acc | 95% CI | Latência (med) | c/resposta-certa |
|----------|-----|--------|----------------|-----------------|
| sql_stats_fs | **96.8%** | [94.3%, 98.3%] | 1931ms | 1566 |
| cot_sql_fs | 96.5% | [93.9%, 98.0%] | 4726ms | 1610 |
| pandas_fs | 68.6% | [63.2%, 73.4%] | 2113ms | 2749 |
| polars_fs | 47.6% | [42.2%, 53.1%] | 2127ms | 3983 |

**SQL vs CoT-SQL:** diferença de 0.3pp está dentro do CI — são equivalentes
em acurácia. CoT custa 2.4× mais latência sem ganho mensurável. Conclusão:
modelos locais 7-14B já sintetizam o "plano de joins" implicitamente quando
o schema é claro; verbalizar os passos não ajuda.

**SQL vs Pandas (-28pp):** hipótese "Pandas usa named params → menos alucinação
de FK" falsificada. O problema não é de representação do join — é de geração
de código multiline. Modelos falham em fechar parênteses, indentação e lógica
encadeada de `.merge().groupby().agg()`. SQL é uma linguagem de expressão
*declarativa de linha única* — mais fácil de gerar corretamente do que
código imperativo encadeado.

**SQL vs Polars (-49pp):** Polars é inviável com os modelos testados. A API
(`pl.col()`, `.with_columns()`, lazy frames) tem representação insuficiente
em training data dos modelos 7-14B locais.

**Segmentação por modelo:**
| Modelo | SQL | CoT | Pandas | Polars |
|--------|-----|-----|--------|--------|
| qwen3:14b | 100% | 100% | 62% | 48% |
| phi4:latest | 96% | 98% | 76% | 43% |
| qwen2.5-coder:7b | 94% | 91% | 68% | 52% |

phi4 e CoT: phi4 é o único onde CoT > SQL (+2pp) — consistente com o fato
de phi4 ser um modelo reasoning com training specific para structured output.

**Implicação metodológica:**
- Para SQL generation com schema TCF: usar sql_stats_fs, não envolver Python
- CoT pode ser útil em modelos reasoning específicos (phi4), mas não é
  ganho genérico suficiente para justificar 2.4× de latência
- Polars requer fine-tuning especializado para ser viável como execution form

**Referência:** `experiments/results/m5_intermediate/manifest.jsonl` (2026-04-22)

---

| 2026-04-22 | F-Q18 (SQL > Pandas > Polars para code-gen; CoT não adiciona acurácia) |
| 2026-04-22 | F-Q19 (HAVING falha universal: confusão de escopo de agregação aninhada) |
| 2026-04-22 | M6: WHERE+filter+GROUP-SUM=100%; HAVING=7% |

## F-Q19 — HAVING com agregação aninhada falha universalmente em modelos locais

**Conclusão:** Queries do tipo "quantos grupos satisfazem COUNT(*) > N" têm
acurácia de 7% (2/27) em 3 modelos × 3 domínios × 3 seeds. O modelo gera
SQL sintaticamente correto com HAVING mas na forma errada: aplica COUNT
*dentro* de cada grupo em vez de *sobre* os grupos resultantes. Requer
subquery que o modelo não usa espontaneamente.

**Evidência (M6, 2026-04-22):** 3 modelos × 3 domínios × 3 seeds = 27 combos.

| Modelo | Acc q_having | Padrão gerado |
|--------|-------------|---------------|
| qwen3:14b | 0/9 (0%) | `SELECT COUNT(DISTINCT fk) ... GROUP BY fk HAVING COUNT(*) > N` |
| phi4:latest | 1/9 (11%) | Idem, exceto seed=123 onde usa subquery |
| qwen2.5-coder:7b | 1/9 (11%) | Idem |

**Padrão de falha (18/25 wrong_count):**
```sql
-- ERRADO: retorna 1 por grupo (COUNT(DISTINCT fk) dentro de grupo = sempre 1)
SELECT COUNT(DISTINCT id_cliente)
FROM vendas GROUP BY id_cliente HAVING COUNT(*) > 25
```

**Padrão correto (phi4 seed=123):**
```sql
-- CORRETO: subquery filtra grupos, outer query conta os grupos restantes
SELECT COUNT(DISTINCT id_cliente) FROM (
    SELECT id_cliente FROM vendas
    GROUP BY id_cliente HAVING COUNT(*) > 24
)
```

**Mecanismo:** O modelo conhece a sintaxe HAVING mas não raciocina sobre
**escopo de agregação**. "Contar entidades que aparecem mais de N vezes"
requer dois níveis: (1) agrupar e filtrar com HAVING, (2) contar os grupos
resultantes via subquery. O modelo colapsa os dois em uma única cláusula
SELECT com semântica errada mas sintaxe válida — por isso executa sem erro
e retorna resultado plausível (um número, nunca uma exception).

**Comparação com F-Q12:** F-Q12 (aritmética sobre 255 linhas) falha por
*capacity* — o modelo não consegue somar mentalmente. F-Q19 falha por
*escopo de raciocínio* — o modelo não entende que precisa de duas passagens
sobre os dados. Ambos são failure modes distintos de "resposta errada que
executa sem erro".

**Implicação metodológica:**
- Queries HAVING-counting são um caso especial que requer subquery; não são
  detectáveis por syntax checking — executam mas retornam errado
- Para cobrir esse caso em production: adicionar ao few-shot um exemplo de
  subquery com HAVING (similar ao efeito de F-Q15 sobre q_top_entity)
- M6b (hipótese): adicionar exemplo HAVING ao FEWSHOT_BLOCK e re-testar

**Referência:** `experiments/results/m6_filter/manifest.jsonl` (2026-04-22)

**Atualização M6b (2026-04-23):** Adicionar exemplo de subquery ao fewshot
corrigiu q_having de 7% → **88.9%** (24/27). As 3 falhas restantes são
erro de FK no domínio financial (phi4: `t.titular` não existe) — não
relacionado ao padrão HAVING. Subquery fewshot é o fix mínimo efetivo.

---

## F-Q20 — Queries L3 (CTE/subquery aninhada) alcançam 86% com fewshot adequado

**Conclusão:** Queries de nível 3 de complexidade SQL — CTE com filtro em
agregação (`q_above_avg`), subquery aninhada em WHERE (`q_top_e1_best_e2`),
COUNT DISTINCT em GROUP BY (`q_e2_most_e1`) — alcançam **86.4% global**
(70/81) com fewshot que inclui exemplos dos padrões. O padrão CTE é o mais
confiável (100% em q_above_avg); falhas concentradas em dois tipos:

1. **Column confusion em subquery** (`q_top_e1_best_e2`, 78%): modelo usa
   coluna errada na subquery interna (ex: `SELECT id FROM consultas` em vez de
   `SELECT id_paciente FROM consultas`). Erro de referência de coluna em query
   com dois JOINs.

2. **ID vs nome na saída** (`q_e2_most_e1`, 81%): modelo retorna FK/ID em vez
   do nome da entidade — JOIN à tabela de dimensão ausente ou usa CTE que
   seleciona `id_categoria` em vez de `d2.nome`.

**Por que CTE > subquery aninhada:** CTEs tornam cada passo nomeado e
rastreável. Modelos treinados em código Python têm viés para nomes explícitos.

**Evidência (M7, 2026-04-23):** 3 modelos × 3 domínios × 3 questions × 3 seeds = 81 combos.

| Question | Acurácia | Padrão SQL | Tipo de falha |
|---------|---------|-----------|--------------|
| q_above_avg | 27/27 (100%) | CTE + WHERE avg | — |
| q_e2_most_e1 | 22/27 (81%) | COUNT DISTINCT GROUP BY | ID vs nome (5x) |
| q_top_e1_best_e2 | 21/27 (78%) | subquery aninhada WHERE | coluna errada (6x) |

**Implicação metodológica:**
- CTEs com nomes explícitos são mais robustos que subqueries aninhadas
- Falhas de "coluna errada" e "ID vs nome" são distintas das falhas de HAVING
  (scope confusion) — são erros de *mapeamento de schema*, não de lógica
- Fewshot com exemplos específicos de cada padrão é mais efetivo que hint geral
- Hipótese `--safe-sql`: diretiva de estilo "prefira CTEs" pode generalizar
  os ganhos do fewshot sem precisar de exemplo para cada tipo de query

**Referência:** `experiments/results/m7_complex/manifest.jsonl` (2026-04-23)
Ver research-note: [2026-04-23-conservative-sql-flag.md](../research-notes/2026-04-23-conservative-sql-flag.md)

---

## F-Q21 — Falhas de SQL se dividem em dois tipos: detectáveis por invariante e silenciosas

**Conclusão:** De 39 falhas analisadas em M6/M6b/M7, **21% são Type A** (invariante
matemático violado — detectáveis sem GT) e **79% são Type B** (resultado plausível
mas errado — "falhas silenciosas"). Os dois tipos têm causas distintas e exigem
estratégias de recuperação diferentes.

| Tipo | Definição | % do total | Exemplo |
|------|-----------|-----------|---------|
| **Type A** | Resultado viola invariante conhecido | 21% (8/39) | SQL retorna ID numérico em vez de nome; SQL gera erro de coluna |
| **Type B** | Resultado dentro dos limites mas errado | 79% (31/39) | q_having retorna `1` (≤ COUNT DISTINCT, mas incorreto) |

**Por question type:**

| Question | Type A | Type B | Detectabilidade |
|---------|--------|--------|----------------|
| q_having | 0% | 100% | 0% — falha completamente silenciosa |
| q_top_e1_best_e2 | 100% | 0% | 100% — SQL error ou nome inválido |
| q_e2_most_e1 | 40% | 60% | 40% — ID numérico é detectável |

**Por que q_having é 0% detectável:** O modelo retorna `1` — matematicamente
plausível (1 ≤ total_distinct_fk1), mas errado porque representa o COUNT por
grupo e não o COUNT de grupos. O invariante `result ≤ COUNT(DISTINCT fk1)` é
satisfeito e não sinaliza nada. É o tipo de falha que só GT ou análise estrutural
de SQL detecta.

**Por que q_top_e1_best_e2 é 100% detectável:** Modelo usa coluna errada na
subquery interna → SQL lança `OperationalError`. O `executed_result` é uma
mensagem de erro, não um nome de entidade — trivialmente detectável pelo
invariante "resultado deve ser nome válido de dim2".

**Implicação metodológica:**
- Embedded invariants só ajudam em falhas de Type A — que em M6/M7 são minoria
- Para o tipo mais frequente (q_having Type B), a única solução robusta é
  fewshot ou diretiva de estilo (`--safe-sql`)
- Na prática, invariant checking é útil como camada de sanidade adicional,
  não como substituto para GT ou fewshot

**Referência:** `experiments/eval/run_minv_invariant_check.py` (2026-04-23);
análise sobre manifests m6_filter, m6b_having_fix, m7_complex.

---

## Ordem de aplicação ao desenhar novo experimento

1. **F-Q1, F-Q8, F-Q9** — antes de configurar cliente Ollama
2. **F-Q7** — ao escolher painel de modelos
3. **F-Q3, F-Q4, F-Q6** — ao desenhar prompts
4. **F-Q2, F-Q5** — ao qualificar modelos novos
5. **F-Q10, F-Q11, F-Q12** — ao interpretar resultados
