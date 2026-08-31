---
title: LLM gera codigo auto-validador a partir de TCF — Program of Thoughts aplicado
type: experiment
status: OPEN
priority: HIGH
created: 2026-04-10
origin: Visao de LLM como "compilador de analise" sobre dados TCF
---

# LLM Gera Codigo Auto-Validador

## Contexto

F92 mostrou que LLMs NAO somam 509 numeros. Mas LLMs sabem **escrever
codigo que soma 509 numeros**. A ideia do Program of Thoughts (Chen et al.
2023) e: em vez de LLM calcular, LLM gera programa que calcula.

Se aplicamos PoT ao TCF:
1. LLM recebe dados em TCF
2. LLM gera script Python (ou SQL, JS) que responde a pergunta
3. Executamos o script
4. Comparamos resposta do script com ground truth

Isso contorna a limitacao aritmetica E a dependencia de STATS.

## Hipoteses

### H-codegen-1: LLMs geram codigo correto a partir de TCF?
Mesmo modelos que falham em Q&A direto (gemma2:9b = 0%) podem acertar
se a tarefa for "escreva codigo Python que responda X".

### H-codegen-2: TCF e mais facil de parsear em codigo que CSV?
Intuicao: formato columnar com blocos claros (`col:`) pode ser mais facil
para LLM gerar parser ad-hoc que CSV com quoting/escaping complexo.

### H-codegen-3: LLM lida com complexidade arbitraria via codigo?
Perguntas que exigem multi-step ("clientes que compraram produto X no mes Y")
sao impossiveis em Q&A direto mas triviais em codigo.

## Design experimental

### Niveis de dificuldade

| Nivel | Tarefa | Exemplo | Dificuldade |
|-------|--------|---------|-------------|
| C1 | Parse basico | "Gere Python que leia os dados TCF e imprima count" | Facil |
| C2 | Agregacao simples | "Gere Python que calcule sum(total)" | Media |
| C3 | Filtragem | "Gere Python que some total onde produto=Caneta" | Media |
| C4 | Multi-step | "Gere Python que liste top 3 clientes por valor gasto" | Dificil |
| C5 | Analise complexa | "Gere Python que identifique outliers em preco" | Muito dificil |

### Execucao segura

Scripts gerados pelo LLM devem ser executados em sandbox:
- subprocess com timeout
- sem acesso a filesystem alem do tmp
- sem rede
- memoria limitada

```python
def run_generated_code(code, tcf_data, timeout=30):
    # Write tcf_data to tmp, run code with subprocess
    # Capture stdout, compare with ground truth
    ...
```

### Scoring

- **Executa sem erro?** (passa/falha basica)
- **Resposta correta?** (exact match com ground truth)
- **Parsing correto?** (script soube ler o TCF)
- **Logica correta?** (script fez a operacao certa)

## Comparacoes criticas

### TCF vs CSV para codegen
Rodar mesmo experimento com CSV. TCF ganha se:
- LLM gera parser TCF correto mais frequentemente que parser CSV
- Resposta e mais acurada (menos bugs)

### Com vs sem STATS
STATS podem ajudar LLM a "validar" o codigo gerado
(compara output com STATS esperado).

## Relacao com outros tickets

- **E-llm-decompress**: ja testa LLM gerar CSV de TCF (D1-D4).
  E-code-generation e mais ambicioso: LLM gera **codigo que processa** TCF.
- **P-G33-metodologia**: PoT estava marcado como "futuro trabalho".
  Este ticket implementa essa hipotese.
- **E-qualitative-reasoning**: ortogonal — esse testa LLM direto,
  aquele testa LLM como gerador de programa.

## Impacto potencial

Se funcionar: **TCF vira um formato para AI agents**, nao so para Q&A.
Agents leem TCF, geram codigo, executam, interpretam resultado.
Bem mais poderoso que "modelo responde valor exato".

## Tarefas

- [ ] Definir banco de 10-15 tarefas com ground truth executavel
- [ ] Implementar runner de code generation (sandbox seguro)
- [ ] Rodar com 4 modelos × (TCF L0, L2) × (com/sem STATS)
- [ ] Comparar com CSV (mesmo design)
- [ ] Analisar: LLM gera parser TCF correto?
- [ ] Documentar em article/07 como secao "Program of Thoughts + TCF"
