---
title: Tratamento numerico com perda controlada — shaper + TCF core
type: research
status: OPEN
priority: 22
created: 2026-04-12
---

# Numeric Precision Treatment

## Contexto

Numeros com muitas casas decimais sao custosos em TODOS os formatos:
- CSV: cada digito = 1 byte
- JSON: idem
- TCF textual: idem
- SQLite: 8 bytes (REAL = IEEE 754 double)
- Compressao binaria: nao ajuda muito em floats aleatorios

**Hipotese:** reduzir precisao de forma controlada melhora compressao
e velocidade, com perda aceitavel e mensuravel.

## Duas camadas independentes

### Camada 1 — Shaper (pre-TCF)

**Proposito:** reduzir precisao na FONTE para:
- Menos bytes no SQLite (nao muda tipo, mas muda valor)
- Menos caracteres nos CSVs derivados
- Melhor compressibilidade via RLE (mais repeticoes com menos decimais)
- Controle estatistico do erro acumulado

**Submodulo:** `scripts/shaper/strategies/numeric_precision.py`

**Parametros:**
```python
ShapeRequest(
    ...,
    numeric_precision={
        "max_decimals": 2,         # cortar para 2 casas
        # OU
        "max_error_pct": 0.001,    # maximo 0.1% de erro em somas
        # OU
        "significant_digits": 4,   # arredondamento cientifico
    }
)
```

**Controle de erro:**

Ao arredondar, o erro se propaga diferentemente por operacao:

| Operacao | Propagacao de erro | Formula |
|----------|-------------------|---------|
| Soma de N valores | Pior caso: N × delta | E_sum <= N × delta_max |
| Media | Pior caso: delta (nao acumula) | E_avg <= delta_max |
| Multiplicacao A × B | Relativo: |E_rel| <= |dA/A| + |dB/B| | Propagacao percentual |
| Divisao | Idem multiplicacao | Propagacao percentual |
| Acumulado (sum of products) | Combinacao: N × delta_prod | Mais complexo |

**Perspectivas de analise:**
- **Financeiro:** soma de vendas, totais. Erro absoluto importa.
  $147,445.47 com 0.1% de erro = $147.45 de discrepancia.
  Aceitavel em analytics exploratorio, inaceitavel em contabilidade.

- **Cientifico:** propagacao de incerteza (Gauss). Erro relativo importa.
  Se cada medida tem incerteza de 0.01%, N=1000 medidas somadas tem
  incerteza de ~0.32% (raiz de N, nao linear).

- **Compressao:** menos decimais → mais repeticoes → melhor RLE.
  Exemplo: precos arredondados para inteiro (2.50 → 3) podem ter
  50% de repeticao vs 5% com 2 casas decimais.

### Camada 2 — TCF core (futuro)

**Proposito:** o encoder TCF tem sua propria logica de compressao numerica.
Diferente do shaper:

- **Textual:** cada digito e um caracter. Menos digitos = menos chars.
  `147445.47` = 9 chars, `147445` = 6 chars (33% menor).

- **Notacao cientifica:** `1.47e5` = 6 chars vs `147445.47` = 9 chars.
  Pode ser mais compacto para valores grandes, mas LLMs podem confundir.

- **Codificacao binaria textual:** representar floats como base64 ou hex.
  `0x41102D73` = 10 chars para float32 de 9.01.
  Pode ser mais compacto para alta precisao, mas LLMs nao entendem.

- **Delta encoding numerico:** `base=147000 deltas=445 450 430...`
  Os deltas tem menos digitos. Ja registrado em H-advanced-encodings.

- **Scale factor:** `col[x100]: 14744547 12500000 893215`
  Remove ponto decimal. Inteiros comprimem melhor em RLE.

**Submodulo futuro:** `src/tcf/numeric.py`

```python
EncodeConfig(
    ...,
    numeric_mode="auto",        # auto, fixed_decimals, scientific, delta, scale
    numeric_precision=2,        # casas decimais (se fixed_decimals)
    numeric_max_error_pct=0.01, # perda maxima (se auto)
)
```

## Relacao entre as camadas

```
Dados fonte (30 decimais)
  ↓
Shaper: arredonda para 4 decimais (controle estatistico)
  Calcula: erro acumulado em somas, multiplicacoes, medias
  Registra: {"original_precision": 30, "shaped_precision": 4, "max_sum_error": 0.02%}
  ↓
TCF encode: recebe dados ja arredondados (4 decimais)
  Pode ainda compactar mais: scale factor (x10000), delta encoding
  Registra: {"encoding": "scale_x10000", "text_precision": 0, "real_precision": 4}
  ↓
TCF decode: reverte para 4 decimais (nao para 30 — perda do shaper e irrecuperavel)
  ↓
Validacao: comparar com original (30 decimais) e com shaped (4 decimais)
  Erro total = erro_shaper + erro_tcf
```

**Importante:** TCF decode nao pode reverter o arredondamento do shaper.
A perda do shaper e IRRECUPERAVEL. O TCF so reverte sua propria compressao.

## Metricas de avaliacao

Para cada combinacao (precision × operacao):

| Metrica | O que mede |
|---------|-----------|
| `sum_error_abs` | |sum_original - sum_rounded| |
| `sum_error_pct` | % de erro na soma total |
| `mean_error_abs` | erro na media |
| `max_single_error` | maior erro em um valor individual |
| `product_error_pct` | erro acumulado em multiplicacao (qty × price) |
| `rle_improvement` | % de runs extras criados pelo arredondamento |
| `bytes_saved_csv` | bytes a menos na representacao CSV |
| `bytes_saved_tcf` | bytes a menos na representacao TCF |

## Sequencia de implementacao

**Nao implementar agora.** Registrar para futuro.

1. Primeiro: terminar shaper basico (tickets 19-22)
2. Depois: `scripts/shaper/strategies/numeric_precision.py`
   (arredondamento na fonte com controle de erro)
3. Depois: `src/tcf/numeric.py`
   (compressao de numericos no encoder com parametros de perda)
4. Por fim: testes end-to-end de propagacao de erro
   (shaper arredonda → TCF encode/decode → medir erro total)

## Referencias

- Propagacao de incerteza de Gauss (ISO GUM)
- IEEE 754 double precision (15-17 significant digits)
- `decimal` module do Python (precisao arbitraria)
- H-smart-rounding (ticket congelado, conceito similar)
- H-advanced-encodings (ticket congelado, delta/scale/FOR)
