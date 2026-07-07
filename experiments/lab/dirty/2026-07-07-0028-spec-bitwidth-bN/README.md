# 2026-07-07-0028 — spec por largura de bits (b/b2/b4/b8)

**Ticket**: [T-OPT-INFERENCE](../../../../tickets/T-OPT-INFERENCE.md) · nota-mãe
[tipos-como-specs](../notas/tipos-como-specs.md) · generaliza o
[motor spec_bin](../2026-07-06-2354-spec-bin-motor/result.md) e o
[Formato A/B](../2026-07-07-0016-spec-bin-formato-A-B/result.md). Nota do owner (2026-07-07): spec primitivo
de tipo por largura de bits.

## Estado

- **era**: spec binária só cobria domínio-2.
- **foi**: generalizada numa **família por largura de bits** `b<w>`.
- **é**: k distintos → w bits → 8/w linhas/byte: k≤2→**b**(8/byte) · k≤4→**b2**(4/byte) · k≤16→**b4**(2/byte)
  · k≤256→**b8**(1/byte). O spec é `col:b<w>` + a **lista do domínio embutida = a referência** (índice↔valor).
  `spec_bin` = caso `b`. RT-OK em k=2..16 sintético + 12 colunas reais. **Bit-pack vence em todas as reais**
  (dado espalhado): b ~16×, b2 ~6-9×, b4 ~2-6×.
- **será**: pack pós-HCC real (`*N|^k`); b8/b16; welding V2-L.

## A família (o spec primitivo)

| k | spec | w bits | linhas/byte |
|---|---|---|---|
| ≤2 | b | 1 | 8 |
| 3–4 | b2 | 2 | 4 |
| 5–16 | b4 | 4 | 2 |
| 17–256 | b8 | 8 | 1 |

## Achados (medidos, colunas reais N=48842/60175/…)

- **b** (k=2): sex 97KB→6KB (16×), l_linestatus 48→7.5KB, matriz_filial 72→25KB.
- **b2** (k=3): l_returnflag 97→15KB, o_orderstatus 34→3.7KB.
- **b4** (k=5–16): race/relationship/marital/workclass/occupation/education → todas ~24.5KB (48842×4/8).
- **PESAR vs HCC** (owner): o HCC-nativo já empacota repetições (RLE de refs, textual); o bit-pack ganha no
  **espalhado**. O motor escolhe o menor. Real (espalhado) → bit-pack; ordenado → HCC-RLE (explicável).

## Arquivos

- `bitpack.py` — width_for/pack/unpack/induce/encode/decode; domínio embutido (afixo) = referência.
- `run.py` — tabela + RT sintético + reais pesadas vs HCC. `python run.py` regenera `artifacts/`.
- `artifacts/` — `00-resumo` · `01-tabela-larguras` · `02-sintetico-rt` · `03-reais-pesa-vs-hcc`.

## Como rodar

```
python experiments/lab/dirty/2026-07-07-0028-spec-bitwidth-bN/run.py
```

## Escopo

Dirty. NÃO toca `src/tcf`. O pack é V2-L (binário interno); header `col:b<w>` textual roteia.
