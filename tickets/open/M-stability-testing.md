---
title: Metodologia de estabilidade — separar sinal de coincidencia
type: methodology
status: OPEN
priority: CRITICAL
created: 2026-04-10
origin: Observacao de que alguns modelos "as vezes" acertam, pode ser coincidencia
---

# Metodologia de Estabilidade

## Problema

Todos os nossos experimentos atuais sao **single-run** (N=1 por combo).
Com temperature=0 e seed=42, assumimos determinismo perfeito. Mas:

1. **Ollama nao e 100% deterministico** mesmo com seed (float ops, GPU non-determinism)
2. **Alguns modelos tem variancia alta** — mesmo com t=0, podem dar respostas diferentes
3. **"Acertou" em single-run pode ser coincidencia** — especialmente em L2/L3 onde
   muitos modelos dao respostas vazias ou bizarras

**Sem N>1, nao podemos distinguir sinal estavel de ruido.**

## Exemplos concretos do stats_ablation

Alguns findings suspeitos:
- qwen3 L2_nostats q3_max: OK 516s — mas qwen3 L2_stats q3_max tambem OK
  (estavel neste caso)
- qwen3 L0_nostats q3_max: OK — e L0_stats q3_max tambem OK (estavel)
- gemma2 0% em tudo — claramente estavel (sinal claro)
- llama3.1 L2_stats q4_min: OK vs L2_nostats q4_min: OK — pode ser luck?

Sem repeticao, nao sabemos.

## Proposta: metodologia de estabilidade

### Criterio de estabilidade

Um resultado so e **estavel** se:
```
Repeticoes: N ≥ 3
Concordancia: ≥ 2/3 das respostas iguais (majority vote)
OU mean(correct) > 0.66
```

Resultados em 1/3 ou 2/3 sao marcados como "instaveis" e NAO contam
como "acerto" nem "erro" — contam como "ambiguo".

### Quando aplicar N≥3

Nao e pratico aplicar a todos os combos (multiplicaria tempo por 3).
Aplicar seletivamente:

**Sempre (findings centrais):**
- Top 4 modelos × formato × questao em Etapa 2
- Combos criticos de stats_ablation
- Diagnostic 3-layer (resultados surpreendentes)

**Amostra (validacao):**
- 20% aleatorio dos demais combos
- Combos que "mudam de resultado" entre runs

### Como implementar

```python
def run_with_stability(model, prompt, n=3, config=...):
    results = []
    for i in range(n):
        result = client.generate(model, prompt, options={**config, "seed": 42+i})
        results.append(score(result))

    majority = sum(results) > n / 2
    confidence = sum(results) / n
    stable = confidence >= 2/3 or confidence <= 1/3

    return {
        "majority_correct": majority,
        "confidence": confidence,
        "stable": stable,
        "raw_results": results,
    }
```

### Metrica composta

Ao inves de accuracy binaria, reportar:
- **Accuracy confirmada** (stable + correct): 2/3+ dizem sim
- **Accuracy provavel** (unstable + majority correct)
- **Ambiguo** (2/3+ variancia)
- **Erro confirmado** (stable + wrong)

## Criterio de eliminacao de modelos

Se um modelo tem **>30% dos resultados ambiguos**, eliminar do benchmark
principal. Nao e "bom" nem "ruim" — e ruidoso, e nao podemos tirar conclusoes.

## Relacao com literatura

- **Self-Consistency (Wang 2023):** majority voting ja proposto para boost de accuracy
- **Prompt Sensitivity (PromptSET 2025):** variancia como fenomeno a medir
- **POSIX (2024):** indice formal de sensibilidade

Nosso uso e diferente: nao queremos **melhorar** accuracy, queremos
**validar** se o resultado single-run representa comportamento real.

## Impacto no pipeline atual

Experimentos ja feitos (single-run) precisam ser re-classificados:
- Manter resultados como "provisorios"
- Rodar amostra de validacao (20% aleatorio com N=3)
- Se validacao confirma >80% dos resultados, single-run e confiavel para este modelo
- Se validacao contradiz >20%, todo benchmark precisa de N≥3

## Tarefas

- [ ] Implementar `run_with_stability()` helper
- [ ] Rodar validacao (20% aleatorio de Etapa 2) com N=3
- [ ] Rodar validacao de stats_ablation (critico — findings centrais)
- [ ] Classificar cada finding como "confirmed" vs "provisional"
- [ ] Documentar metodologia em article/04
- [ ] Nao re-rodar tudo — usar amostragem inteligente
