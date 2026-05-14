# M10 — Datasets elevation (smoke test)

**Data**: 2026-05-17
**Estado**: foi (fechado, validou)
**Foco**: smoke test do fluxo "datasets canonicos em `datasets/synthetic/`
em vez de `./data/` local por macro".

## Objetivo

Validar que a elevacao de D1-D9 para `datasets/synthetic/`
(localizacao canonica oficial) preserva o fluxo: macro deve produzir
bytes byte-a-byte identicos aos do M9.

Se bate, oficializamos a localizacao + (opcional) removemos
duplicatas das macros M4-M9 ou expandimos com variantes
(D1a/D1b/etc.).

## Mudanca vs M9

- Em vez de `header, linhas = ler_csv(THIS / "data" / f"{ds}.csv")`:
  ```python
  DATASETS_DIR = THIS.parents[3] / "datasets" / "synthetic"
  ...
  header, linhas = ler_csv(DATASETS_DIR / f"{ds}.csv")
  ```
- M8.A syntax + online + syntax_base + run_lote sao copias exatas de M9.

Tudo identico exceto o path da entrada.

## Resultado

RT 9/9 OK. Bytes byte-a-byte identicos a M9:

| Dataset | M9 bytes | M10 bytes | Diff |
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

Validacao byte-level:
```
diff -r M9/output M10/output  → vazio, exit 0
```

## Conclusao

**Fluxo da elevacao OK.** `datasets/synthetic/` pode ser referenciada
por experimentos futuros (M11+, EXP-007+) sem perda. Macros fechados
M4-M9 mantem snapshots locais por reprodutibilidade (nao remover sem
plano).

## Proximos passos

1. **Oficializar `datasets/synthetic/`** como localizacao canonica (feito).
2. **Macros futuros** (M11+, EXP-007+) referenciam `datasets/synthetic/`.
3. **Expansao** (D1a, D1b, ...) — opcional, sob demanda.
4. **Cleanup** das duplicatas em M4-M9 — DECISAO PENDENTE (user)
   se vale a pena. Risco: perde snapshot-por-macro reproducibility.

## Conexoes

- `datasets/synthetic/README.md` — documentacao oficial
- `../2026-05-17-M9-stress-adversarial/` — baseline
- `../notas/welding-plan.md` — proximo passo (sair pro src/)
