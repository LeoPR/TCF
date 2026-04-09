---
title: Selecao inteligente de modelos — familias, tamanhos, quantizacoes
type: research
status: OPEN
priority: HIGH
---

# Selecao Inteligente de Modelos

## Descoberta de modelos

**Nao existe API publica** para listar modelos remotos do Ollama.

Script criado: `experiments/eval/llm_eval/ollama_registry.py`

Endpoints usados:
- `https://ollama.com/library` → scraping HTML: lista de ~219 modelos
- `https://ollama.com/library/{model}/tags` → scraping: tags + tamanhos em disco
- `https://ollama.com/search?q={query}` → scraping: busca por nome
- `https://registry.ollama.com/v2/library/{model}/manifests/{tag}` → OCI manifest
- `http://localhost:11434/api/tags` → modelos locais (API oficial)
- `http://localhost:11434/api/show` → detalhes de modelo local

Comandos:
```bash
python -m experiments.eval.llm_eval.ollama_registry installed
python -m experiments.eval.llm_eval.ollama_registry tags qwen3
python -m experiments.eval.llm_eval.ollama_registry family deepseek
python -m experiments.eval.llm_eval.ollama_registry recommend
```

## Mapa de familias e versoes (2026-04-09)

### Regra: usar versao mais recente. Pular obsoletas.

| Familia | Mais recente | Tamanhos disponiveis | Obsoletos (pular) |
|---------|-------------|---------------------|-------------------|
| deepseek | **deepseek-r1** (reasoning) | 1.5b, 7b, 8b, 14b, 32b, 70b | deepseek-coder (2 anos), deepseek-llm, deepseek-v2/v2.5 |
| | **deepseek-v3.x** (general) | 671b (nao cabe) | |
| llama | **llama3.2** (pequenos) | 1b, 3b | llama2, llama3 |
| | **llama3.1/3.3** (medios) | 8b, 70b | |
| | **llama4** | sem tamanhos uteis ainda | |
| gemma | **gemma3** | 270m, 1b, 4b, 12b, 27b | gemma, gemma2 |
| | **gemma4** (novo) | e2b(3.8b), e4b, 26b, 31b | |
| phi | **phi4** | 14b | phi, phi3, phi3.5 |
| | **phi4-mini** | 3.8b | |
| | **phi4-reasoning** | 14b (com thinking) | |
| qwen | **qwen3** | 0.6b, 1.7b, 4b, 8b, 14b, 30b | qwen, qwen2, qwen2.5 |
| | **qwen3.5** (novissimo) | 0.8b, 2b, 4b, 9b, 27b, 35b | |
| mistral | **mistral** (7b) | 7b | versoes anteriores |
| | **mistral-small3.2** | 24b (nao cabe Q4) | |
| gpt-oss | **gpt-oss** | 20b | 120b (nao cabe) |

### Excecao: deepseek-coder para hipotese H-coder

deepseek-coder e obsoleto (2 anos), mas foi treinado especificamente em codigo.
Hipotese: modelos treinados com codigo estruturado (JSON, CSV, YAML) podem
interpretar TCF melhor. Testar deepseek-coder:6.7b vs deepseek-r1:7b como ablacao.
Se r1:7b for melhor que coder:6.7b → coder e realmente obsoleto, sem vantagem.

## GPU constraint: RTX 3060 12GB

Maximo confortavel: ~14B Q4_K_M (~9GB disco, ~10GB VRAM)
Limite: ~20B MXFP4 (~14GB disco, ~12GB VRAM — usa tudo)

### Selecao final — 12 modelos (cobertura 0.6B-20B)

| # | Modelo | Params | Disk | Status | Nota |
|---|--------|--------|------|--------|------|
| 1 | qwen3:0.6b | 0.6B | 0.5GB | INSTALAR | Menor viavel |
| 2 | gemma3:1b | 1B | 0.8GB | INSTALAR | Escalabilidade gemma |
| 3 | qwen3:1.7b | 1.7B | 1.4GB | INSTALAR | Thinking pequeno |
| 4 | llama3.2:latest | 3.2B | 2.0GB | JA TEM | Meta baseline |
| 5 | gemma3:4b | 4B | 3.3GB | INSTALAR | Escalabilidade gemma |
| 6 | qwen3:8b | 8.2B | 5.2GB | JA TEM | Thinking |
| 7 | gemma2:9b | 9.2B | 5.4GB | JA TEM | Controle (0% TCF em E2) |
| 8 | gemma3:12b | 12.2B | 8.1GB | JA TEM | MELHOR (88% TCF L0) |
| 9 | phi4:latest | 14.7B | 9.1GB | JA TEM | Microsoft |
| 10 | qwen3:14b | 14B | 9.3GB | INSTALAR | Thinking grande |
| 11 | deepseek-r1:14b | 14.8B | 9.0GB | JA TEM | Reasoning |
| 12 | gpt-oss:latest | 20.9B | 13.8GB | JA TEM | OpenAI no limite |

Instalar: 5 modelos (~15GB download)
```bash
ollama pull qwen3:0.6b
ollama pull gemma3:1b
ollama pull qwen3:1.7b
ollama pull gemma3:4b
ollama pull qwen3:14b
```

### Modelos ja instalados que ficam DE FORA (redundantes)

| Modelo | Params | Por que excluir |
|--------|--------|-----------------|
| phi3:latest | 3.8B | Obsoleto por phi4 |
| mistral:latest | 7.2B | Saturado na faixa 7-8B, qwen3:8b e mais moderno |
| qwen2.5:latest | 7.6B | Obsoleto por qwen3:8b |
| deepseek-r1:7b | 7.6B | Redundante com qwen3:8b na mesma faixa |
| llama3.1:8b | 8.0B | Redundante na faixa 8B |

**NAO desinstalar** — so nao incluir no benchmark principal.
Podem ser usados em experimentos secundarios.

### Modelos opcionais para hipoteses especificas

| Modelo | Para que | Quando |
|--------|----------|--------|
| deepseek-coder:6.7b | H-coder (treinamento em codigo) | Se sobrar tempo |
| deepseek-coder:6.7b-q2_K / q8_0 | H-quant (quantizacao) | Se sobrar tempo |
| gemma4:e4b | Familia nova vs gemma3:4b | Se gemma4 estiver maduro |
| phi4-mini:3.8b | Phi scaling (3.8B vs 14B) | Se sobrar tempo |

## Hipoteses

### H-scaling: accuracy x params (mesma familia)
Curva: gemma3 1b→4b→12b e qwen3 0.6b→1.7b→4b→8b→14b
Pergunta: existe threshold minimo? Ou e gradual?

### H-coder: treinamento em codigo ajuda?
deepseek-coder:6.7b vs deepseek-r1:7b (mesma faixa, proposito diferente)
Se coder for melhor em TCF → treinar com dados estruturados importa.

### H-quant: quantizacao degrada TCF?
Um modelo em Q2_K vs Q4_K_M vs Q8_0 vs FP16
Se Q2 degrada TCF mais que CSV → RLE precisa de mais precisao de pesos.
Obs: quantizacoes menores podem ficar MAIS lentas (overhead de dequant).

## Tarefas

- [ ] Instalar 5 modelos faltantes
- [ ] Rodar Etapa 2 expandida (12 modelos × 3 formatos × 8 questoes = 288 combos)
- [ ] Gerar curva accuracy vs log(params) por familia
- [ ] Opcionalmente: deepseek-coder ablacao
- [ ] Opcionalmente: quantizacao ablacao
