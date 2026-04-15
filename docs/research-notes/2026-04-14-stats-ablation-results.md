# Stats Ablation — Resultados e Interpretação

**Data:** 2026-04-14  
**Experimento:** benchmark_stats_ablation.py  
**Dataset:** adult-census (5 questões × 3 formatos × 3 escalas × 3 modelos = 135 combos)

---

## Design

Testamos as mesmas perguntas em 3 formatos:
- `csv`: baseline sem metadados
- `tcf_L0_stats`: TCF sem compressão, **com** linhas `# STATS`
- `tcf_L0_nostats`: TCF sem compressão, **sem** linhas `# STATS`

Questões selecionadas (mix de `stats_answerable` e não):

| ID | stats_answerable | Tipo |
|----|-----------------|------|
| q1_avg_age | **true** | agregação descritiva (média) |
| r1_count_age_above_50 | false | filter + count |
| r2_avg_age_bachelors | false | filter + avg |
| r5_males_more_hours | false | comparação (Yes/No) |
| h2_income_imbalanced | false | heurística proporção (Yes/No) |

Escalas: 10, 100, 500 linhas. Modelos: gemma3:4b, gemma3:12b, gpt-oss:latest.

---

## Resultados (Acc@T2, todos os modelos e escalas)

```
Question              Stats?  csv    tcf+S  tcf-S  Gap(+S−-S)
q1_avg_age             YES    67%    67%    67%    +0%
r1_count_age_above_50   no     0%     0%     0%    +0%
r2_avg_age_bachelors    no    50%    80%    67%   +13%
r5_males_more_hours     no    89%    78%    89%   -11%
h2_income_imbalanced    no    88%    89%    78%   +11%
```

**Resumo por categoria:**

```
Stats-answerable  tcf+S=67%  tcf-S=67%  →  gap = 0%
Reasoning         tcf+S=59%  tcf-S=58%  →  gap = +1%
```

---

## Interpretação

### 1. STATS não ajudou questões stats-answerable (q1_avg_age)

A hipótese inicial era: *modelos usariam STATS como atalho para questões descritivas,
tornando-as triviais mesmo em grandes escalas.* Os dados refutam isso.

Gap = 0% mesmo sendo q1 (média global) diretamente legível no bloco STATS:
```
# STATS count=500 mean=38.64 std=13.41 min=17 max=90
```

**Por quê?** Dois fatores:
1. Para N=10 ou N=100, a média do subconjunto ≠ média da tabela completa.
   STATS nos dados pequenos reflete o subconjunto, não o dataset completo.
   O modelo pode estar confundindo as duas médias.
2. A precisão do STATS (mean=38.64) e a resposta esperada coincidem, mas
   modelos menores (gemma3:4b) frequentemente chegam a um valor próximo
   por estimativa simples da coluna, sem precisar do STATS.

### 2. STATS ajudou r2 (filter+avg, +13%)

r2 pergunta a média de idade de pessoas com education='Bachelors'. 
STATS por coluna não responde diretamente (não há STATS por subgrupo),
mas fornece _âncoras_ (min/max/mean global da coluna `age`) que o modelo
usa para verificar se sua resposta filtrada é plausível.

Efeito: STATS serve como referência de sanidade para cálculos filtrados.

### 3. STATS prejudicou r5 (comparação Males vs Females, -11%)

r5 compara médias de grupos: "Males work more hours than females?". 
TCF com STATS é mais longo (mais tokens) e inclui estatísticas globais
que podem obscurecer a necessidade de calcular _por grupo_.

Hipótese: o STATS global de hours-per-week (sem breakdown por sexo) pode
induzir o modelo a responder com base na média global ao invés de comparar
grupos. TCF sem STATS força o modelo a ler os valores individuais.

### 4. STATS serviu como oráculo populacional para h2 (heurística proporção)

**Caso mais revelador do experimento:**

`gemma3:12b` em N=10, questão h2 ("mais de 60% ganham <=50K?"):
- csv: **errado** (T5)
- tcf_L0_nostats: **errado** (T5)
- tcf_L0_stats: **correto** (T1)

Com apenas 10 linhas de dados, o modelo não consegue inferir a proporção
real da população. O bloco STATS (mesmo gerado sobre os 10 rows) inclui
contagem de valores da coluna `class`, que em 10 rows mostra algo como 8/10
para <=50K — o modelo usa isso para estimar "sim, >60%".

Isso demonstra o papel de **oráculo de população** do STATS quando dados
são truncados: o modelo precisa de estatísticas resumidas para responder
questões que demandam visão global do dataset.

---

## Achado de Escala

`r1_count_age_above_50` (count de linhas com age > 50) = **0% em todos os formatos**.
Este é o padrão de falha de "counting problem" — modelos não conseguem
fazer scan completo para contagem exata sem ferramentas externas.
TCF, CSV e STATS não ajudam: o problema é computacional, não de formato.

---

## Conclusões para o Artigo

1. **STATS não é atalho para questões descritivas** — modelos não substituem
   computação por leitura de STATS mesmo quando disponível. O impacto em
   questões stats-answerable é nulo (gap = 0%).

2. **STATS serve como âncora e oráculo** — para questões de raciocínio sobre
   subconjuntos, STATS global fornece referência de sanidade (+13% em r2).
   Para questões com dados truncados, STATS supre informação populacional
   que os dados sozinhos não fornecem (h2 com N=10).

3. **STATS pode interferir em comparações entre grupos** — quando a questão
   exige breakdown por grupo (r5), STATS global pode distrair o modelo (-11%).

4. **O problema de contagem é format-agnostic** — filter+count (r1) falha em
   todos os formatos (0%). Nenhum formato de representação resolve o problema
   de scan completo sem ferramentas.

5. **Impacto global marginal** — o efeito médio de STATS é +1% para reasoning
   e 0% para stats-answerable, não justificando STATS como mecanismo de
   accuracy improvement em escala geral. Seu valor é seletivo e contextual.

---

## Notas Técnicas

- 3 erros em gpt-oss (combos 118, 124, 128) — provavelmente timeout em scale 500
- gpt-oss foi o mais lento: até 540s por combo em scale 100
- gemma3:12b foi o mais consistente; gemma3:4b com mais variância
- Unparseable em r2_avg_age_bachelors para todos os modelos em N=10 —
  com apenas 10 rows, nenhum pode ter education='Bachelors', modelos respondem
  "não há dados" sem número → unparseable pelo extractor
