# Avaliacao Critica — 2026-04-10

Documento de revisao honesta motivado por questionamento do usuario:
**"Preciso de uma metrica muito solida pra ter certeza absoluta que
comprimir por coluna e uma boa estrategia."**

---

## 1. O que sabiamos (e estava errado)

### 1.1 Sobre TOON — informacoes imprecisas anteriores

Em revisoes anteriores, ha duas afirmacoes que precisam de ajuste:

**Anterior:** "TOON tem benchmarks empiricos solidos"
**Realidade:** depende da fonte.

Pesquisa detalhada de hoje revelou:

| Fonte | Tipo de benchmark | Forca |
|-------|-------------------|-------|
| **LogRocket article** | **Calculado** (tiktoken, sem LLM real) | Fraco |
| **GitHub TOON oficial** | **Empirico** (209 Q × 4 modelos) | Medio |
| **arxiv 2603.03306** | **Empirico** (plain vs constrained vs TOON) | Forte |
| **arxiv 2601.12014** | **Empirico** + sustentabilidade | Forte |

Leituras dos papers arxiv revelam que as conclusoes **nao sao limpas:**

- **arxiv 2603.03306:** "TOON shows promising accuracy/token ratio **for in-domain generation**, though this advantage is often reduced by the 'prompt tax' of instructional overhead **in shorter contexts**." **"Plain JSON actually achieved superior one-shot accuracy, undermining TOON's primary value proposition."**
- **arxiv 2601.12014:** "TOON yields markedly more compact outputs and lower emissions, **but lower structural correctness when models lack native support**." "TOON isn't objectively better — it's a strategic choice for teams prioritizing environmental efficiency over maximum structural correctness."

**Conclusao honesta:** TOON tem valor mas **nao e unanimemente melhor que JSON**. Os trade-offs sao reais e documentados. Nosso TCF pode ser comparado em igualdade, nao como "resposta a formato consagrado".

### 1.2 O artigo LogRocket engana parcialmente

O artigo LogRocket apresenta numeros como "**62.7% savings**" de forma que parece definitiva, mas:

- **NAO roda em LLM real** — so conta tokens via tiktoken
- **NAO mede accuracy** — so mede custo
- **NAO usa modelos abertos** (como nossos Ollama)
- Usa exemplo artificial (100 objetos uniformes — caso otimo)
- Custo calculado ($169 savings) e **linear em tokens**, assumindo LLM processa igual

**Implicacao:** a maior parte das "vantagens de TOON" difundidas em blogs e **estimativa calculada, nao validada empiricamente**. O proprio projeto TOON tem benchmarks reais (209 Q x 4 modelos) — e eles mostram ganho modesto (76.4% vs 75.0% accuracy, +1.4pp).

### 1.3 Nossos proprios findings — lacuna metodologica

Descobri hoje que:

**Nossos runners gravam `prompt_chars`, mas o ollama_client JA RETORNA `prompt_tokens` reais (do Ollama, tokens do proprio modelo).**

- `experiments/eval/llm_eval/ollama_client.py:54` captura `prompt_eval_count`
- Os runners (etapa1, etapa2, g30, diagnostic, stats_ablation, scale) **nao gravam** no manifest
- Temos os dados mas nao estamos persistindo

**Isso e uma correcao trivial** — adicionar `result["prompt_tokens"] = gen["prompt_tokens"]` em cada runner. Todos os experimentos futuros terao tokens reais GRATIS.

**Para experimentos passados:** nao podemos recuperar prompt_tokens, mas podemos:
- Re-tokenizar o mesmo prompt offline (mesma config = mesmos tokens)
- Usar tiktoken como aproximacao para GPT-family
- Re-rodar amostra pequena para validar

---

## 2. Questoes cientificas reais

### 2.1 O que realmente precisa ser provado

Para o paper fazer sentido, precisamos demonstrar uma dessas:

**H-core-1:** "Orientacao columnar (agrupar por coluna) reduz tokens em tokenizers BPE reais, nao so caracteres."
- Validavel: medir em tiktoken + ollama tokenize
- Se verdadeiro: fundamento do paper

**H-core-2:** "LLMs (open source) tem accuracy >= row-oriented com TCF+STATS em dados tabulares repetitivos."
- Validavel: F50 ja mostra isso (TCF L0 49% > CSV 19% em Etapa 2)
- **MAS:** precisa revalidar com TOON incluido no mesmo benchmark

**H-core-3:** "Compressao columnar textual beneficia gzip mais que row-oriented."
- Validavel: F70-F73 ja mostra em parte (TCF+gzip 29% < CSV+gzip em 5K rows)
- **MAS:** F70-F73 compara TCF vs CSV/JSONL, nao vs TOON

