# M11 — Welding step 1: alg16 em src/tcf/core/

**Data**: 2026-05-17
**Estado**: foi (fechado, validou)
**Welding step**: 1 de N (ver `../notas/welding-plan.md`)
**Foco**: smoke test do alg16 copiado para `src/tcf/core/online.py`.

## Objetivo do step

Validar que a copia de `online.py` (alg16 — TCF-CORE) do M0 para
`src/tcf/core/online.py` esta funcional. Critery: bytes byte-a-byte
identicos a M10/M9 quando M8.A composicional usa a copia.

## Mudanca vs M10

- M11 NAO tem `online.py` local — usa `src/tcf/core/online.py`.
- `run_lote.py` ajusta `sys.path` para `from online import ...`
  resolver em `src/tcf/core/`.
- Resto identico a M10 (mesma syntax M8.A, mesmo datasets/synthetic/).

## Resultado

RT 9/9 OK. Bytes byte-a-byte identicos a M10:

```
diff -r M10/M8-A-baseline/output M11/M8-A-baseline/output
  → vazio, exit 0
```

Total D1-D9: 1615 bytes (igual M9 = M10).

| Dataset | M10 | M11 | diff |
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

## Validacao da copia

```
diff M0/online.py src/tcf/core/online.py
  → vazio, exit 0 (byte-exata)
```

## Conclusao

**Welding step 1 OK.** alg16 em `src/tcf/core/online.py` reproduz
M9/M10 byte-a-byte. Pode prosseguir para step 2 (M8.A composicional).

## Proximo (step 2)

Copiar `M8-A-detector-unificado/syntax.py` (M8.A 736 LOC) para
`src/tcf/composicional/syntax.py`. Smoke test M12. Ver
`../notas/welding-plan.md`.

## Cuidados (memory flow)

- ✋ NAO modificou `M0/online.py` (fonte da verdade)
- ✋ NAO modificou `M8.A-detector-unificado` (canonico)
- ✋ NAO modificou outros macros
- ➕ Apenas adicionou `src/tcf/core/online.py` (copia) e M11
- Rollback: `rm -rf src/tcf/core experiments/.../M11`

## Conexoes

- `../notas/welding-plan.md` — plano completo (steps 1-7)
- `../2026-05-17-M10-datasets-elevation/` — baseline byte-canonico
- `../M0-fase-exploratoria-inicial/2026-05-11-16-online-cleanup/online.py` — fonte alg16
