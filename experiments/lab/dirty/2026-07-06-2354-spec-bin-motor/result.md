# Resultado — motor spec_bin (escape + RLE/bitstream + exceções) [probatório]

Números: `artifacts/` (`python run.py`). Design do owner: motor preparado, dado depois.

## O motor (sem catálogo — escape)

- **Domínio do dado**: os 2 valores mais comuns SÃO o domínio (bit 0/1). Sem dicionário interno.
- **Guardado 1×, afixo-comprimido** (`02`): `encode(['male','female'])='male\nfe1\n'` — `female`→`fe1`
  referencia `male` pelo OBAT (o owner previu "fe1").
- **Corpo = bit-stream**; o motor testa 2 codificações e escolhe a menor.
- **Overlay de exceções**: raros fora do domínio (null/other) → canal esparso (posição,valor).

## 1. Crossover ordem × codificação (`01`, N=1000)

| distribuição | #runs | RLE | packed (N/8) | vencedor |
|---|---|---|---|---|
| ordenado (2 runs) | 2 | **12B** | 125B | RLE |
| skew 99/1 | 21 | **95B** | 125B | RLE |
| bloco-10 | 100 | 500B | **125B** | packed |
| alternado | 1000 | 4000B | **125B** | packed |
| pseudo-aleatório | 1000 | 4000B | **125B** | packed |

**Poucos runs (ordenado/skew) → RLE** (textual, explicável). **Muitos runs → packed** (N/8 constante).

## 2. Colunas REAIS — packed vence (dado espalhado) (`04`)

| coluna | N | raw(HCC) | RLE | packed | #runs | vencedor |
|---|---|---|---|---|---|---|
| adult.sex | 48842 | 97291B | 86619B | **6106B** | 21580 | packed (16×) |
| adult.class | 48842 | 80886B | 72154B | **6106B** | 17856 | packed |
| matriz_filial | 200000 | 71874B | 64281B | **25000B** | 15297 | packed |
| l_linestatus | 60175 | 48477B | 35017B | **7522B** | 8219 | packed |

**Dado real vem ESPALHADO** (17–21k runs em 48–200k linhas) → RLE perde, **packed ganha (16× em adult.sex)**.
RLE só ganharia se o dump fosse **ordenado/agrupado** pela coluna (export sorted, índice clusterizado). Todas RT-OK.

## 3. Overlay de exceções (`03`)

99% male/female + raros null/other (N=1000, 10 exceções): **RT-OK**. domínio 9B + packed 125B + exceções
65B = **199B**. O bit-stream cobre 100% (exceção=placeholder), a overlay (posição,valor) corrige. Lossless.
= **def-level (Ciclo 1c) + binário**.

## Tensão explicabilidade — "manter a quebra"

- **RLE** `*N|male` = textual, **grupos visíveis** (mantém a quebra, pilar explicabilidade).
- **packed** = binário **opaco** — é **V2-L** (representação binária INTERNA do TCF; header textual `col:spec_bin`
  + domínio ainda roteia/inspeciona). Não compete com gzip — é o TCF binarizando o próprio conteúdo.
- Política: **preferir RLE quando fica perto** (mantém a quebra); ir binário quando o ganho é grande
  (real: 6KB vs 86KB justifica). O motor escolhe; o header continua textual.

## Síntese

O `spec_bin` com **escape** serve QUALQUER enum-2 sem catálogo (`matriz_filial=1|2`, `Male/Female`, `F/O`).
Em **dado real espalhado o corpo útil é binário** (packed/bitmap, V2-L) — reforça o achado do estudo
anterior (compressão de enum é binária). RLE fica pro ordenado/skewed (e pela explicabilidade). Motor pronto;
"o dado depois" = medir mais combinações + enum-k.

## Limites

- Distribuições sintéticas em N=1000; reais em 4 colunas. enum-k>2 não feito. packed é contado (N/8), não
  materializado (é V2-L). Autoridade (typed→canonicaliza) não exercida.

## CORREÇÃO (2026-07-07)

As "colunas reais" (`04-colunas-reais.txt`) foram medidas contra `tcf.encode(list[str])` — path
**single-column**, que ignora `fallback`. O baseline correto é multi-coluna com `fallback=True` (**V2-B**,
[ADR-0025](../../../../docs/adr/0025-v2b-dictionary-categorical-weld.md), já weldado em produção), não HCC
single-col puro. Contra o baseline correto, o ganho de bit-packing cai mas permanece teoricamente limpo
(~8/w bits por item pré-brotli) — tabela corrigida em
[`notas/tipos-como-specs.md`](../notas/tipos-como-specs.md).

Além disso, o ganho pré-brotli colapsa quase por completo sob brotli quality=11 (1.01×-1.33× pós-brotli
nas 4 colunas testadas), confirmando o caveat já registrado em H-REF-05 (2026-06-19,
[`dict-referencia-hipoteses.md`](../notas/dict-referencia-hipoteses.md)) — a hipótese original é
qualitativa (sem números); esta sessão só confirma o caveat com medição, não o inventa. O escape/domínio-
embutido descrito aqui continua um mecanismo válido dentro do espectro de specs — a ressalva é de escopo
de uso (representação terminal) e de cobertura de fontes (N<5 reais), não de invalidade do mecanismo.
