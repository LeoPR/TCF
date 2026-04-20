# Model Qualification Suite

**Objetivo**: Qualificar quais modelos rodam corretamente na máquina local
(RTX 3060 12GB + CPU 36 cores + Ollama Docker) com **perguntas canônicas
TCF-agnósticas** antes de consumi-los nos experimentos TCF.

**Não é o foco do projeto TCF**. É infraestrutura. Responde a pergunta:
*"Esse modelo funciona aqui, e com quais flags?"* — independente do
formato ou task que vamos testar depois.

## Motivação

Descobrimos (2026-04-20) que decisões sobre "modelo X falha em TCF" misturavam
três camadas:
1. **Hardware/Ollama**: partial offload, KV cache, num_ctx behavior
2. **Modelo**: bugs, limitações, thinking modes
3. **TCF**: o formato em si

Sem isolar as camadas 1+2, qualquer conclusão sobre a 3 fica confusa.
O qualification suite isola 1+2 com testes canônicos literatura-based.

## Uso

```bash
# Full flow: audit + testes canônicos em todos os modelos instalados
python qualify.py

# Só audit (sem rodar modelos — rápido, ~30s)
python qualify.py --audit-only

# Modelo específico
python qualify.py --model qwen3:8b

# Incluir testes de thinking (se o modelo suportar)
python qualify.py --model qwen3:8b --with-thinking

# Gerar relatório final a partir do manifest existente
python qualify.py --report
```

## Canonical questions

Definidas em `canonical_qa.json`. 5 categorias, todas com respostas
verificáveis determinísticas:

1. **Factual recall** (PT+EN): "Qual a capital do Brasil?" → "Brasília"
2. **Arithmetic**: "What is 17 + 28?" → 45
3. **Instruction following**: "Reply only with the word 'yes'" → "yes"
4. **Counting**: "How many words: 'The quick brown fox'" → 4
5. **Simple list**: "List 3 colors comma-separated" → any 3 colors

Cada pergunta rodada com **3 seeds distintos** (42, 7, 123) — N=3 replicação
para ter significância estatística mínima.

## Critério de "qualified"

Um modelo é qualified se:
- **Load**: carrega em <5min (disk → VRAM/RAM)
- **Accuracy canônica**: acerta ≥2/3 em pelo menos 4 das 5 categorias
- **Latência característica**: documentada (ms/call) para planejar tempo TCF
- **Não hang**: nenhuma pergunta excede 120s (indicativo de runaway generation)

## Outputs

- `results/capability_audit.json`: snapshot do ambiente (VRAM, modelos instalados,
  env vars do Ollama, configuração de contexto detectada)
- `results/qualification.jsonl`: uma linha por (modelo, pergunta, seed) com
  resposta, correctness, latency
- `results/qualified_models.json`: **lista final** que os experimentos TCF devem
  consumir — contém apenas modelos que passaram o critério

## Consumo pelo TCF

`experiments/eval/run_frontier_search.py` deve ler `qualified_models.json`
e restringir `DEFAULT_MODELS` aos qualificados. Modelos não-qualificados
podem ser rodados com `--force` mas geram warning.
