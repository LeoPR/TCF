# Compressao Avancada e Tokenizacao — Estrategia e Empiria

**Data:** 2026-04-15
**Motivacao:** Revisao critica do espaco de compressao do TCF:
estrategias mais agressivas, analise de tokenizacao real, curva de joelho,
STATS como indicador de confiança, e variantes de notacao RLE.

---

## 1. Tokenizacao Real (tiktoken cl100k_base) — Resultados

### 1.1 TCF vs concorrentes (100 linhas, 3 colunas, dados reais)

| Formato | Tokens | Chars | tok/char |
|---------|--------|-------|----------|
| JSONL | 1975 | 5529 | 0.357 |
| Markdown | 979 | 2669 | 0.367 |
| CSV | 751 | 1948 | 0.386 |
| TCF L0 (expanded) | 798 | 1885 | 0.423 |
| TCF L1 (RLE only) | 706 | 1522 | 0.464 |
| **TCF L2 (sort+RLE)** | **553** | **1183** | **0.467** |
| **TCF L3 (dict+sort+RLE)** | **455** | **687** | **0.662** |

**Achados:**
- TCF L2 usa 26% menos tokens que CSV (553 vs 751) — **validado empiricamente**
- TCF L3 usa 39% menos tokens que CSV (455 vs 751)
- TCF L2 usa 72% menos tokens que JSONL (553 vs 1975) — **supera TOON** (que reivindica -54% vs JSON)
- TCF L3 usa 77% menos tokens que JSONL
- TCF L0 é levemente pior que CSV em tokens (+6%) mas melhor em chars (-3%)

### 1.2 Eficiência RLE por multiplicador

| Multiplicador | Tokens RLE | Tokens expandido | Economia | Break-even |
|--------------|------------|-----------------|---------|-----------|
| 2 | 4 | 4 | 0% | nao compensa |
| 3 | 4 | 6 | 33% | compensa |
| 5 | 4 | 10 | 60% | bom |
| 8 | 4 | 16 | 75% | otimo |
| 25 | 4 | 50 | 92% | excelente |
| 100 | 4 | 200 | 98% | perfeito |
| 1000 | 5 | 2000 | ~100% | perfeito |

**Conclusao:** RLE compensa a partir de count=3. No adult-census com
education ordenada, grupos tipicos sao 20-35 rows — saving de 90%+.

### 1.3 Notacao RLE — todas equivalentes em tokens

| Notacao | Tokens para "N*val\n" | Exemplo |
|---------|----------------------|---------|
| `3*Ana\n` | 4 | atual TCF |
| `Ana x3\n` | 4 | tentativa TOON-like |
| `Ana(3)\n` | 4 | parenteses |
| `x3 Ana\n` | 4 | prefixo |
| `3xAna\n` | 4 | sem espaco |

**Todas as notacoes custam 4 tokens** para {count}{sep}{val}{newline}.
**Nao ha ganho em mudar a notacao atual** `N*val`. Manter.

O `*` e um unico token (id=9), otimo.

### 1.4 Impacto de precisao numerica em tokens

| Tipo de valor | Tokens | Exemplo |
|--------------|--------|---------|
| Integer 2 digitos | 1 | `38` |
| Integer 6 digitos | 2 | `147445` |
| Float 2dp | 3 | `38.64` |
| Float grande 2dp | 4 | `147445.47` |
| Scaled int (x100) | 3 | `14744547` |

**Conclusao critica:** inteiros tokenizam melhor.
- `38.64` (float) = 3 tokens
- `38` (int, arredondado) = 1 token — **economia de 67%**
- `147445.47` (float grande) = 4 tokens
- `147445` (int) = 2 tokens — **economia de 50%**

---

## 2. Novas Estrategias de Compressao

### 2.1 Delta Encoding (L4 proposto)

**Caso de uso:** colunas sequenciais ou quasi-monotônicas (IDs, timestamps, datas, contadores).

**Resultado empirico:**
- 20 IDs sequenciais raw: 60 tokens
- `base=1001 step=+1 n=20`: 12 tokens — **80% de economia**
- Explicitamente decodificavel por LLMs que entendem aritetica simples

**Notacao proposta:**
```
id:
# DELTA base=1001 step=+1 n=100
```
ou para deltas irregulares:
```
rank:
# DELTA base=1 d=+1+1+1+2+1+3
```

