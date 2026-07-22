# T-CI-3 — gate byte-canonical do .pyx COMPILADO: outputs de inspecao [probatorio]

**Data**: 2026-06-25. Ambiente: Cython 3.2.5 + MSVC (VS18 Insiders) -> `.pyx` COMPILA.

## Provas (read-only)
1. `.pyx` compilou: `detect.cp313-win_amd64.pyd` (build_ext --inplace, igual hatch_build).
2. **138 gates byte-canonical PASSAM com accel=True** (test_regression_v1_baseline +
   test_real_world_snapshots + test_natures + test_core_rt) -> Cython == baselines pinados.
3. **Comparacao DIRETA accel=True vs accel=False: IDENTICO (0 diff) em 31 datasets**
   sinteticos (`comparar.py`, hashes em `_accel_true.txt`/`_accel_false.txt`).

## Conclusao
O caminho Cython e' byte-equivalente ao pure-Python HOJE. O risco que o T-CI-3 cobre:
REGRESSAO futura (alguem edita `_detect_compositions`/`.pyx` e diverge sem a suite pegar).

## Proposta de teste (pra ajustar)
- `draft-test_pyx_byte_equivalence.py`: skip se accel=False; senao compara Cython vs
  pure-Python nos 31 datasets sinteticos (parametrizado).
- Precisa do **enabler de 1 linha** (`draft-syntax-enabler.md`): salvar `_detect_compositions_py`.
- AJUSTES possiveis: (a) incluir real-world snapshots (so' onde Z: existe);
  (b) inputs aleatorios alem dos datasets; (c) rodar no CI so' no job com extensao
  compilada (matrix). (d) alternativa subprocess sem mexer no src.

## Pendente owner
- Aprovar o enabler (toca src/tcf, 1 linha aditiva) OU escolher a via subprocess.
- Decidir o escopo (datasets sinteticos basta? + real-world? + random?).
- Depois: mover o teste pra tests/ + (futuro) job CI com a extensao.
