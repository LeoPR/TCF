# Resultado — tipos como specs (análise) [probatório]

Números: `artifacts/` (`python run.py`). Reframe do owner; 3 questões medidas + a regra universal.

## 1. Bool como spec — o número corrigiu a hipótese (`01-bool-spec-compressao.txt`)

`true`/`false` (string) vs `t`/`f` (spec) + tag `b`, via `tcf.encode` (RLE aplica aos dois):

| N | dist | string | spec+tag | Δ |
|---|---|---|---|---|
| 100 | alternado | 305B | 299B | **−6B** |
| 100 | 70-30 | 125B | 119B | **−6B** |
| 100 | all-true | 10B | 8B | **−2B** |

**Ganho FLAT ~6B, não ~N.** O HCC já dedup os 2 valores distintos num dict e guarda N **referências**; o
spec só encolhe o **dict** uma vez. A compressão por-valor real (1 bit) é **binária** (bitmap, V2-L), não
textual. Em texto o bool-spec vale por **aceleração** (decode tipado) + dict-shrink modesto. **Não
superestimar compressão de tipo em texto.**

## 2. A regra universal de indução: ROUND-TRIP (`02-inducao-roundtrip.txt`)

**Induz a spec ⟺ o valor faz round-trip por ela.** Zero-config, resolve o self-description:

| valor | induz | motivo |
|---|---|---|
| `"30"` | int | `str(int)=="30"` ✓ |
| `"01310"` | **string** | →1310≠"01310" (zero à esquerda) ✗ |
| `"4.5"` | float | ✓ |
| `"4.50"` | **string** | →4.5≠"4.50" ✗ |
| `"1e3"` | **string** | →1000.0≠"1e3" ✗ |
| `"true"` | bool | ∈{true,false} ✓ |
| `"True"` | **string** | JSON minúsculo ✗ |

Análogo exato do **hex-default** (T-OPT-INFERENCE) e da **1ª-string-molde do OBAT**.

## 3. Número (`03-numero-cadence.txt`)

- cadenciado 1..100 → **23B**; espalhado i² → **601B**. O número sequencial comprime forte.
- **MAS `cadence.rule_hit=None`** no encode default: a compressão veio do **HCC (seq-RLE/range)**, não da
  regra de cadence nomeada (que é estágio do pipeline delta-aware). int vs float = sub-spec pelo ponto.

## 4. Gabarito (`04-gabarito.txt`)

`analyze_column.sample[0]` PROPÕE; o round-trip em TODAS CONFIRMA:
- `idades` → int; `ceps ["01310",…]` → **string** (guard salva); `misto ["30","ana"]` → **string**.
= a **C-híbrida (1b) generalizada**.

## Síntese (→ nota [tipos-como-specs](../notas/tipos-como-specs.md))

- **Espectro único**: string → int/float/bool → nature (CPF/datetime). Tipo = spec mínima.
- **Justificativa**: compressão OU aceleração; senão não spec (string).
- **Indução segura ⟺ round-trip**; **gabarito propõe, round-trip confirma**.
- **Unifica** tipo (1a/1b) + hex (T-OPT-INFERENCE) + natures (ADR-0015) num só mecanismo no pre-pass
  (`analyze_column` já induz; custo ~zero).
- **Camadas**: compressão forte de bool = binária (V2-L); em texto, aceleração. O espectro cruza as 2 camadas.

## Limites

- Só a **compressão** foi medida; a **aceleração** (decode tipado vs deduzido) fica pra medir (Ciclo 3).
- Colunas homogêneas; amostras minúsculas/médias (N≤100). Real-world + bool-bitmap pendentes.
