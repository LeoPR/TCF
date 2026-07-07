# Resultado — spec por largura de bits (b/b2/b4/b8) [probatório]

Números: `artifacts/` (`python run.py`). Nota do owner: spec primitivo de tipo por largura de bits.

## O spec primitivo (`01-tabela-larguras.txt`)

k distintos → w bits → 8/w linhas por byte. O spec = `col:b<w>` + a **lista do domínio embutida** (a lista
É a referência: índice ↔ valor). Corpo = índices empacotados a w bits.

| k | spec | w | linhas/byte |
|---|---|---|---|
| ≤2 | **b** | 1 | 8 |
| 3–4 | **b2** | 2 | 4 |
| 5–16 | **b4** | 4 | 2 |
| 17–256 | **b8** | 8 | 1 |

`spec_bin` (domínio-2) vira o caso `b`. A **referência embutida no spec** = "até a referência está embutida"
(owner).

## Colunas REAIS — bit-pack vs raw HCC, pesa e escolhe (`03-reais-pesa-vs-hcc.txt`)

| coluna | N | k | spec | raw HCC | packed | ganho |
|---|---|---|---|---|---|---|
| adult.sex | 48842 | 2 | b | 97291B | **6117B** | 16× |
| adult.class | 48842 | 2 | b | 80886B | **6117B** | 13× |
| lineitem.l_linestatus | 60175 | 2 | b | 48477B | **7526B** | 6× |
| estabelecimentos.matriz_filial | 200000 | 2 | b | 71874B | **25008B** | 3× |
| lineitem.l_returnflag | 60175 | 3 | b2 | 97131B | **15050B** | 6× |
| orders.o_orderstatus | 15000 | 3 | b2 | 34806B | **3756B** | 9× |
| adult.race | 48842 | 5 | b4 | 55993B | **24477B** | 2× |
| adult.relationship | 48842 | 6 | b4 | 133862B | **24483B** | 5× |
| adult.marital-status | 48842 | 7 | b4 | 127459B | **24503B** | 5× |
| adult.workclass | 48842 | 9 | b4 | 98471B | **24510B** | 4× |
| adult.occupation | 48842 | 15 | b4 | 155842B | **24624B** | 6× |
| adult.education | 48842 | 16 | b4 | 144375B | **24558B** | 6× |

**Bit-pack vence em todas** (dado real espalhado). b4 packa a ~24.5KB constante (48842×4/8=24421 + domínio);
raw HCC varia com o comprimento dos valores (55–155KB) e sempre perde. Todas RT-OK.

## Pesar vs HCC-nativo (owner: "o HCC pode dar naturalmente uma forma de empacotar")

- **HCC-nativo** = RLE de refs (`*N|^k`), textual, mantém a quebra. Empacota REPETIÇÕES → vence **ordenado/
  agrupado** (poucos runs).
- **bit-pack** = índices a w bits (V2-L, binário) → vence **espalhado** (real). O motor escolhe o menor.
- Header textual `col:b<w>` + domínio embutido roteia/inspeciona; só o corpo de índices é binário (V2-L).

## Síntese

Um **spec primitivo único** cobre string→enum-k por largura de bits (`b/b2/b4/b8`), com a **referência
embutida** (domínio na spec). `spec_bin` = `b`. Em dado real (espalhado) o bit-pack ganha 2–16×; o HCC-RLE
fica pro ordenado + explicabilidade. O motor pesa e escolhe.

## Limites

- Domínio por 1ª aparição (frequência daria índices menores p/ RLE, não muda w). b8/b16 não exercitados em
  real. pack materializado é V2-L (aqui contado). O "pesar" é por-coluna; combinar com o pré-ordenamento (S3) é futuro.

## CORREÇÃO (2026-07-07, mesmo dia do lab)

A tabela `artifacts/03-reais-pesa-vs-hcc.txt` compara bit-packing contra HCC via `tcf.encode(list[str])`
(path single-column, `fallback` ignorado) — não contra **V2-B**
(`encode({col: vals}, fallback=True)`, já weldado, [ADR-0025](../../../../docs/adr/0025-v2b-dictionary-categorical-weld.md)),
que é o baseline que o usuário do TCF usa por default. A tabela corrigida (V2-B correto vs bitpack,
pré-brotli) está em [`notas/tipos-como-specs.md`](../notas/tipos-como-specs.md) — os ganhos corrigidos
seguem o padrão teórico ~8/w (w=1→~8×, w=2→~4×, w=4→~2×), com 2 desvios explicados por dado real já
agrupado (HCC-RLE nativo).

Teste adicional (não presente no lab original): brotli quality=11 sobre os dois lados colapsa o ganho
pré-brotli pra 1.01×-1.33× em 4 colunas reais. Isso confirma empiricamente o caveat qualitativo de H-REF-05
("encosta em entropy-coding, tende a sumir sob brotli", registrada 2026-06-19, antes deste lab — a hipótese
original não trazia números). Veredito atualizado: família bN é confirmada-empírica **com ressalva**
(escopo = TCF como representação terminal sem re-compressão a jusante; N<5 fontes reais) — não
confirmada-empírica plena, não pronta pra weld.
