# T02 — Encoding de Colunas Numéricas

**Status:** ABERTO  
**Tipo:** Pesquisa + Implementação  
**Deps:** T01

## Pergunta
Para colunas numéricas (ex: `vl`), qual estratégia de encoding favorece que o LLM faça operações matemáticas (soma, média, contagem)?

## Opções

### A) Raw float (sem transformação)
```
vl: 2.5 11.0 1.0 3.75 2.9 ...
```
- **Pro:** LLM vê o valor real, pode somar diretamente
- **Contra:** Menos compacto que bins
- **Hipótese:** Melhor accuracy para operações aritméticas

### B) Bins inteiros (quantização uniforme)
```
vl: 2 9 0 3 2 3 2 4 5 6 9 1 7 0 2 8 ...  (16 bins, 0-15)
```
- **Pro:** Muito compacto (1 char por valor)
- **Contra:** LLM precisa conhecer os limites dos bins para recalcular
- **Hipótese:** Melhor para contagem/distribuição, ruim para soma/média exata

### C) Escala inteira (multiplicar por fator fixo)
```
# vl * 100 → inteiros
vl: 250 1100 100 375 290 450 320 ...
```
- **Pro:** Sem perda de precisão (para dados com 2 casas decimais)
- **Pro:** LLM opera com inteiros (mais confiável que float)
- **Contra:** Menos compacto que bins

### D) Quantização por percentil (bins não-uniformes)
- Bins com mesmo número de valores em cada faixa
- Mais informativo para distribuições assimétricas
- Complexidade maior no encoder/decoder

## Experimento Proposto
Testar as opções A, B, C com o Ollama:
- Pergunta 1: "Qual é a soma de vl?"  (ground truth: calcular do CSV)
- Pergunta 2: "Qual é a média de vl?"
- Pergunta 3: "Qual o maior valor de vl?"
- Medir: accuracy, tokens no prompt, latência

## Hipótese Inicial
**Opção A (raw float) deve ter melhor accuracy para aritmética.**  
Opção C pode ser comparável mas com inteiros.  
Bins (B) deve falhar em soma/média exata mas funcionar para ranking.

## Questões em Aberto
- [ ] O LLM consegue somar 41 floats num prompt só?
- [ ] Há diferença de accuracy entre modelos (gemma, llama, mistral) para floats vs ints?
- [ ] Truncar para 1 casa decimal (ex: 3.7 em vez de 3.75) afeta accuracy?
