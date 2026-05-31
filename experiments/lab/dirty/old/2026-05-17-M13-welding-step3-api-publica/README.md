# M13 — Welding step 3: API publica `from tcf import encode, decode`

**Data**: 2026-05-17
**Estado**: foi (fechado, validou)
**Welding step**: 3 de N (ver `../notas/welding-plan.md`)
**Foco**: validacao da API publica `from tcf import encode, decode`
contra a cadeia M12 / M11 / M10 / M9.

## Objetivo do step

Confirmar que a interface publica em `src/tcf/`:

```python
from tcf import encode, decode

text = encode(["abc", "abcd", "abcde"])
values = decode(text)
assert values == ["abc", "abcd", "abcde"]
```

produz bytes byte-a-byte identicos a M12 (que usava
`M8AVirtualRefsSyntax` direto).

## Componentes welded em src/tcf/

```
src/tcf/
  __init__.py             # expoe encode, decode
  encoder.py              # encode(values: list[str]) -> str
  decoder.py              # decode(text: str) -> list[str]
  core/
    online.py             # alg16 (byte-exato de M0)
    syntax_base.py        # interface Syntax (1 import adaptado)
  composicional/
    syntax.py             # M8.A (2 imports adaptados; logica byte-exata)
```

## Mudanca vs M12

M12 importava `M8AVirtualRefsSyntax` direto e instanciava manualmente.
M13 usa apenas a API publica de alto nivel — abstrai alg16,
deduplicacao, sintaxe. User da lib so' precisa:

```python
from tcf import encode, decode
```

## Resultado

RT 9/9 OK. Bytes byte-a-byte identicos a M12:

```
diff -r M12/M8-A-src/output M13/M13-tcf-api/output
  → vazio, exit 0
```

| Dataset | M12 | M13 | diff |
|---|---:|---:|---:|
| D1 | 118 | 118 | 0 |
| D2 | 166 | 166 | 0 |
| D3 | 177 | 177 | 0 |
| D4 | 113 | 113 | 0 |
| D5 | 281 | 281 | 0 |
| D6 | 287 | 287 | 0 |
| D7 | 215 | 215 | 0 |
| D8 | 100 | 100 | 0 |
| D9 | 158 | 158 | 0 |
| **Total** | **1615** | **1615** | **0** |

Total raw 2981, ratio 54.2%.

## Significado

Apos M13:

- `src/tcf/` tem encode/decode **formalmente funcionando**.
- Dirty lab fica como **backup canonico** (M0-M12 = fonte da verdade
  que validou o welding).
- Cadeia byte-identica: M0 alg16 → M8.A composicional → M9 → M10 →
  M11 → M12 → **M13 (API publica em src/)**.

Proxima fase: criar **EXP-007** em `experiments/lab/clean/`
consumindo `from tcf import encode, decode` como teste publicavel —
sair finalmente do dirty.

## Cuidados (memory flow)

- ✋ NAO modificou alg16 (`M0/online.py`)
- ✋ NAO modificou M8.A original
- ✋ NAO modificou M9-M12 (cadeia de checkpoints byte-canonica)
- ✋ NAO modificou `src/tcf/core/` ou `src/tcf/composicional/` (Steps A+B)
- ➕ Adicionou `src/tcf/encoder.py`, `src/tcf/decoder.py`
- ✏ Atualizou `src/tcf/__init__.py` para expor API publica
- ➕ Criou M13 (smoke test via API publica)

## Conexoes

- `../notas/welding-plan.md` — plano completo
- `../2026-05-17-M12-welding-step2-m8a-src/` — checkpoint anterior
- `../2026-05-17-M11-welding-step1-alg16-src/` — checkpoint Step A
- `../2026-05-17-M10-datasets-elevation/` — baseline de bytes