**Onde aplica:** `id`, `order_key`, `dt` (se sorted), `rank`, `sequence_num`.
**Onde nao aplica:** valores categoricos, floats com variacao alta.

### 2.2 Frame-of-Reference (FOR) (L5 proposto)

**Caso de uso:** numericos em faixa estreita (precos, temperaturas, scores).

**Resultado empirico** (20 precos em torno de 1200):
- Raw: 100 tokens
- `@1200 +12.3 -48.1 ...` (FOR): 84 tokens — **16% de economia** (modesto)
- FOR e mais util quando os offsets sao inteiros ou pequenos

**Notacao proposta:**
```
price:
# FOR base=1200
-48.3
+12.1
-31.7
```

**Ganho token:** economico quando offsets tem menos digitos que o valor absoluto.
Precos em torno de 1200 com variacao de +-50: "1247.3" = 3 tokens, "+47.3" = 3 tokens.
Pouca economia em tokens para float. Mais util para inteiros.

### 2.3 Value Encoding — Scale to Integer (L-numeric proposto)

**Caso de uso:** floats com precisao conhecida que precisam ser eficientes.

**Notacao proposta:**
```
age[x1]:    # already integer-like
38
42
...

price[x100]:  # remove decimal, scale by 100
120047
119850
```

**Ganho token:**
- `38.64` (3 tokens) -> `38` (1 token) arredondado: 67% economia
- `147445.47` (4 tokens) -> `14744547` (3 tokens) scaled: 25% economia
- `147445.47` (4 tokens) -> `147445` (2 tokens) truncado para int: 50% economia

**Decodificador:** `decoded_value = int_val / scale_factor`
**Declaracao no header:** `price[x100]:` ou `# SCALE price=100`

### 2.4 Bucket Quantization — L-lossy (NOVO CONCEITO)

**Primeiro nivel EXPLICITAMENTE LOSSY do TCF.**

**Resultado empirico** (100 precos, mean~1200, std~100):

| Bucket | Tokens RLE | % redução vs raw | Erro avg |
|--------|-----------|-----------------|---------|
| raw | 498 | 0% | 0.00% |
| 1 | 278 | 44% | 0.00% |
| 5 | 219 | 56% | 0.02% |
| 10 | 162 | 67% | 0.02% |
| 25 | 86 | 83% | 0.03% |
| 50 | 49 | 90% | 0.13% |

**Joelho da curva:** bucket=25 oferece 83% de reducao com apenas 0.03% de erro.
Bucket=50 oferece 90% mas o erro sobe para 0.13%.

**Notacao proposta:**
```
price[b=25]:
# LOSSY bucket_size=25 max_error_est=0.03%
```

**Para BI:** "preco na faixa de R$1.200, variando +-$25" e informacao suficiente
para a maioria das analises de tendencia/comparacao.

---

## 3. STATS como Indicador de Confiança para Dados Truncados

### 3.1 O problema

Quando exibimos N=100 rows de uma tabela com N_total=48842:
- Os STATS atuais mostram estatisticas do subconjunto, nao da populacao
- A LLM nao sabe se esta vendo dados parciais ou completos
- Isso causa erros tipo "a media nao bate" quando a LLM calcula sobre os dados

### 3.2 STATS com Intervalo de Confiança

**Notacao proposta (custo: +1 token apenas):**
```
# STATS age: n=100 avg=38.64 err=0.8% full_n=48842
```

Onde `err` e o erro padrao relativo do estimador:
```
SE = std / sqrt(n)
CI_95 = avg +/- 1.96 * SE
err_pct = 1.96 * SE / avg * 100
```

| Versao | Tokens | Conteudo |
|--------|--------|---------|
| Atual | 23 | `n=100 sum=3864 min=17 max=90 avg=38.64` |
| +CI compact | 24 | `n=100 avg=38.64 err=0.8% full_n=48842` |
| +CI verbose | 37 | `n=100/48842 sum=3864+/-2.1% avg=38.64+/-0.8%` |

**Recomendacao:** versao compact (+1 token) e suficiente.
`err=X%` informa a LLM que a estatistica e estimada com aquela margem.
`full_n=48842` informa que existem mais dados.

### 3.3 Confiança para Nivel Lossy

Quando bucket quantization e aplicada:
```
# STATS price[b=25]: n=100 avg=1198.5 err=0.1% (quantization) full_n=...
```

Dois componentes de erro:
1. **Erro de amostragem:** SE = std/sqrt(n)
2. **Erro de quantizacao:** max = bucket_size / 2 / mean * 100

