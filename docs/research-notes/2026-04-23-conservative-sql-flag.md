---
title: Conservative SQL flag — guiar modelos para padrões SQL mais simples e equivalentes
date: 2026-04-23
type: research-note
status: HIPÓTESE — experimento M8-variant proposto
---

# Conservative SQL: guiar LLMs para padrões SQL mais robustos via hint de prompt

## Motivação empírica (dados M6)

Em M6, q_having falhou 93% das vezes com um padrão **sempre igual**:

```sql
-- O que todos os modelos geraram (ERRADO):
SELECT COUNT(DISTINCT id_cliente) FROM vendas GROUP BY id_cliente HAVING COUNT(*) > 25
-- Retorna: 1  (conta distinct por grupo = sempre 1)
-- Esperado: 3
```

A falha não é de sintaxe nem de execução — é semântica. O modelo entende
HAVING mas não entende que precisa de dois níveis de agregação.

M6b fix (adicionar exemplo de subquery no fewshot) corrigiu para 89%.
Mas a solução foi reativa: mostramos o padrão correto depois de observar a falha.

**A hipótese agora é proativa**: e se o prompt incluísse uma diretiva de estilo
SQL que orientasse o modelo a **nunca usar HAVING direto** e sempre decompor
em subquery? Isso evitaria a classe de erro em vez de corrigi-la.

---

## A ideia: `--conservative-sql` (nome provisório)

Uma flag de geração que adiciona ao prompt uma diretiva de estilo SQL:

```
## Estilo SQL (modo conservador)
- NUNCA use HAVING diretamente em queries com COUNT/SUM externos.
- Para filtrar em agregações, use derivd table com alias explícito:
    SELECT COUNT(*) FROM (SELECT col, COUNT(*) AS cnt FROM t GROUP BY col) WHERE cnt > N
- Prefira CTEs (WITH ...) para cada passo de transformação.
- Evite subconsultas correlacionadas implícitas.
- Cada nível de agregação deve estar em um bloco separado (subquery ou CTE).
```

O resultado esperado é que o modelo gere:

```sql
-- HAVING-free equivalent (mais explícito):
SELECT COUNT(*) FROM (
  SELECT id_cliente, COUNT(*) AS cnt FROM vendas GROUP BY id_cliente
) WHERE cnt > 25
```

Isso é semanticamente idêntico à versão com subquery+HAVING, mas:
1. Não usa HAVING (evita a armadilha de scoping)
2. Nomeia o COUNT intermediário (`cnt`)
3. Filtra com WHERE convencional

---

## Análise da equivalência matemática

Para o padrão q_having, 3 SQLs são equivalentes:

| Variante | SQL | Usa HAVING | Risco |
|----------|-----|-----------|-------|
| A — subquery+HAVING | `SELECT COUNT(*) FROM (SELECT fk FROM t GROUP BY fk HAVING COUNT(*) > N)` | Sim (inner) | Baixo |
| B — HAVING-free | `SELECT COUNT(*) FROM (SELECT fk, COUNT(*) AS c FROM t GROUP BY fk) WHERE c > N` | Não | Baixo |
| C — errado | `SELECT COUNT(DISTINCT fk) FROM t GROUP BY fk HAVING COUNT(*) > N` | Sim (outer) | **ERRO** |

A diferença entre A e C é sutil: HAVING no inner vs no outer. Os modelos
sem fewshot geram C. Com fewshot (M6b), geram A. Com `--conservative-sql`
gerariam B.

**B pode ser mais fácil de gerar** porque:
- WHERE é mais familiar que HAVING em qualquer contexto
- A coluna intermediária (`cnt`) torna o filtro explícito e auditável
- Não há ambiguidade de qual COUNT está sendo filtrado

---

## Mapeamento de equivalências para outros padrões

O conceito se generaliza além do HAVING:

| Padrão potencialmente problemático | Equivalente conservador |
|-----------------------------------|------------------------|
| `GROUP BY x HAVING COUNT(*) > N` | `(SELECT x, COUNT(*) AS c ... GROUP BY x) WHERE c > N` |
| Subquery correlacionada em WHERE | CTE explícita que materializa o subconjunto |
| `COUNT(DISTINCT x)` em GROUP BY | Dois passos: DISTINCT + GROUP BY separados |
| `MAX(SUM(...))` implícito | CTE com sums, depois SELECT MAX |

Essa é uma **filosofia de decomposição**: cada transformação em um bloco
separado, nenhuma dependência implícita de escopo.

---

## Onde implementar

**Opção 1 — Prompt hint (custo zero):**
Adicionar ao `PROMPT_TEMPLATE` ou ao fewshot block uma seção de estilo.
Testável como variante M8c vs M8 baseline (mesmo modelo, prompt diferente).

**Opção 2 — Flag de CLI:**
`--conservative-sql` no runner modifica o fewshot/template usado.
Permite comparação direta: `sql_stats_fs` vs `sql_stats_fs_conservative`.

**Opção 3 — Rewriter pós-geração (SQL → SQL):**
Transformar o SQL gerado para o equivalente conservador via parsing.
Mais complexo, mas permitiria recovery sem re-invocar o LLM.

**Recomendação:** Opção 1/2 como variante em M8 — baixo custo, alta informação.

---

## Nome mais adequado

`--conservative-sql` é ok mas pode confundir com "SQL antigo/legado".
Opções melhores:

| Nome | Semantica |
|------|-----------|
| `--decomposed-sql` | Cada passo em bloco separado |
| `--explicit-agg` | Agregações explícitas em cada nível |
| `--safe-sql` | SQL sem armadilhas de scoping |
| `--no-having` | Literal, apenas para HAVING |
| `--subquery-first` | Preferência por subquery em vez de cláusulas inline |

**Sugestão:** `--safe-sql` como flag de alto nível, com implementação inicial
focada em HAVING. Nome simples, semântica clara para quem usa.

---

## Conexão com embedded-query-invariants

As duas ideias se complementam:
- `--safe-sql` previne a geração de SQL errado via hint de estilo
- `--invariant-check` detecta quando SQL errado foi gerado mesmo assim

A combinação seria: hint conservador + validação por invariante = pipeline
de geração mais robusto sem depender de GT.

---

## Próximos passos propostos

1. Implementar como variante em M8 (modelos comerciais): comparar
   `sql_stats_fs` vs `sql_stats_fs_safe` nos mesmos combos
2. Hipótese: `--safe-sql` recupera >95% de acurácia em q_having sem fewshot
   específico de HAVING — o style hint é mais genérico e robusto
3. Se confirmado: propor como mecanismo de robustez no paper
   ("prompt-level SQL style guidance as a zero-shot recovery strategy")

---

## Status

- [ ] M8-safe-sql: variante com --safe-sql em modelos comerciais
- [ ] Testar sem fewshot de HAVING (só com style hint) vs M6b baseline
- [x] Hipótese documentada com equivalências matemáticas
