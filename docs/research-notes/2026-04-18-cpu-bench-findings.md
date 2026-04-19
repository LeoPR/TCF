---
title: CPU-only ablation — 44 combos em gemma3:4b (notação, idioma, bridge, alias)
date: 2026-04-18
type: research-note
status: FINDINGS_PRELIMINARES
related:
  - docs/research-notes/2026-04-18-rle-notation-tokenization.md
  - experiments/eval/run_rle_notation_bench.py
  - experiments/eval/run_language_matrix.py
  - experiments/eval/run_bridge_instructions.py
  - experiments/eval/run_alias_bench.py
constraints:
  - GPU ocupada por outro processo (torch direto na VRAM) por ~8h.
  - Todo o teste rodou em CPU (Xeon E5-2697 v4, 36 cores, num_thread=24-12)
  - num_gpu=0 respeitado em 100% dos combos (size_vram=0 monitorado por 60min)
---

# CPU-only ablation — achados de gemma3:4b

## Protocolo

Infraestrutura validada:
- `num_gpu=0` + `num_thread=N` em todas as chamadas Ollama
- Monitor VRAM (10s interval) logando tanto nvidia-smi quanto `/api/ps` por modelo
- Outro processo consumindo ~11.8GB VRAM / 100% util GPU sem interferir

4 benchmarks sequenciais, total 44 combos:

| Bench | Dataset | Combos | Tempo |
|-------|---------|--------|-------|
| RLE notation | retail n=200 | 8 | 60min |
| Language matrix | retail n=50 | 12 | 11min |
| Bridge instructions | retail n=50 | 16 | 14min |
| Alias @A vs int | retail n=50 | 8 | 7min |

## Findings

### F-1: L3 integer > L2 RLE para small models

**Achado mais forte.** gemma3:4b obteve **75% (3/4)** em perguntas analíticas usando L3 com dict+integer-indices, contra **0-25%** no mesmo dataset em L2 com qualquer notação RLE.

Perguntas acertadas em L3 integer:
- `q_count` → 115 ✓
- `q_top_product` → Grampeador ✓
- `q_top_customer` → Rodrigo ✓

Perguntas erradas:
- `q_distinct_customers` → 4 (esperado 5)

**Hipótese**: dict header explícito + índices integer é mais amigável que RLE textual pra modelos pequenos. CSV-like, pattern-matchable.

**Implicação prática**: TCF L3 pode ser o default recomendado para uso com modelos <7B. L2 tem melhor compressão em runs curtos mas perde em compreensão.

**Pendente**: validar em qwen2.5:7b, qwen2.5-coder:7b, e eventualmente modelos cloud.

### F-2: @A aliases prejudicam accuracy em small model

Hipótese inicial: `@A=batata` seria parsing-friendly (sinal "variável" vs "número").
Resultado: **@A cai para 25% vs 75% do integer**. Modelo fica confuso com notação não-padrão.

Onde @A acertou (1/4): `top_customer = Rodrigo`. Onde errou:
- count → "94" (alucinou número)
- top_product → Caderno (pegou valor errado)
- distinct → texto longo, não parseou

**Hipótese refinada**: small models são CSV-nativos. Anything que desvia de `N,val1,val2` polui o parsing. `@A` introduz dois tokens e um símbolo não-numérico onde o modelo espera número.

**Pendente**: testar em qwen2.5:7b — talvez modelos capazes neutralizem ou até beneficiem do @A (legibilidade).

### F-3: Bridge instructions não compensam modelo fraco

4 variantes de system prompt (V0 minimal → V3 pseudocode) com notação `N val` fixa:

| Variante | Acc | Observação |
|----------|-----|------------|
| V0 minimal | 25% | só acerta count (provavelmente do header) |
| V1 atual | 25% | mesmo |
| V2 pedagógico | 25% | mesmo |
| V3 pseudocode (EN) | **0%** | inglês quebra até o count |

**Achado**: prompt engineering NÃO recupera capacidade ausente. Se o modelo não processa RLE, explicar melhor não ajuda.

**Consequência**: `N val` (tokenização 25% mais barata) só vale pena em modelos **já capazes** de parsear RLE. Pra small models, RLE textual é incompreensível — melhor L3 integer (F-1).

### F-4: Pista suspeita sobre idioma — precisa teste mais forte

Resultado bruto:
- `pt_pt` (data+prompt PT): **33%** (1/3) — acertou count
- `pt_en`: 0%
- `en_pt`: 0% (halucinou "Mouse" como top product)
- `en_en`: 0%

