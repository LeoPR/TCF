# Data — alvos de transformação × declaração da grafia

`n=600` por regime. RT conferido em dois níveis: o wire, e a **inversa do alvo** (as datas voltam iguais).

## Parte 1 — os alvos

Bytes por regime. **negrito = melhor do regime.**

| regime | `iso` | `ordinal-dec` | `ordinal-denso` | `ordinal-b64` | `epoch-seg` | `compacto` | `delta-dias` |
|---|---:|---:|---:|---:|---:|---:|---:|
| `diario` | 414 | **22** | 2736 | 2663 | 30 | 329 | 27 |
| `semanal` | 2744 | **22** | 3009 | 3061 | 31 | 1956 | 27 |
| `mensal` | 6338 | **23** | 3009 | 3009 | 32 | 4672 | 28 |
| `agrupado` | 64 | 143 | 221 | 165 | 473 | **62** | 235 |
| `repetido-k12` | 529 | 449 | 467 | 478 | 458 | 500 | **237** |
| `espalhado` | 5364 | 4193 | **2990** | 2991 | 6254 | 5074 | 3068 |
| `espalhado-ord` | 5376 | 3455 | 2867 | 2921 | 5753 | 4089 | **643** |
| `decada-espalhada` | 6848 | 4199 | **3007** | 3007 | 6583 | 5625 | 3755 |

### Quem vence, e quantos alvos são necessários

| regime | vence | ganho sobre `iso` |
|---|---|---:|
| `diario` | **ordinal-dec** | 18.8× |
| `semanal` | **ordinal-dec** | 124.7× |
| `mensal` | **ordinal-dec** | 275.6× |
| `agrupado` | **compacto** | 1.0× |
| `repetido-k12` | **delta-dias** | 2.2× |
| `espalhado` | **ordinal-denso** | 1.8× |
| `espalhado-ord` | **delta-dias** | 8.4× |
| `decada-espalhada` | **ordinal-denso** | 2.3× |

**4 alvos distintos vencem em algum regime**: `compacto`, `delta-dias`, `ordinal-dec`, `ordinal-denso`.


### O mesmo quadro, PAGANDO a declaração

`iso` não transforma nada (nada a declarar). `delta-dias` guarda o 1º valor **verbatim**, então a grafia viaja de graça. Os outros destroem a grafia e pagam os **10 B** do header.

| regime | `iso` | `ordinal-dec` | `ordinal-denso` | `ordinal-b64` | `epoch-seg` | `compacto` | `delta-dias` |
|---|---:|---:|---:|---:|---:|---:|---:|
| `diario` | 414 | 32 | 2746 | 2673 | 40 | 339 | **27** |
| `semanal` | 2744 | 32 | 3019 | 3071 | 41 | 1966 | **27** |
| `mensal` | 6338 | 33 | 3019 | 3019 | 42 | 4682 | **28** |
| `agrupado` | **64** | 153 | 231 | 175 | 483 | 72 | 235 |
| `repetido-k12` | 529 | 459 | 477 | 488 | 468 | 510 | **237** |
| `espalhado` | 5364 | 4203 | **3000** | 3001 | 6264 | 5084 | 3068 |
| `espalhado-ord` | 5376 | 3465 | 2877 | 2931 | 5763 | 4099 | **643** |
| `decada-espalhada` | 6848 | 4209 | **3017** | 3017 | 6593 | 5635 | 3755 |

| vence | em quantos regimes |
|---|---:|
| `delta-dias` | 5 |
| `ordinal-denso` | 2 |
| `iso` | 1 |

**A declaração inverte o quadro:**

| regime | sem declarar | pagando |
|---|---|---|
| `diario` | `ordinal-dec` | `delta-dias` ← |
| `semanal` | `ordinal-dec` | `delta-dias` ← |
| `mensal` | `ordinal-dec` | `delta-dias` ← |
| `agrupado` | `compacto` | `iso` ← |
| `repetido-k12` | `delta-dias` | `delta-dias` |
| `espalhado` | `ordinal-denso` | `ordinal-denso` |
| `espalhado-ord` | `delta-dias` | `delta-dias` |
| `decada-espalhada` | `ordinal-denso` | `ordinal-denso` |

## Parte 2 — declarar a grafia

- **H1 — spec no header** (`#TCF.8 :data-iso`): **10 B** fixos, uma vez por coluna.
- **H2 — template no 1º registro**: 7–9 B (o `%Y-%m-%d` e afins), uma vez por coluna — e ocupa uma linha do corpo.
- **H3 — inferir do 1º registro**: **0 B**, mas só funciona se o primeiro valor tiver leitura única. Medido abaixo, sobre as 366 datas de um ano:

| grafia | 1º valor desambigua | taxa | exemplo ambíguo |
|---|---:|---:|---|
| `iso` | 366/366 | **100.0%** | — |
| `br` | 221/366 | **60.4%** | `01/01/2026` → ['br', 'us'] |
| `us` | 221/366 | **60.4%** | `01/01/2026` → ['br', 'us'] |
| `compacto` | 366/366 | **100.0%** | — |
| `ponto` | 366/366 | **100.0%** | — |
| `iso-invertido` | 366/366 | **100.0%** | — |

---

**falhas de RT: 0**

*(alfabeto denso: 80 chars, largura 4)*
