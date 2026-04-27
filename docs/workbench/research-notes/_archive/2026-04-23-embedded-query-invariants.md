---
title: Embedded Query Invariants — hipótese de verificação lógica de SQL gerado por LLMs
date: 2026-04-23
type: research-note
status: HIPÓTESE — não implementada
---

# Embedded Query Invariants: âncoras matemáticas para validação de SQL gerado por LLM

## TL;DR

A ideia é pedir ao LLM que, além de gerar a consulta-objetivo, gere também uma
"âncora" — uma consulta simples cujo resultado é matematicamente previsível —
de forma que a consistência entre as duas valide (ou invalide) a lógica da
consulta complexa **sem depender do valor de ground-truth**.

Isso é diferente de execution-based scoring (que já fazemos): é verificação
da *coerência interna da lógica*, não do *resultado final*.

---

## A ideia em detalhe

### Forma 1 — Duas consultas: simples + objetivo

Prompt solicita duas queries:

```
Query A (âncora): SELECT COUNT(DISTINCT id_cliente) FROM vendas
Query B (objetivo): SELECT COUNT(*) FROM (
  SELECT id_cliente FROM vendas GROUP BY id_cliente HAVING COUNT(*) > 5
)
```

**Invariante verificável:** `B ≤ A` sempre.

Se o modelo gerar `B > A`, detectamos inconsistência sem precisar do GT.
Esse é exatamente o padrão de falha de q_having: modelo retorna `COUNT(DISTINCT)`
no outer query, que pode ser igual ao total de entidades, não ao filtrado.

### Forma 2 — Coluna piloto (embedded assertion)

Consulta única com coluna de autovalidação:

```sql
SELECT
  resultado,
  total_entidades,
  resultado <= total_entidades AS e_consistente
FROM (
  SELECT
    COUNT(*) AS resultado,
    (SELECT COUNT(DISTINCT id_cliente) FROM vendas) AS total_entidades
  FROM (SELECT id_cliente FROM vendas GROUP BY id_cliente HAVING COUNT(*) > 5)
)
```

Se `e_consistente = 0`, a consulta tem erro lógico detectável.

### Forma 3 — Decomposição em etapas com check intermediário

Para consultas em 2 níveis:
1. Etapa 1: gera soma por entidade (simples, auditável)
2. Etapa 2: filtra a partir do CTE
3. Check: resultado da etapa 2 ≤ COUNT(*) da etapa 1

---

## Análise crítica

### O que a ideia resolve bem

**Caso de uso principal:** quando o modelo gera SQL sintaticamente válido mas
semanticamente errado (o tipo mais difícil de detectar). Em M6, 93% dos casos
de falha em q_having são desse tipo: SQL executa, retorna número, mas é o
número errado.

**Invariantes robustos existem para vários padrões:**

| Padrão de query | Invariante | Exemplo |
|----------------|-----------|---------|
| HAVING count threshold | resultado ≤ COUNT(DISTINCT fk) | M6 q_having |
| GROUP BY + SUM + max | resultado IS IN dim table | group_sum |
| subquery above avg | resultado ≤ COUNT(DISTINCT fk) | M7 q_above_avg |
| TOP-N | resultado ∈ nomes conhecidos | qualquer q_top |
| filter + SUM | resultado ≤ SUM total (sem filtro) | filter_month |

### Limitações honestas

**1. O modelo falha junto com a query**
Quando o modelo não entende o padrão de duas etapas (que é exatamente onde ele
falha), pedir a âncora no mesmo prompt não ajuda: ele vai gerar a âncora errada
também. Em q_having com threshold=5: modelo que gera `COUNT(DISTINCT)` errado
provavelmente vai gerar a âncora `COUNT(DISTINCT)` como total (correto) mas a
lógica interna da query B ainda estará errada.

**2. Sobrecarga de prompt**
Pedir duas queries aumenta prompt_tokens ~30% e response_tokens ~50%.
Para modelos 7B, isso pode degradar a geração da query principal.

