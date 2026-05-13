# H07 — Tamanho do Modelo × Formato (Interação)

**Status:** ABERTO  
**Deps:** H02, P06  
**LLM calls:** ~400 (subconjunto de H02)

## Hipótese

Modelos menores beneficiam mais do TCF vs JSONL do que modelos maiores, pois modelos grandes já conseguem decodificar qualquer formato.

**H7_0 (nula):** O ganho de accuracy (TCF − JSONL) é constante entre categorias de tamanho.

## Categorias e Modelos

| Categoria | Parâmetros | Modelos candidatos |
|-----------|-----------|-------------------|
| tiny | <3B | gemma3:1b, qwen2.5:0.5b, llama3.2:1b, smollm2 |
| small | 3–7B | llama3.2:3b, phi3:mini, gemma3:4b, qwen2.5:3b |
| medium | 7–14B | qwen3:8b, llama3.1:8b, gemma3:12b, mistral:7b |
| large | >14B | gemma3:27b, qwen2.5:14b, deepseek-r1:14b |

*(Selecionar 2–3 por categoria conforme disponibilidade no Ollama)*

## Design

```
4 categorias × 2 formatos (tcf_sorted_dict vs jsonl_expanded) × 10 perguntas × 5 runs
= 400 calls mínimo
```

**Estatística:** ANOVA mista — formato within-subject, categoria between-subject.

## Predição

```
Ganho TCF vs JSONL
  alto  │ tiny ●
        │      \
  médio │       small ●
        │             \
  baixo │              medium ●──── large ●
        │
        └─────────────────────────────────→ tamanho do modelo
```

Tiny models mostram maior ganho porque não conseguem fazer o "decode overhead" do JSONL no contexto limitado.

## Nota

Esta hipótese é **exploratória** (2–3 modelos por categoria = poder estatístico limitado). Reportar com intervalos de confiança, não como confirmação.