O STATS pode reportar o maior dos dois, ou a soma, como `err` total.

---

## 4. Algoritmo de Joelho Automatico

### 4.1 Conceito

Para cada coluna numerica, encontrar a precisao minima que:
- Reduz tokens maximamente
- Mantém erro de agregacao abaixo de um threshold configuravel

```python
def find_knee(values, max_error_pct=1.0, ops=['sum', 'avg']):
    results = []
    for precision in [4, 3, 2, 1, 0]:
        rounded = [round(v, precision) for v in values]
        err = max(compute_agg_error(values, rounded, op) for op in ops)
        tokens = count_tokens(rounded)
        results.append((precision, tokens, err))
        if err > max_error_pct:
            break
    # Find the knee: max token saving before error threshold
    # Knee = max saving while err <= threshold
    return max(r for r in results if r[2] <= max_error_pct, key=lambda r: -(r[1]))
```

### 4.2 Resultado esperado do knee

Para dados reais de idades (mean=38.64, std=13.4):
```
precision=2: 399 tokens, err=0.00%  <- baseline
precision=1: 399 tokens, err=0.00%  <- mesmo tokens! (chars menores)
precision=0: 199 tokens, err=0.03%  <- JOELHO aqui para max_err=1%
```

Para dados de preco (mean=1200, std=100):
```
bucket=1:  278 tokens, err=0.00%
bucket=25:  86 tokens, err=0.03%   <- JOELHO para max_err=1%
bucket=50:  49 tokens, err=0.13%   <- ultrapassa 0.1%, fica em bucket=25
```

### 4.3 API proposta

```python
config = EncodeConfig(
    level=2,
    auto_precision=True,     # ativa knee algorithm
    max_error_pct=1.0,       # tolerancia de erro em agregacoes
    precision=None,          # sobreposicao manual por coluna (opcional)
)
```

### 4.4 Separacao: LLM-mode vs Transport-mode

Um insight fundamental: a compressao ideal para LLM e diferente da ideal para transporte.

| Modo | Objetivo | Tecnicas uteis |
|------|----------|----------------|
| **LLM-mode** | Menos tokens no prompt, mais acertos | RLE, STATS, precision reduction, dict |
| **Transport-mode** | Menos bytes na rede, mais velocidade | sort+gzip (RLE redundante com gzip), brotli |
| **BI-LLM mode** | Acerto em queries analiticas com minimo tokens | Bucket quantization + STATS com CI |

**Achado de P-rle-vs-gzip:** RLE textual pode atrapalhar gzip (LZ77 ja faz RLE).
Para transport, L2-sort-no-rle + gzip pode ser melhor que L2 (sort+RLE) + gzip.
Para LLM input, RLE reduz tokens diretamente (sem gzip), entao e sempre util.

**Proposta de modos:**
```python
config = EncodeConfig(level=2, mode='llm')       # RLE ativo, stats ativados
config = EncodeConfig(level=2, mode='transport')  # sort sem RLE, sem stats
config = EncodeConfig(level=2, mode='bi_llm')     # bucket+stats+CI
```

---

## 5. Hierarquia de Compressao Revisada (v0.3)

### 5.1 Niveis atuais (L0-L3) — manter como base

| Level | Tecnica | Reversivel | Uso |
|-------|---------|-----------|-----|
| L0 | Expanded | 100% | Debug, baseline |
| L1 | RLE | 100% | Dados sem ordem |
| L2 | Sort + RLE | 100% (dados) | LLM-mode padrao |
| L3 | Dict + sort + RLE | 100% | Token-max, LLM grande |

### 5.2 Novos niveis propostos (L4-L6)

| Level | Tecnica | Reversivel | Uso |
|-------|---------|-----------|-----|
| L4 | Delta encoding (L3 + delta para seq) | 100% | IDs, timestamps |
| L5 | FOR + delta (L4 + frame-of-reference) | 100% | Precos estreitos |
| Lb | Bucket quantization | Controladamente lossy | Transport BI |

### 5.3 Variante de modo: `mode='llm'` vs `mode='transport'`

Para qualquer nivel L1-L5, modo controla se RLE e emitido textualmente
ou se confia no gzip downstream.

---

## 6. Comparacao com TOON — Dados Empiricos

Com token counting real (tiktoken), agora podemos comparar honestamente:

