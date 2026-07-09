# Resultado — F3 misto seletivo (bN-w≤4 no min) [probatório]

Números: `artifacts/` (`python3 run.py`). Baseline = produção real `min(tcf,raw,v2b,split)`, fallback=True.
Verificado adversarialmente (4 lentes) — somas conferem, enquadramento corrigido.

## Nível-tabela weighted (8 fontes reais, N amostrado a LIMIT=20000)

| fonte | N | cols | prod tabela B | econ w≤4 B | pre % | pos-brotli % | (wide w≤8 pre %) |
|---|---|---|---|---|---|---|---|
| adult | 20000 | 15 | 401914 | 105000 | **26.1%** | 2.9% | 26.1% |
| tpch.lineitem | 20000 | 16 | 1179075 | 83502 | **7.1%** | 0.5% | 8.8% |
| receita.estab | 20000 | 8 | 492771 | 10608 | **2.2%** | **−0.2%** | 2.2% |
| br.pessoas | 20000 | 6 | 875835 | 0 | 0.0% | 0.0% | 0.0% |
| ibge.municipios | 5571 | 8 | 136920 | 0 | 0.0% | 0.0% | 4.1% |
| beijing-pm25 | 20000 | 13 | 211635 | 15000 | **7.1%** | 0.7% | 7.1% |
| online-retail | 20000 | 8 | 257906 | 0 | 0.0% | 0.0% | 15.2% |
| wine | 6497 | 13 | 159375 | 3248 | **2.0%** | 0.5% | 29.3% |
| **WEIGHTED** | | | 3715431 | 217358 | **5.9%** | **0.5%** | **8.8% (= D3)** |

## Decomposição por largura (`03`)

| w | k | tile-de-byte? | cols que vencem | bytes | % prod |
|---|---|---|---|---|---|
| 1 | ≤2 | sim (8/byte) | 4 | 49110 | 1.32% |
| 2 | ≤4 | sim (4/byte) | 3 | 45000 | 1.21% |
| 4 | ≤16 | sim (2/byte) | 13 | 123248 | 3.32% |
| 8 | 95..256 | NÃO (1 val/byte) | 11 | 108242 | 2.91% |

F3 (w≤4) = 217358 B = 5.9%. O extra w=8 (108242 B, 2.9 p.p.) é k **95..256**: 8 bits = 1 byte exato, vence
v2b só porque v2b usa 2 chars/índice p/ k>94 — não é bit-packing sub-byte. Em k 17..94, bN=v2b=1 byte → 0 wins.

## Veredito

- **BYTE-SAFE só no TERMINAL** por construção — `min()` é sobre bytes terminais, garante F3 ≤ prod terminal.
  **Pós-brotli NÃO é safe**: `receita` = −0.2% (+469 B). Bits densos destroem a redundância byte-a-byte que
  o brotli explora no stream base-94. Weighted pós-brotli 0.5% → efetivamente nulo, com caudas negativas.
- **O bit-packing sub-byte real (w≤4) = 5.9% terminal**, concentrado em colunas binárias/categóricas de N
  alto (adult 26.1%). Colapsa pós-brotli. Confirma D3 no subconjunto honesto.
- **Reproduz D3** (wide=8.8%): é reprodução do mesmo método (bN até w=8), não cross-check independente — mas
  serve de sanity (a decomposição mostra que ~1/3 do "8.8% do D3" era o regime w=8, não bit-packing).

## Conclusão p/ H-TYPE-07

F3 (o 3º fluxo) é **byte-neutro-a-negativo pós-brotli** e byte-safe só no terminal. Como F1 e D3, o valor do
bN é **terminal/streaming**, não byte re-comprimido. **Não justifica welding por byte.** Se algum dia entrar,
o gate correto é w≤4 (o subconjunto byte-tileável) + regime terminal — e ainda assim como candidato do `min()`
(byte-safe terminal), nunca imposto. Fecha os 3 fluxos: **F1 latência (2.4×), F2 = natures já welded, F3
byte-neutro**. O byte não é o eixo do bN; latência/terminal é.

## Limites

- Domínio do bN reusa v2b com min_len=None (produção pode usar auto) — isolamento do radix aproximado, o delta
  de tabela << delta de radix (números conservadores). O pb comparado é o min real, não necessariamente v2b.
- Pós-brotli = corpos-concat (sem header), proxy do regime re-comprimido; o ~1 B/coluna do discriminador de
  modo bN (~20 B total) é omitido — desprezível vs 217358 B. 8 fontes, N amostrado a 20000.
