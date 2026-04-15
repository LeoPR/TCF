---
title: Compressao avancada v0.3 — delta, FOR, scale-to-int, bucket, knee algorithm
type: hypothesis
status: OPEN
priority: HIGH
created: 2026-04-15
origin: Revisao critica de compressao + tokenizacao empirica (2026-04-15)
see_also: docs/research-notes/2026-04-15-compression-tokenization-strategy.md
---

# Compressao Avancada TCF v0.3

## Contexto

Tokenizacao empirica com tiktoken revelou:
- TCF L2 ja usa **-26% tokens vs CSV**, **-72% vs JSONL** sem otimizacao especifica
- Todos os notacoes RLE (N*val, val xN, etc.) custam os mesmos 4 tokens — manter atual
- Inteiros tokenizam 50-67% melhor que floats equivalentes
- Bucket quantization entrega 83% reducao com apenas 0.03% de erro (preco bucket=25)

Evidencia: `docs/research-notes/2026-04-15-compression-tokenization-strategy.md`

## Hipoteses

### H-adv-1: Delta encoding para colunas sequenciais

Sequencia de 20 IDs: raw=60 tokens vs `base=1001 step=+1 n=20`=12 tokens (80% economia).

**Notacao proposta:**
```
id:
# DELTA base=1001 step=+1 n=100
```
Para deltas irregulares: `# DELTA base=1001 d=+1+1+2+1+3`

**Caso de uso:** `id`, `order_key`, timestamps como unix epochs, rankings.
**Nao aplica a:** valores categoricos, floats com alta variancia.

### H-adv-2: Value encoding (scale-to-int)

Floats com precisao conhecida -> inteiros com fator de escala.

- `38.64` (3 tokens) -> `38` arredondado (1 token, -67%)
- `147445.47` (4 tokens) -> `147445` truncado (2 tokens, -50%)

**Notacao proposta:** declarar no header da coluna:
```
price[x100]:
120047
119850
```
ou flag no STATS: `# SCALE price=100`

### H-adv-3: Bucket quantization (primeiro nivel lossy)

Valores numericos agrupados em buckets de tamanho fixo.
**Explicitamente lossy mas controlado.**

Resultado empirico (100 precos, mean~1200, std~100):
- bucket=25: 83% reducao tokens, erro avg=0.03%
- bucket=50: 90% reducao tokens, erro avg=0.13%

**Curva de joelho:** bucket=25 e o ponto otimo para max_error=1%.

**Notacao:**
```
price[b=25]:
# LOSSY bucket_size=25 max_error_est=0.03%
1200
1175
1225
```

### H-adv-4: Knee algorithm — auto-precision por budget de erro

Encontrar automaticamente a precisao minima que mantém erro <= threshold:

```python
config = EncodeConfig(
    level=2,
    auto_precision=True,
    max_error_pct=1.0,   # 1% tolerancia
)
```

O encoder testa precision=4,3,2,1,0 e bucket=1,5,10,25,50 e retorna
a configuracao com mais tokens economizados dentro do budget.

**Analogia:** JPEG tem quality 0-100 para compressao visual.
TCF com knee seria o **"JPEG analitico"** — compressao com budget de erro.

### H-adv-5: STATS com intervalo de confiança para dados truncados

Quando n < full_n (amostragem), adicionar ao STATS:
```
# STATS age: n=100 avg=38.64 err=0.8% full_n=48842
```

Custo: +1 token apenas. Informa a LLM sobre:
- Que os dados sao uma amostra (n vs full_n)
- O erro estatistico esperado em estimativas (SE relativo)

Formula: `err = 1.96 * std / sqrt(n) / avg * 100`

Para dados lossily comprimidos:
```
# STATS price[b=25]: n=100 avg=1198.5 err=0.03% (quantization)
```

### H-adv-6: Modo LLM vs Transport

Separar configuracoes otimas para cada caso de uso:

```python
EncodeConfig(level=2, mode='llm')        # RLE ativo, STATS ativados
EncodeConfig(level=2, mode='transport')  # sort sem RLE, sem STATS (gzip faz RLE)
EncodeConfig(level=2, mode='bi_llm')     # bucket + STATS com CI
```

**Baseado em:** evidencia de P-rle-vs-gzip de que RLE textual pode
atrapalhar gzip (LZ77 ja faz RLE internamente).
RLE e util para LLM (reduz tokens), menos util para gzip.

## Implementacao

### V0.2.1 (sem quebrar API — adicionar features opcionais):
- [ ] `_stats_line()`: adicionar params `full_n` e `err_pct` opcionais
- [ ] `EncodeConfig`: adicionar campo `precision` por coluna `dict[str, int] | None`
- [ ] Benchmark tiktoken: re-tokenizar todos os experimentos passados

### V0.3.0 (novos encodings):
- [ ] `compression.py`: `delta_encode(values)` / `delta_decode(header, n)`
- [ ] `compression.py`: `scale_to_int(values, factor)` / `int_to_scale(values, factor)`
- [ ] `compression.py`: `bucket_quantize(values, bucket_size)` / `bucket_decode(values, bucket_size)`
- [ ] `compression.py`: `find_knee(values, max_error_pct, ops)` — knee algorithm
- [ ] `encoder.py`: detectar automaticamente tipo de coluna (sequencial, numerica estreita, etc.)
- [ ] `encoder.py`: suporte a `mode` em `EncodeConfig`
- [ ] Atualizar spec em `docs/article/appendices/A-tcf-spec.md`

## Testes necessarios

Antes de adicionar L4-L6 como niveis oficiais:
1. Rodar benchmark LLM com delta/FOR/scale: sera que LLMs entendem?
2. Verificar que gzip downstream ainda funciona (delta pode ser mais entropico)
3. Verificar roundtrip perfeito para encodings lossless (L4, L5)
4. Quantificar erro exato de bucket para cada tipo de coluna

## Risco

**Delta encoding pode confundir LLMs** — "base=1001 step=+1 n=100" exige
que o LLM entenda que precisa reconstruir os 100 valores antes de raciocinar.
Pode ser que a compressao de tokens nao valha o custo cognitivo.

**Teste necessario:** mesmo LLM, mesma pergunta, dados com/sem delta encoding.
Se accuracy cair, documentar como "compressao para transporte, nao para LLM".
