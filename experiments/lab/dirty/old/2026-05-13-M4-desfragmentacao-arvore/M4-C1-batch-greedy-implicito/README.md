# M4.C1 — Batch greedy com idx implicito (v1: runs inteiras)

## Tecnica

Identifica runs de refs (sequencias consecutivas em uma linha)
que se repetem entre linhas. 1a aparicao recebe `~RUN` (marcador
de definicao); subsequentes viram `&N`.

Sem preambulo `&N=...` estilo M3. Custo de definicao reduzido
a 1 char (`~`).

## Sintaxe

```
~1..4\3       # 1a aparicao: ~ define alias 1 = "1..4"
&1\4          # 2a aparicao: usa alias 1
```

Idx alocado por ORDEM DE 1a APARICAO (encoder e decoder concordam).

## Resultado nos canonicos

| Dataset | M1.E | M4.C1 | delta |
|---|---:|---:|---:|
| D1 | 149 | 148 | -1 |
| D2 | 180 | 178 | -2 |
| D3 | 206 | 203 | -3 |
| D4 | 141 | 137 | -4 |
| **TOTAL** | **676** | **666** | **-10 (-1.5%)** |

RT 4/4 OK.

## Comparacao com M2.A

| | D1 | D2 | D3 | D4 | Total |
|---|---:|---:|---:|---:|---:|
| M1.E | 149 | 180 | 206 | 141 | 676 |
| M2.A (alias tupla M2) | 141 | 178 | 206 | 141 | 666 |
| M4.C1 v1 (runs inteiras) | 148 | 178 | 203 | 137 | 666 |

**Mesmo total** (666) mas distribuicao diferente:
- M2.A ganha mais em D1 (-8 vs -1 M4.C1)
- M4.C1 v1 ganha mais em D3 (-3 vs 0) e D4 (-4 vs 0)
- D2 empata (-2 em ambos)

Sugere que M2.A e M4.C1 capturam **oportunidades distintas** do
mesmo regime — M2.A pega sufixos, M4.C1 pega runs inteiras
repetidas. Combinar pode aumentar.

## Limitacao clara identificada

**M4.C1 v1 detecta apenas RUNS INTEIRAS repetidas** — nao captura
subsequencias internas de runs maiores.

Caso concreto D4 nao capturado:
- Linha 9: `1,2,11,12,4,6` — run (1,2,11,12,4,6) unica
- Linha 10: `8,2,11,12,4,5` — run (8,2,11,12,4,5) unica
- Linha 11: `8,2,11,12,4\3` — run (8,2,11,12,4) unica

Cada run inteira aparece 1x apenas. Counter nao detecta.

A **subsequencia interna `2,11,12,4` aparece 3x** em runs maiores
mas v1 nao busca subsequencias. Limite teorico do M4.A (114B
intermediario implicito) so' seria atingido com detector mais
sofisticado.

## Estrutura

```
M4-C1-batch-greedy-implicito/
  README.md      (este)
  syntax.py
  output/        TCFs gerados
  decoded/       contra-prova
  debug/         detalhado
```

## Bug resolvido

V0 alocava idx por ordem de NET (maior net = idx 1). Decoder
aloca por ORDEM DE `~` no TCF. Encoder e decoder divergiam,
RT falhava. Fix: encoder agora aloca por **ordem de 1a aparicao**,
espelhando o decoder.

## Implicacao para M4.C1' / M4.C2 / M4.C3

V1 confirma:
- Idx implicito funciona (marker `~` baixo custo)
- Greedy batch sobre runs inteiras da' ganho modesto (-10B)

Limitacao: subsequencias internas nao detectadas. Para capturar
o limite teorico de 114B (M4.A), precisa:
- **M4.C1'**: estender detector pra subsequencias (sufixos e
  prefixos de runs, similar a M2.A)
- OU **M4.C2**: online com janela deslizante
- OU **M4.C3**: refragmentacao (mais complexo)

V1 e' validacao da SINTAXE de idx implicito. Detector mais
sofisticado mantem mesma sintaxe.

## Como rodar

```bash
cd 2026-05-13-M4-desfragmentacao-arvore
python run_lote.py
```
