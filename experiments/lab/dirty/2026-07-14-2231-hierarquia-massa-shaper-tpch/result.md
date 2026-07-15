# Resultado — teste em massa da hierarquia com DADO REAL (TPC-H aninhado via FK)

**[probatório]** `build.py` lê o hub `Z:/tcf-data/interim/tpch-sf001.db`, aninha pela FK e exige
RT byte-exato + invariante estrutural + byte-determinismo. Números:
[outputs/03-massa-result.txt](outputs/03-massa-result.txt).

## Medido (dado real, em massa)

| forma real (aninhada via FK) | docs | filhos aninhados | bytes `.tcf` | RT | determinismo | invariante |
|---|---:|---:|---:|:--:|:--:|:--:|
| `customer → [pedidos] → [itens]` (2 níveis) | 1500 | 75175 | 4 774 688 | ✅ | ✅ | ✅ |
| `orders → [itens]` (1 nível, outro pai) | 15000 | 60175 | 999 849 | ✅ | ✅ | ✅ |

Amostra diffável (3 clientes): `intermediates/01-nested-sample.json` (23 566 B) →
`outputs/01-sample.tcf` (5 775 B) → `outputs/02-roundtrip-sample.json` — **deep-equal True**. O header
da amostra mostra a gramática em dado real: `#TCF.8Hcustkey:8,…,pedidos#:10[…,itens#:61[…,obs` —
counts explícitos (`pedidos#`, `itens#`), blocos aninhados `[…]`, última-folha-sem-size (`obs`).

## Leitura

O weld (`src/tcf/hierarchical.py`) faz RT byte-exato de **dado hierárquico real em massa** — 75 mil
filhos aninhados em 2 níveis, 60 mil em 1 nível, com free-text real (`l_comment`) passando pelo
compressor de coluna (L1). Complementa o fuzz sintético (8000/8000, lab 2120) e os clássicos pinados:
agora há **dado real** confirmando capacidade + robustez de topologia. O aninhamento veio do próprio
esquema do projeto (FK do TPC-H) — o "shaper montando o dataset", invertido (normalizado → aninhado).

## Fronteira / o que NÃO estabelece

- **Capacidade + topologia**, não compressão: os bytes `.tcf` NÃO são claim de ganho (comparação é
  vs JSON indentado, não vs baseline canônico; e o escopo é all-string).
- **Classe coberta** (all-string via `str()`): tipos (float/date reais coeridos), `null` e ragged são
  camada ortogonal, deixados pro FIM (decisão do owner). Nulls não ocorreram nas chaves; folhas
  nulas foram coeridas a `""` no teste de topologia.
- **Perf** (`.9`): o encode de 60k free-text pelo HCC é o custo dominante (rodou em background) —
  território de otimização, fora do escopo agora.

`confianca: Alta` p/ a classe coberta (fuzz sintético + clássicos + **dado real em massa** agora).
