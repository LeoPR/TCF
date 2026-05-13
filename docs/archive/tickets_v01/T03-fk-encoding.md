# T03 — Encoding de Foreign Keys e Relações

**Status:** ABERTO  
**Tipo:** Design + Pesquisa  
**Deps:** T01

## Pergunta
Como representar relações FK no TCF de forma que o LLM entenda a ligação entre tabelas sem precisar expandir (JOIN) os dados?

## Problema Concreto
`vendas.id_pessoa` aponta para `pessoas.id`.  
No CSV expandido (JOIN), repetimos o nome da pessoa em cada linha de venda.  
No TCF, queremos evitar essa repetição.

## Opções

### A) FK como índice de linha (0-based) na tabela referenciada
```
## COL vendas n=41
pessoa: 0 1 0 2 3 4 5 ...   ← índice em pessoas (linha 0 = Ana, linha 1 = Bruno)
```
- DICT `pessoas.nome` está separado: `0=Ana 1=Bruno ...`
- **Pro:** Máxima compressão, sem repetição
- **Contra:** LLM precisa fazer lookup mental no DICT

### B) FK resolvida inline (JOIN no encoder)
```
## COL vendas n=41
pessoa_nome: Ana Bruno Ana Carla Diego Elisa ...
```
- **Pro:** LLM não precisa de lookup
- **Contra:** Mais verboso, não é columnar puro
- **Hipótese:** Melhor para perguntas sobre nome ("quantas vendas fez Ana?")

### C) FK como símbolo do dict (igual opção A, mas explicitando)
```
## DICT pessoas [key=id]
0=Ana 1=Bruno 2=Carla ...

## COL vendas n=41
pessoa[->pessoas]: 0 1 0 2 3 ...   ← anotação de FK no header
```
- Torna a referência explícita para o LLM
- O modelo sabe que `pessoa` é um ponteiro para `pessoas`

### D) Duas representações: compacta + hint
```
## COL vendas n=41
pessoa: 0 1 0 2 3 4 5 6 ...
# HINT: pessoa ref pessoas.nome → 0=Ana 1=Bruno 2=Carla 3=Diego 4=Elisa ...
```
- Hint em linha de comentário após a coluna
- LLM tem o mapa imediatamente após os dados

## Experimento Proposto
Testar opções A, B, C, D na pergunta:
- "Quantas vendas Ana fez?"
- "Qual produto foi mais vendido?"
- Comparar com CSV expandido (JOIN completo)

## Hipótese Inicial
Para perguntas por nome: **B** ou **D** devem ser melhores.  
Para perguntas numéricas (soma, média): **A** é suficiente e mais compacto.  
**Estratégia ótima:** usar A para FK numéricas puras, D para FK que aparecem em perguntas.

## Questões em Aberto
- [ ] O LLM consegue fazer lookup no DICT para resolver um FK?
- [ ] Qual o custo em tokens de inline (B) vs dict (A)?
- [ ] Com 30+ categorias, o DICT ainda cabe no contexto sem confundir o modelo?