**3. Invariantes são query-type-specific**
Não há invariante genérico para todos os tipos. Precisaria de uma biblioteca
de invariantes por tipo de query — engenharia não-trivial.

**4. Não detecta erros de JOIN**
Se modelo usa coluna errada num JOIN (ex: `v.id_produto` em vez de `p.nome`),
a query executa, o COUNT pode ser até consistente com o invariante, mas o
resultado é semanticamente errado.

**5. Escopo do TCF**
TCF é o formato; SQL é um "plus" de capacidade. Adicionar meta-verificação
dentro do prompt sobrecarregaria o TCF como veículo. Melhor tratar como camada
de aplicação externa, não como parte do formato.

---

## Comparação com a literatura (2023-2025)

| Abordagem | Paper | Cobertura |
|-----------|-------|-----------|
| Execution feedback loop | Dynamic-SQL (2026), CHESS (2024) | Corrige após falha de execução — post-hoc |
| Self-consistency voting | DIN-SQL, DAIL-SQL | Múltiplas amostras, voto majoritário — sem invariante |
| Equivalência de SQL | LLM-SQL-Solver (2023), SQLGovernor (2025) | Compara duas queries entre si — não embeddado |
| Structural robustness | SQLStructEval (2025) | Avalia robustez pós-geração — não proativo |
| Intent-centered eval | ROSE (2025) | Mede alinhamento com intenção — não invariante |

**Lacuna confirmada:** Nenhum paper embute verificação lógica proativa durante
a geração. SQLStructEval é o mais próximo mas é avaliação pós-hoc, não
estratégia de geração.

**A ideia é genuinamente nova para NL2SQL com tabelas relacionais.**

---

## Onde isso se encaixa no projeto

### Não é TCF core
TCF é o formato de representação. A verificação por invariante é uma estratégia
de *aplicação* que qualquer formato poderia usar. O valor científico seria:
"LLMs que usam TCF + schema carrier + invariant anchoring atingem X% de
detecção de erros lógicos sem GT".

### Possível contribuição de paper separado
Se executado com rigor, isso seria uma contribuição de pesquisa independente:
"Query Invariant Anchoring for LLM-Generated SQL Verification" — citaria o
trabalho de SQLStructEval, CHESS e LLM-SQL-Solver como baseline, mostrando
que a abordagem proativa captura uma classe de erros que as outras perdem.

### Como experimento TCF leve (M_inv)
Versão mínima que não sobrecarrega o projeto:
- Adicionar invariant check como **pós-processamento** sobre SQLs já gerados
- Para cada SQL em M6/M7 que falhou: calcular o invariante matematicamente
  a partir das tabelas e verificar se o SQL gerado o violaria
- Reportar: "X% das falhas em q_having violam o invariante `resultado ≤ COUNT DISTINCT`"
- Isso NÃO require nova rodada de LLM — só análise dos manifests existentes

---

## Proposta de experimento M_inv (baixo custo)

**Input:** manifests M6 e M7 existentes (SQLs já gerados)
**Processo:**
1. Para cada SQL que falhou, executar: (a) o SQL gerado pelo LLM; (b) a âncora
   calculada diretamente das tabelas (não via LLM)
2. Checar se a invariante é violada
3. Classificar falhas: (A) invariante violada → detectável sem GT; (B) invariante
   ok mas resultado errado → falha silenciosa mais grave

**Output:** taxa de detecção por invariante, por question type, por modelo

**Custo:** ~2h de engenharia, sem novas chamadas ao LLM.

**Hipótese:** para q_having, >50% das falhas serão do tipo (A) — detectáveis.
Para q_above_avg (M7), idem. Para q_e2_most_e1 (M7), maioria será tipo (B).

---

## Status

- [ ] M_inv — análise post-hoc sobre M6/M7 (após M7 concluir)
- [ ] Avaliar: vale um paper separado sobre invariant anchoring?
- [x] Ideia documentada e situada na literatura
