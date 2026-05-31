# M12 — Welding step 2: M8.A composicional em src/tcf/composicional/

**Data**: 2026-05-17
**Estado**: foi (fechado, validou)
**Welding step**: 2 de N (ver `../notas/welding-plan.md`)
**Foco**: smoke test do M8.A composicional welded para
`src/tcf/composicional/syntax.py` (com imports adaptados ao package
layout).

## Objetivo do step

Validar que M8.A composicional copiado para
`src/tcf/composicional/syntax.py` (com imports adaptados para
`tcf.core.online` e `tcf.core.syntax_base`) produz bytes byte-a-byte
identicos a M11 (e por extensao M10 e M9).

## Mudanca vs M11

- M12 importa M8AVirtualRefsSyntax direto de
  `src/tcf/composicional/syntax.py` (com syntax adaptado pra
  package paths).
- M12 NAO tem syntax.py local — usa import package nativo.
- `run_lote.py` adiciona `src/` ao sys.path antes do import.

### Adaptacoes vs M8.A original (welding step 2)

Apenas linhas de import mudaram:
- `from online import ...` → `from tcf.core.online import ...`
- `from syntax_base import Syntax` → `from tcf.core.syntax_base import Syntax`
- Removido `sys.path.insert(0, str(Path(__file__).parent.parent))`

E cascata em `src/tcf/core/syntax_base.py`:
- `from online import Token` → `from tcf.core.online import Token`

**Logica de encode/decode permanece byte-exata.** Validado por M12
matriz_bytes igual a M11.

## Resultado

RT 9/9 OK. Bytes byte-a-byte identicos a M11:

```
diff -r M11/M8-A-baseline/output M12/M8-A-src/output
  → vazio, exit 0
```

| Dataset | M11 | M12 | diff |
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

## Conclusao

**Welding step 2 OK.** M8.A composicional em `src/tcf/composicional/`
reproduz M11/M10/M9 byte-a-byte via package imports limpos. Cadeia
de checkpoints intacta: M0 → M9 → M10 → M11 → M12.

## Incidente durante execucao (registrado)

User reportou freeze do Claude durante Step B inicial. Apos retomada:
- Verificado estado: ultimo commit `2b6f507` intacto, dirty lab + M11 intactos
- Estado em progresso: src/tcf/composicional/ adaptado (imports), M12 com refactor incompleto
- Reparo: completou M12 run_lote.py (removeu dead code, corrigiu SINTAXES_REGISTRADAS,
  ajustou print, adicionou cascade adaptation em src/tcf/core/syntax_base.py)
- Resultado: M12 RT 9/9 OK, diff byte-exato vs M11

## Proximo (step 3)

API publica: `src/tcf/encoder.py` + `src/tcf/decoder.py` com
`encode()` / `decode()` wrappers de alto nivel. Ver
`../notas/welding-plan.md` Fase 4.

## Cuidados (memory flow)

- ✋ NAO modificou alg16 original (`M0/online.py`)
- ✋ NAO modificou M8.A original (`2026-05-16-.../syntax.py`)
- ✋ NAO modificou M9, M10, M11
- ➕ Adicionou `src/tcf/composicional/syntax.py` (imports adaptados)
- ➕ Adicionou M12 (smoke test do welding step 2)
- ✏ Adaptou `src/tcf/core/syntax_base.py` (import path; cascade)

## Conexoes

- `../notas/welding-plan.md` — plano completo
- `../2026-05-17-M11-welding-step1-alg16-src/` — checkpoint anterior
- `../2026-05-16-M8-virtual-refs-clean-output/M8-A-detector-unificado/syntax.py` — fonte M8.A
