# Resultado — Sub-exp 08 (H-DA-10 min_len trade-off)

**Data**: 2026-05-17
**Estado**: concluido
**Plano**: [README.md](README.md)
**Tabela**: [summary.md](summary.md)

## Conclusao executiva

**H-DA-10 CONFIRMADA com nuance.** min_len otimo varia por dataset:

| Dataset | min_len otimo | Bytes fork |
|---|---:|---:|
| D16a (3-char IDs) | 3 (default) | **11** |
| D11d (19-char datetime) | 2 ou 3 (empate, default ok) | **73** |
| **D9 (wrapper `@@@KEY=valueX@@@`)** | **5** | **94** |

D9 com `min_len=5` da **-33 bytes vs default** (127→94). Ganho
substantial (-26% adicional sobre HCC fork ja' ativo).

## Tabela completa

| Dataset | min_len | canonical body | HCC fork body | RT |
|---|---:|---:|---:|---|
| D16a | 2 | 60 | 33 | OK |
| D16a | 3 (default) | 65 | **11** | OK |
| D16a | 4 | 65 | 11 | OK |
| D16a | 5 | 65 | 11 | OK |
| D11d | 2 | 110 | 73 | OK |
| D11d | 3 (default) | 110 | 73 | OK |
| D11d | 4 | 121 | 121 | OK |
| D11d | 5 | 134 | 134 | OK |
| D9 | 2 | 158 | 127 | OK |
| D9 | 3 (default) | 158 | 127 | OK |
| D9 | 4 | 150 | 113 | OK |
| D9 | 5 | 174 | **94** | OK |

## Padroes observados

### D16a — strings curtas (3 chars)

- min_len=2: cria refs micro (overhead alto) → fork=33
- min_len>=3: sem refs (LCP=2 < min_len) → seq-RLE livre → **fork=11**

**Insight**: pra strings curtas, **subir** min_len evita refs
inuteis e libera seq-RLE.

### D11d — strings medias (19 chars)

- min_len=2-3: optimo (default)
- min_len>=4: refs nao cobrem o suficiente → caem pra literal puro → pior

**Insight**: default min_len=3 e' bem calibrado pra strings medias.

### D9 — strings longas (~21 chars) com wrapper pattern

- min_len=2-3: optimo "alto" (127 fork)
- min_len=4: melhora (113 fork)
- **min_len=5: muito melhor (94 fork)**

**Insight**: pra patterns wrapper, refs grandes consolidam melhor.
Forca OBAT a NAO criar refs pequenos espalhados, mas sim refs
maiores que cobrem chunks substanciais.

D9 strings: `@@@KEY=valueX@@@` (X varia). Wrapper de 6 chars cada
lado, slot de ~10 chars. Com min_len=5, OBAT prefere refs >= 5
chars, que coincidem com partes do wrapper. Refs ficam grandes e
uniformes.

## Implicacao pra welding / clean lab

Default min_len=3 e' bom pra **maioria**, mas:
- Datasets com strings curtas e LCP < 3: subir min_len
  (deixa seq-RLE trabalhar) — **D16a, similar**
- Datasets wrapper/template com slots variaveis: testar
  min_len=4 ou 5 — **D9, similar**

**Auto-tuning**: Pre stage pode tentar min_len ∈ {2,3,4,5} no
encoder e escolher menor body. Custo: ate 4x encode. Mas
single-pass por tentativa, baixa memoria.

Sub-hipotese decorrente **H-DA-10b**: auto-tune de min_len no Pre
stage. Nao implementada — registrar pra futuro.

## Status H-DA-10 no roadmap

**CONFIRMADA** — trade-off existe, min_len otimo varia por dataset.
Ganho mensuravel (D9: -33B).

## H-DA-10b (decorrente)

Auto-tune min_len no Pre stage: tentar varios e usar menor. Custo
moderado (single-pass por tentativa). Registrar.

## Arquivos

```
08-min-len-trade-off/
├── README.md
├── run.py
├── summary.md
├── result.md
└── outputs/<ds>/min_len_<n>/
    ├── body-canonical.tcf
    ├── body-hcc-fork.tcf
    └── stats.txt
```