**H-core-4:** "STATS hints embutidos sao unicos e compensam limitacoes aritmeticas dos LLMs."
- Validavel: F81-F94 ja mostra isso (delta -25 a -62pp sem STATS)
- Forte, independente de TOON

### 2.2 H-core-4 e o mais solido

**STATS shortcut** e a inovacao que **nenhum outro formato tem:**
- CSV: nao tem STATS
- JSON: nao tem STATS
- TOON: nao tem STATS
- Parquet: tem estatisticas mas em metadata binario, nao acessivel a LLM via prompt
- TCF: **unico** com hints textuais no prompt

Isso sozinho justifica o TCF, mesmo se orientacao columnar for marginalmente melhor que row-oriented.

### 2.3 O nicho redefinido

**Reposicionamento honesto:**

TCF NAO e "o melhor formato para LLMs". TCF e:

> **"O primeiro formato textual que embute hints meta-cognitivos**
> **(STATS) compensando limitacoes aritmeticas dos LLMs,**
> **organizados em estrutura colunar que permite compressao**
> **textual adicional (RLE, sort, dict)."**

Ou seja, nao vendemos "colunar vence row-oriented". Vendemos **"hints cognitivos + estrutura colunar compressivel"** — duas coisas que nenhum outro formato tem simultaneamente.

---

## 3. Gaps metodologicos identificados

### 3.1 Gap 1: tokens nao medidos

**Impacto:** alto
**Correcao:** trivial (salvar `prompt_tokens` no manifest)
**Custo:** zero (dado ja existe)

### 3.2 Gap 2: TOON nao integrado no benchmark

Tinhamos um "TOON stub" no formats.py legado (archive/v01). Nao ha encoder TOON real, nunca foi testado em Etapa 2.

**Impacto:** alto (paper precisa comparar contra TOON para ter credibilidade)
**Correcao:** implementar encoder TOON real (2-3h)
**Custo:** re-rodar Etapa 2 expandida com TOON (mais 12 modelos x 8 Q = 96 combos)

### 3.3 Gap 3: single-run sem validacao de estabilidade

Ja registrado em M-stability-testing, mas ignorado nos experimentos ate agora. Alguns findings podem ser coincidencia.

**Impacto:** medio (findings F81, F90 sao robustos — 4 modelos × 8 Q, replicated pattern; F85-F89 com 1 modelo sao mais fragieis)
**Correcao:** rodar 20% aleatorio com N=3
**Custo:** ~40 combos adicionais

### 3.4 Gap 4: tokenizer escolhido = tokenizer unico

Nosso Ollama da `prompt_eval_count` **do modelo que esta rodando**. Entao:
- gemma3 tokenizer quando roda gemma3
- qwen3 tokenizer quando roda qwen3
- llama tokenizer quando roda llama

Isso e **OTIMO na verdade** — cada modelo mede com seu proprio tokenizer. Temos a ground truth real, nao aproximacao.

Para TOON que usa tiktoken (OpenAI), podemos instalar tiktoken e medir com GPT-4 tokenizer como ponto adicional.

### 3.4.1 Versao do Ollama e endpoints de tokenizacao

**Verificado 2026-04-10:**

- Nossa versao: **0.20.0**
- Ultima disponivel: **0.20.5** (released 2026-04-09, ontem!)
- Changes 0.20.0 → 0.20.5: Gemma4 support, flash attention, tool calling, TUI fixes
- **NENHUMA mudanca em tokenization API** entre 0.20.0 e 0.20.5