| Formato | Tokens (100 rows, mixed data) | vs JSONL |
|---------|------------------------------|---------|
| JSONL | 1975 | baseline |
| TOON (estimado, -54% vs JSON) | ~908 | -54% |
| CSV | 751 | -62% |
| **TCF L2** | **553** | **-72%** |
| **TCF L3** | **455** | **-77%** |

**TCF L2 supera TOON** (estimado) em reducao de tokens vs JSONL.
Caveat: TOON foi medido com tiktoken em dados diferentes. Precisa de
comparacao direta no mesmo dataset.

**Por que TCF ganha:** orientacao columnar + sort + RLE =
blocos de valores identicos que tokenizam como 4 tokens independente
de quantas repeticoes. TOON e row-oriented e nao tem RLE.

---

## 7. Para o Artigo — Novos Argumentos

### 7.1 Hierarquia de compressao para LLMs

TCF oferece um espectro de tradeoffs nao visto em nenhum formato atual:

```
Precisao maxima    <----- continuum ----->    Tokens minimos
L0                L2          L3           Lb (bucket lossy)
798 tokens     553 tokens  455 tokens     ~100 tokens
err=0%          err=0%      err=0%        err=0.03-0.13%
```

### 7.2 Argumento de token efficiency comprovado

- TCF L2: **-26% tokens vs CSV**, **-72% vs JSONL** (empirico, tiktoken)
- Supera os benchmarks divulgados do TOON em reducao vs JSON
- Sem precisar de otimizacao especifica para tokenizer — e natural do formato

### 7.3 STATS como interface cognitiva adaptativa

- Full data: STATS mostra parametros exatos, sem CI necessario
- Amostra: STATS adiciona `err=X% full_n=N` (custo: +1 token)
- Dados lossily comprimidos: STATS adiciona `(quantization)` para
  distinguir erro de quantizacao de erro de amostragem

### 7.4 Curva de joelho como feature diferencial

Nenhum formato tabular para LLMs oferece "auto-precision by error budget".
TCF com `auto_precision=True` e `max_error_pct=1.0` poderia fazer:
- "Para queries de tendencia, aceito 1% de erro, minimo tokens"
- "Para auditoria fiscal, aceito 0.001% de erro, tokens mais altos"

**Analogia com JPEG:** JPEG tem qualidade 0-100 que controla erro visual.
TCF com knee algorithm seria o "JPEG analítico" para dados tabulares.

---

## 8. Checklist de Implementacao

### Imediato (V0.2.1 — sem quebrar API):
- [ ] STATS: adicionar `full_n` e `err` opccionais ao `_stats_line()`
- [ ] `EncodeConfig`: adicionar campo `precision` por coluna (`dict[str, int]`)
- [ ] Benchmark: rodar comparacao com tiktoken em todos os experimentos passados
- [ ] Fechar ticket M-tokenizer-validation com esses resultados

### Proximo (V0.3.0 — novos niveis):
- [ ] Delta encoding na `compression.py` (L4)
- [ ] Value encoding / scale-to-int (variante de L3)
- [ ] Knee algorithm: `find_optimal_precision(values, max_error_pct)`
- [ ] Bucket quantization (L-lossy / Lb)
- [ ] `mode='llm'` vs `mode='transport'` em EncodeConfig
- [ ] Testes: verificar que novos encodings sao decodiveis

### Pesquisa necessaria (before V0.3):
- [ ] Rodar TOON real no mesmo benchmark (P-competing-formats)
- [ ] Medir impacto de delta/FOR em LLM accuracy (nao so em tokens)
- [ ] Validar que bucket quantization nao confunde LLMs
- [ ] Estudar se ollama /api/tokenize existe em versao mais nova

---

## 9. Literatura Adicional Necessaria

### Ja temos:
- Sui et al. 2024 (Table Meets LLM)
- TabLLM 2023
- PoT/PAL 2023
- TOON arxiv 2026

### Falta pesquisar:
- **TableEval EMNLP 2025** — benchmark moderno com queries complexas
- **LLMLingua-2 (2024)** — versao melhorada de prompt compression
- **Columnstore compression empirics** — papers de SQL Server/DuckDB/Parquet
- **Lossy compression for analytics (AQP literature)** — approximate query processing
  (BlinkDB, VerdaDB, Wander Join) — TCF-lossy se encaixa neste nicho
- **BPE tokenization analysis papers** — quais estruturas de texto tokenizam melhor
- **"Token-efficient table serialization"** — search arxiv por novos papers 2025-2026