**Esta pista é altamente suspeita** por várias razões:
1. Gemma3 foi treinado majoritariamente em inglês (relatório técnico Google)
2. Small-n (3 perguntas) — pt_pt acertar só o count é consistente com **leitura de header** (`## vendas n=115`), não com compreensão
3. en_pt e en_en falharam em count — mas o header EN *também* tem `n=115`. Por que o modelo não leu?
4. Sem replicação com seeds diferentes, não dá pra descartar artifact

### F-5: Sinal de differenciação entre notações (mesmo todas erradas)

Smoke RLE em n=200, gemma3:4b, `q_count` (esperado 509):
- `N*val` → 196 (contou linhas RLE, não expandiu)
- `N val` → **19** (catastrófico)
- `N xval` → 196
- `val xN` → 196

**`N val` foi dramaticamente pior** (19 vs 196). Confirma parcialmente a hipótese de que `N val` confunde parsing mais que as outras. Mas **todas falharam** — não dá pra usar pra recomendação final.

## Revisão crítica do F-4 (idioma)

O resultado `pt_pt > en_en` em modelo inglês-treinado é **improvável de ser real**. Possíveis explicações:

### Hipótese A: Artifact de header
Modelo pode ter um heurístico "procure `n=<número>` no texto e retorne". Header PT (`## vendas n=115 sorted_by=qtd`) e EN (idem) deveriam funcionar igual. Mas o prompt PT tem palavras como "Quantas linhas", "coluna 'total'" que podem estar co-ocorrendo com a leitura do header. Prompt EN pode ter desviado a atenção.

### Hipótese B: Coincidência por n pequeno
3 perguntas é mínimo. 1/3 = 33% pode ser pura variância aleatória. Precisamos **replicação com ≥3 seeds diferentes**.

### Hipótese C: Tokens mais "custosos" forçam atenção
Nomes PT (Vitória, Rodrigo, São Paulo) tokenizam em mais tokens individualmente que nomes EN. Isso pode fazer o modelo "pausar" mais e prestar atenção no estruturador ao invés de rotinas automáticas. Intuitivo mas sem suporte teórico.

### Hipótese D: Bias do benchmark (matched priors)
Se o modelo sente "tabela em português" + "questão em português" como mais "auto-consistente", pode ativar caminhos de raciocínio mais rigorosos. Mismatch ativaria "translation mode" que é lossy.

## Teste mais forte proposto

Para ter **certeza** sobre F-4:

```
Design fatorial completo:
  - 4 seeds distintos (42, 7, 123, 999)
  - 4 cells (pt_pt, pt_en, en_pt, en_en)
  - 6 perguntas (count, sum, avg, top_product, top_customer, distinct)
  - 2 modelos (gemma3:4b, qwen2.5:7b)
  = 192 combos
```

Adicionalmente:
- **Header ablation**: gerar variante sem `## vendas n=N` (ou mascarada) — testa se "115" vem de leitura direta
- **Prompt "zero-info"**: perguntar "que informação a primeira linha do header contém?" — se o modelo ler `n=115`, ele reporta isso; se não, descobre do corpo

Em CPU-only (num_thread=24, n=50): 192 × 55s = ~175min ≈ 3h. Viável em 1 noite se a GPU seguir bloqueada.

## Conclusões operacionais

1. **Recomendação preliminar**: TCF pode documentar L3 como "small-model friendly". L2 é mais compacto, mas L3 é mais comprehensível pra modelos fracos.

2. **`N val` é tentativa abortada** para small models. Só vale a pena testar em modelos capazes (≥7B) + benchmark maior.

3. **@A aliases**: descartar sem teste adicional em modelo capaz. Se 7B confirmar que "@A >= integer", reconsiderar; senão, manter integer.

4. **Idioma PT vs EN**: **achado suspeito, não confiável**. Replicação multi-seed necessária antes de qualquer recomendação.

5. **Bridge prompts**: prompt engineering não compensa small model. Focar em escolher bem o NÍVEL (L3 > L2), não o texto do prompt.

## Próximo ciclo

Dependendo do resultado do D em qwen2.5:7b:
- Se integer vence em 7B também → @A definitivamente morto, close as hypothesis
- Se @A vence em 7B → reabrir, estudar escalabilidade
- Re-rodar language matrix com 4 seeds × qwen2.5:7b para resolver F-4