**PR /api/tokenize:** [#12030](https://github.com/ollama/ollama/pull/12030)
- Criado em Agosto 2025
- **AINDA NAO MERGED** em abril 2026 (~8 meses em review)
- Pedidos da comunidade regulares mas sem merge
- Pode nao entrar tao cedo

**Conclusao:** nao ha endpoint dedicado de tokenizacao no Ollama, nem em 0.20.0 nem em 0.20.5. A melhor forma disponivel e usar `/api/generate` com `num_predict=1` (gera 1 token rapido) e pegar `prompt_eval_count`.

**Custo desse approach:**
- 1 chamada = processa prompt inteiro + gera 1 token
- Gemma3:1b: ~200ms por prompt (rapido)
- qwen3:8b: ~2s por prompt
- gemma3:12b: ~3s por prompt

Nao e gratuito mas e pratico. Para 500 combos × tokenizer validation:
~500 × 2s = ~17 min total. Aceitavel.

**Alternativa local offline:**
- Para modelos que usam tokenizers publicados (Llama, Gemma, Qwen), instalar `transformers` e carregar so o tokenizer (sem o modelo):
```python
from transformers import AutoTokenizer
tok = AutoTokenizer.from_pretrained("google/gemma-2-9b")
tokens = tok.encode("pessoa: Ana Bruno Carla")
len(tokens)  # exato, offline, gratis
```
- Gemma3 tokenizer: `google/gemma-2-9b` (mesma familia)
- Qwen3 tokenizer: `Qwen/Qwen2.5-7B` (mesma familia)
- Llama3 tokenizer: `meta-llama/Llama-3.1-8B` (requer autorizacao HF)
- GPT-4 tokenizer: `tiktoken` (nao precisa HF)

**Decisao:**
- **Production runners:** usar `prompt_eval_count` ja retornado (custo zero, dado real)
- **Analise offline:** tiktoken (GPT-4 como referencia para comparar com TOON) + transformers (Gemma, Qwen para sanity check)

### 3.5 Gap 5: falta grounding em tokenizacao de Sui et al.

Sui et al. 2024 (anchor paper) mediu accuracy, nao tokens. Nao podemos comparar nossos numeros de tokens com os deles. **Nao e problema:** Sui se foca em HTML/MD/CSV/JSON/NL, nao em eficiencia. Citar como "structural understanding benchmark" sem competir diretamente.

---

## 4. Sao os experimentos atuais validos?

### 4.1 Lote 1 (rodando agora)

**Status:** 66/72 combinacoes (qwen3:0.6b + gemma3:1b + qwen3:1.7b)

**Validos?** Sim, mas **incompletos:**
- Falta salvar `prompt_tokens` (gap 1)
- Falta comparar com TOON (gap 2)
- Dados gerados sao uteis mesmo assim

**Decisao:** deixar terminar (6 combos faltando, ~10 min). Os dados sao uteis como baseline. Mas NAO iniciar lote 2 e 3 ainda — vamos corrigir os gaps primeiro.

### 4.2 Findings ja comprovados

| Finding | Validade | Precisa refazer? |
|---------|----------|------------------|
| F30-F34 (Etapa 1) | Valido (chars) | So re-medir tokens (offline) |
| F50-F55 (Etapa 2) | Valido mas incompleto sem TOON | Adicionar TOON |
| F60-F63 (G30) | Valido | So re-medir tokens |
| F70-F73 (transport) | Valido (bytes, nao tokens) | Nao precisa |
| **F80-F84 (diagnostic)** | **Valido** | **Nao precisa** |
| **F85-F89 (scale)** | **Valido** | **Re-medir tokens** |
| **F90-F94 (stats ablation)** | **Valido** | **Nao precisa** |

**Os findings mais importantes (F80-F84, F90-F94) sao robustos.** Nao dependem de tokens vs chars — sao ablacao com/sem STATS, mesma metrica internamente consistente.

Os findings F30-F89 (comparacao entre formatos) podem ser refinados com tokens reais, mas **a direcao deles nao muda** — TCF sera maior ou menor em tokens, mas a comparacao interna e valida.

### 4.3 Conclusao: experimentos sao validos mas incompletos

**Nao precisa reiniciar.** Precisa:
1. Corrigir gravacao de `prompt_tokens` (1 edit)
2. Implementar TOON real (2-3h)
3. Rodar Etapa 2 expandida **ja com TOON incluido** (corrige 2 gaps de uma vez)
4. Rodar validacao de estabilidade N=3 em amostra

---

## 5. Novo plano em etapas

### Etapa 0 — Consolidacao (agora)
1. **Deixar Lote 1 terminar** (6 combos, ~10 min)
2. **Nao iniciar Lote 2/3** ainda
3. Commit checkpoint com esta revisao
4. Atualizar tickets impactados

### Etapa 1 — Corrigir gap de tokens (prioridade 1)
1. Editar `run_etapa2.py` e outros runners para gravar `prompt_tokens` no manifest
2. Instalar tiktoken: `pip install tiktoken`
3. Script offline para re-tokenizar manifests existentes (pegar prompt original, re-tokenizar, adicionar ao registro)
4. Validar: para combos ja rodados, o `prompt_tokens` que gravarmos nos futuros combos bate com o tiktoken offline? Se sim, temos groundtruth retroativa.

### Etapa 2 — Implementar TOON real (prioridade 2)
1. Ler specs TOON oficial (toonformat.dev, github)
2. Implementar encoder TOON em `experiments/eval/llm_eval/toon_encoder.py`
3. Testes roundtrip (TOON encode/decode)
4. Adicionar `toon` como formato em `run_etapa2.py`
5. Formatos testados: `csv`, `jsonl`, `tcf_L0`, `tcf_L2`, `tcf_L3`, **`toon`**

### Etapa 3 — Rodar Etapa 2 expandida v2
Agora com:
- 12 modelos (5 novos ja instalados)
- 6 formatos (adicionando TOON)
- 8 questoes
- **`prompt_tokens` real salvo**
- **`prompt_chars`** (mantido)

Total: 12 × 6 × 8 = 576 combos. Em lotes de 3 modelos cada (192 combos por lote).

**Metricas gravadas por combo:**
- `correct` (accuracy)
- `prompt_chars`
- `prompt_tokens` (do proprio modelo, exato)
- `latency_s`
- `error_type`

### Etapa 4 — Analise consolidada
- Matriz completa accuracy × formato × modelo em **tokens** (nao chars)
- Comparacao TCF vs TOON honesta
- Validacao de F50-F89 com dados refinados
- Decisao: TCF tem nicho claro?

### Etapa 5 — Ticket G-utility-analysis execucao
- Rodar benchmarks nao-LLM (encode/decode time, memoria, bytes)
- Incluir TOON em todos
- Matriz 10-dimensoes final

### Etapa 6 — Decisao do paper
- Se TCF tem vantagem clara em **pelo menos 3 das 10 dimensoes**: publicar
- Se tem so uma (STATS shortcut): publicar com foco nisso
- Se nao tem nenhuma: documentar como "study of format space" em vez de "TCF e o melhor"

---

## 6. Checkpoint importante

### 6.1 Colunar e valido mesmo assim?

O ponto critico do usuario: **"nao estou convencido da ligacao cientifica da tokenizacao"**.

Justo. Mas ha 3 evidencias independentes de que colunar e valido:

1. **Bancos columnar (SQL Server, Parquet, ClickHouse, Arrow) existem ha decadas** e sao bem-sucedidos em OLAP/analytics. Nao e ideia nova — e aplicada a LLMs pela primeira vez.

2. **F81 (STATS shortcut) e um finding empirico forte** — 5/6 modelos usam STATS em vez de calcular. Isso e independente de tokens/caracteres. E uma observacao sobre como LLMs interagem com formato, validada por ablacao.

3. **F70-F73 (transport compression)** e validado em **bytes** (nao tokens) e confirma que TCF+gzip < CSV+gzip em 5K rows. E um ganho real, nao depende de tokenizacao.

Entao mesmo se a hipotese "colunar economiza tokens" for fraca, o TCF ainda tem **2 pilares solidos** (STATS + compressao). A ordem da apresentacao do paper muda:

**Antes (fraca):** "TCF economiza tokens porque e colunar"
**Agora (forte):** "TCF combina compressao textual columnar com hints STATS, permitindo que LLMs acessem agregacoes que nao saberiam calcular (F81), com ganhos em compressao apos gzip (F70-F73) e accuracy em escala (F30, F50)."

### 6.2 O "body CSV" que o usuario mencionou

> "Se tudo isso a gente poder colocar num corpo 'CSV' por exemplo ajudaria muito o TCF"

Entendi como: **TCF ser compatvel com pipelines CSV**. Isso e uma visao importante:

- **CSV e universal**, todo mundo sabe ler
- **TCF poderia coexistir** com CSV (mesma orientacao row no "body" se necessario)
- **Uma variante TCF-row** poderia ser proposta como "CSV melhorado"

Alternativamente, o "body CSV" pode significar: **o conteudo interno das colunas pode ser no formato CSV** (valores separados por virgula em vez de newline).

Exemplo:
```
pessoa: Ana,Ana,Ana,Bruno,Bruno,Bruno
produto: Caneta,Caneta,Lapis,Caneta,Lapis,Lapis
```

Ao inves de:
```
pessoa:
Ana
Ana
Ana
Bruno
...
```

**Isso reduz newlines drasticamente** — e cada newline e um token. Pode ser um dos "otimizacoes BPE-friendly" do H-token-friendly-format. Vou registrar como variante V1.

---

## 7. Decisoes concretas

1. **Deixar Lote 1 terminar** — dados uteis
2. **Nao iniciar Lote 2/3** — corrigir gaps antes
3. **Nao descartar experimentos passados** — sao validos (ablacao interna e robusta)
4. **Focar em STATS shortcut como pilar central do paper** (nao em "colunar vence")
5. **Implementar gravacao de prompt_tokens** imediatamente (trivial)
6. **Implementar TOON encoder real** como proxima tarefa grande
7. **Adicionar TOON em Etapa 2 expandida v2**
8. **Variante CSV-body** como sub-hipotese em H-token-friendly-format

Sou contra **reiniciar tudo** — e desperdicio. Sou a favor de **refinar e expandir** com as novas informacoes.
