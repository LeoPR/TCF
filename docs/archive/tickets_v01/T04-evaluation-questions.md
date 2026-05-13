# T04 — Perguntas de Avaliação para o LLM

**Status:** RASCUNHO  
**Tipo:** Experimento  
**Deps:** T01, T02, T03

## Pergunta
Quais perguntas usar para avaliar se o LLM consegue operar sobre dados no formato TCF?  
Como calcular o ground truth para scoring automático?

## Categorias de Perguntas

### Categoria 1: Aritmética Simples (uma coluna)
| ID | Pergunta | Ground Truth |
|----|----------|--------------|
| Q1 | Qual é a soma de `vl`? | **217.55** |
| Q2 | Qual é a média de `vl`? | **5.3061** |
| Q3 | Qual é o maior valor de `vl`? | **12.40** |
| Q4 | Qual é o menor valor de `vl`? | **1.00** |
| Q5 | Quantas linhas há em `vendas`? | **41** |

### Categoria 2: Aritmética com Filtro (requer FK lookup)
| ID | Pergunta | Ground Truth |
|----|----------|--------------|
| Q6 | Quantas vendas Ana fez? | **3** (id_pessoa=1) |
| Q7 | Qual o total gasto por Ana? | **8.70** |
| Q8 | Qual produto aparece mais vezes? | **Caneta** (id=22, 5 vezes) |
| Q9 | Qual o produto mais caro em média? | calcular do CSV |

### Categoria 3: Comparação e Ranking
| ID | Pergunta |
|----|----------|
| Q10 | Qual pessoa gastou mais no total? |
| Q11 | Quais 3 produtos têm maior ticket médio? |
| Q12 | Quantos produtos distintos foram vendidos? |

## Estratégia de Scoring
- **Resposta numérica:** aceitar ±1% de erro (tolerância de arredondamento)
- **Resposta de contagem:** exata
- **Resposta de nome:** exact match (case-insensitive)

## Formatos a Comparar
Para cada pergunta, testar:
1. CSV expandido (baseline atual do projeto)
2. JSON Lines expandido
3. TCF com raw float (T02-A)
4. TCF com FK inline (T03-B)
5. TCF com FK como índice + dict (T03-A)

## Questões em Aberto
- [ ] Calcular ground truth exato para Q1-Q12 a partir dos CSVs
- [ ] Definir formato de resposta esperada (número puro vs frase)
- [ ] Como lidar com respostas em formato de lista vs número?
- [ ] Vale testar com e sem chain-of-thought no prompt?
