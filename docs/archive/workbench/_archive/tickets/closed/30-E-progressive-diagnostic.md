---
title: Diagnostic progressivo — escala minima ate complexidade maxima
type: experiment
status: OPEN
priority: 29
parent: 24-M-phase2-tcf-refactor
created: 2026-04-14
origin: Hipotese do usuario — "se nao funciona nem com pouco, que adianta passar muito?"
---

# Diagnostic Progressivo

## Hipotese

Se um modelo nao consegue responder `1+1+1 = ?` (3 numeros), nao adianta
testar com 500 rows de dados tabulares. Precisamos de uma **escala
progressiva** que isola ONDE o modelo falha:

1. Aritmetica pura (sem formato)
2. Formato minimalista (5 rows)
3. Formato com dados reais (20 rows, amostra representativa via shaper)
4. Escalando ate 500 rows

Cada nivel SO FAZ SENTIDO se o anterior funcionar.

## Niveis propostos

| Nivel | O que testa | Input | Perguntas |
|-------|------------|-------|-----------|
| **N0** | Aritmetica pura | "Some: 25, 30, 28" (3 numeros) | sum, avg |
| **N1** | Aritmetica media | "Some: 25, 30, 28, 35, 40, 22, 50" (7 numeros) | sum, count |
| **N2** | Formato CSV minimo | 5 rows × 3 cols Adult em CSV | avg age |
| **N3** | Formato TCF minimo | 5 rows × 3 cols Adult em TCF L0 | avg age |
| **N4** | Formato TOON minimo | 5 rows × 3 cols Adult em TOON | avg age |
| **N5** | Amostra representativa | 20 rows Adult (via shaper stratified) em CSV | avg, count, max |
| **N6** | Idem em TCF | 20 rows Adult em TCF L0 | avg, count, max |
| **N7** | Escala media | 100 rows Adult em CSV, TCF L0, TCF L2 | 5 perguntas |
| **N8** | Escala grande | 500 rows Adult em CSV, TCF L0, TCF L2 | 5 perguntas |

## Por que amostras representativas importam

Voce mencionou: "menores nao e top 10 ou top 50, e amostra representativa".

Isso e exatamente o que o **shaper com stratify_by** faz:

```python
# 20 rows representativas do Adult (proporcionais por sex + education)
result = Shaper().apply(ShapeRequest(
    dataset="adult-census",
    volume=20,
    stratify_by="education",
    order="random",
    seed=42,
))
```

Os 20 rows nao sao os primeiros 20 — sao 20 que **representam a distribuicao
real** de education (1-2 por cada um dos 16 niveis).

Isso testa se o modelo entende os dados COMO ELES SAO NA VIDA REAL,
nao uma amostra enviesada.

## Relacao com diagnostic 3-layer (F80-F84)

O diagnostic existente testou 3 camadas:
- Layer 0 (math_control): aritmetica pura com 509 numeros
- Layer 1 (decode_only): ler formato e listar valores
- Layer 2 (compute): formato + operacao

**Diferenca:** o diagnostic antigo usou 509 numeros FIXO (muito grande
para math_control). Este diagnostic comeca com 3 numeros e ESCALA.

Se o modelo falha com 509 mas acerta com 7, sabemos que o problema
e **escala**, nao **capacidade aritmetica**.

## Resultado esperado

Tabela por modelo × nivel, mostrando onde cada um "quebra":

```
              N0  N1  N2  N3  N4  N5  N6  N7  N8
gemma3:4b     OK  OK  OK  OK  OK  OK  OK  FAIL FAIL   ← quebra em 100+ rows
gemma3:12b    OK  OK  OK  OK  OK  OK  OK  OK   FAIL   ← quebra em 500 rows
qwen3:8b      OK  OK  OK  OK  OK  OK  OK  OK   OK     ← funciona em tudo
phi4          OK  OK  FAIL ...                          ← quebra no formato
```

Isso da uma **narrativa clara** para o paper: "modelo X entende ate N6,
modelo Y entende ate N8".

## Implementacao

Usar o runner de LLM accuracy existente com parametros ajustados:
- Gerar dados via shaper para cada nivel
- Niveis N0-N1 sao prompts manuais (sem formato)
- Niveis N2+ usam format_data() existente

## Tarefas

- [ ] Definir prompts para N0 e N1 (aritmetica pura)
- [ ] Gerar amostras representativas via shaper para N2-N8
- [ ] Implementar runner progressivo (para se nivel anterior falhar)
- [ ] Rodar com 5 modelos
- [ ] Documentar "breakpoint" por modelo
- [ ] Comparar com F80-F84 (diagnostic antigo)
