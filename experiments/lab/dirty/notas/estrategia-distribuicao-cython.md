# Estratégia de distribuição do acelerador Cython (moderna + forward-looking) [decisão]

**Data**: 2026-06-25. **Tipo**: decisão/plano. Refina [ADR-0020](../../../../docs/adr/0020-cython-optional-accelerator.md)
(acelerador opcional) e a dimensão de distribuição do [T-CI-3](../../../../tickets/T-CI-3-pyx-compiled-byte-gate.md).
Verificado contra práticas correntes (web, junho 2026 — fontes no fim).

## Princípio (decidido)
**A compilação NÃO se embute no código de runtime.** O runtime só dá a "dica" (monkeypatch
em `syntax.py`: usa o `.pyd` se presente, senão pure-Python byte-idêntico) e degrada com
graça. A **compilação é concern de PACKAGING** (build do mantenedor), que **adapta à
plataforma**. Compilar em runtime = ❌ (precisa compilador na máquina de execução, frágil,
inseguro).

## Packaging — moderno (fazer no release)
- **cibuildwheel** (PyPA) = O padrão pra wheels por plataforma. **cibuildwheel 3.0** usa
  **`uv` como build frontend** (mais rápido; o TCF já usa `uv build`). Publica wheels
  pré-compiladas (Win/Mac/Linux × pyver, incl. ARM) → usuário `pip install` pega a wheel
  certa, **sem compilador**.
- **Fallback**: sdist + o build-hook best-effort (`hatch_build.py`) — plataforma exótica
  compila-ou-pure-Python. Pure-Python **sempre** funciona.
- **Trusted Publishing (OIDC)** — já usado no `release.yml`. ✓ moderno/seguro.
- **T-CI-3 no CI da wheel**: o mesmo job cibuildwheel roda `test_pyx_byte_equivalence`
  (`accel=True`) em cada wheel ANTES de publicar → verifica byte-equivalência onde a
  extensão é compilada. Não é job separado.

## Adaptações FORWARD-LOOKING (baquear desde já)
1. **Free-threading (no-GIL)** — foco em **3.14t+**, NÃO 3.13t (deprecated, sendo removido).
   cibuildwheel 3.0 já constrói `cp314t` por default. **TCF é naturalmente free-threading-
   friendly**: `detect.pyx` é uma FUNÇÃO PURA (compute determinístico, sem estado
   compartilhado) → thread-safe por construção. Só falta declarar `Py_MOD_GIL_NOT_USED`
   (Cython 3.1+ suporta). **A mesma pureza que o foco-2 busca pro port C/Rust dá a
   free-threading-readiness de graça.**
2. **Stable ABI (abi3)** — compilar com `Py_LIMITED_API` dá **UMA wheel por plataforma**
   cobrindo várias versões de Python (reduz a matriz vs per-pyver). Cython tem
   `--limited-api`. Pra extensão simples/determinística como a nossa, deve caber.
   **Forward**: **abi3t** ([PEP 803](https://peps.python.org/pep-0803/), Python 3.15+) =
   stable ABI pro free-threaded (abi3 puro NÃO funciona com no-GIL). Caminho:
   abi3 (não-FT) + abi3t (FT, 3.15+); tag `abi3.abi3t` + `Py_mod_abi`. [PEP 809](https://peps.python.org/pep-0809/)
   ("Stable ABI for the Future") é o horizonte.
3. **Backend de build** — `hatchling` + hook custom agora (ok p/ 1 `.pyx`). Upgrade path se
   o compilado crescer: **`meson-python`** (o padrão moderno p/ C/Cython/Fortran sério —
   numpy/scipy migraram; Cython nativo no Meson 0.59+). **`maturin`** pro **port Rust** do
   foco-2 (mesmo layout wheel/cibuildwheel). `pyproject.toml` já nota isso.

## Resumo da decisão
- Runtime: dica + fallback (já feito, e free-threading-friendly por pureza). Zero compilação embutida.
- Build: cibuildwheel (uv frontend) → wheels por plataforma; sdist+hook fallback; pure-Python sempre.
- Forward: declarar GIL-not-used (FT 3.14t+); avaliar abi3/abi3t (reduzir matriz); meson-python/maturin se crescer/Rust.
- CI: T-CI-3 roda no build de cada wheel.
- **Timing**: decidido AGORA; cibuildwheel implementado no release (0.8.0). O `.pyd` local
  já está "compilado e adaptado pra nós" (accel=True, T-CI-3 verde).

## Fontes (verificação junho 2026)
- [cibuildwheel](https://cibuildwheel.pypa.io/en/stable/) · [changelog 3.0](https://cibuildwheel.pypa.io/en/stable/changelog/) ·
  [Free-Threading CI guide](https://py-free-threading.github.io/ci/)
- [C API Stability (docs)](https://docs.python.org/3/c-api/stable.html) · [PEP 803 abi3t](https://peps.python.org/pep-0803/) ·
  [PEP 809](https://peps.python.org/pep-0809/) · [abi3t migration howto](https://docs.python.org/3.15/howto/abi3t-migration.html)
- [meson-python](https://mesonbuild.com/meson-python/) · [PEP 517 backend popularity (Quansight)](https://labs.quansight.org/blog/pep-517-build-system-popularity)
