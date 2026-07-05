"""Hatchling build hook — acelerador Cython OPCIONAL (best-effort).

H-PERF-06-v2 Fase B (ADR-0020). Tenta compilar src/tcf/_core/*.pyx durante o
build do wheel. Se Cython ou compilador C estiverem ausentes (ou qualquer erro),
**NAO falha o build**: emite warning e produz um wheel pure-Python. Em runtime,
src/tcf/composicional/syntax.py cai pro _detect_compositions pure-Python
(output byte-identico). Logo `pip install tcf` funciona em qualquer ambiente.

Wheel com extensao = platform-specific (infer_tag). Wheel sem = pure-Python.
"""
from __future__ import annotations

import glob
import os
import subprocess
import sys

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

PYX = ["src/tcf/_core/detect.pyx"]


class CustomBuildHook(BuildHookInterface):
    PLUGIN_NAME = "custom"

    def initialize(self, version, build_data):
        # so' faz sentido no target wheel
        if self.target_name != "wheel":
            return
        require = os.environ.get("TCF_REQUIRE_ACCEL", "").strip().lower() in (
            "1", "true", "yes", "on",
        )
        try:
            self._try_build(build_data)
        except Exception as exc:  # noqa: BLE001 - best-effort: nunca falhar (salvo opt-in)
            if require:
                # Opt-in (CI da wheel / release): a falha do acelerador vira ERRO
                # alto em vez de wheel pure-Python silenciosa. Evita "otimizacao
                # fantasma" (T-CI-3 dimensao distribuicao; revisao 6-lentes #2).
                raise RuntimeError(
                    f"[tcf] TCF_REQUIRE_ACCEL setado mas o acelerador Cython nao "
                    f"compilou ({type(exc).__name__}: {exc}). A wheel seria "
                    f"pure-Python. Verifique Cython + compilador C no ambiente."
                ) from exc
            self.app.display_warning(
                f"[tcf] acelerador Cython pulado ({type(exc).__name__}: {exc}); "
                f"wheel pure-Python (funciona, so' mais lento). "
                f"Set TCF_REQUIRE_ACCEL=1 pra exigir a extensao."
            )

    def _try_build(self, build_data) -> None:
        root = self.root
        pyx_paths = [os.path.join(root, p) for p in PYX]
        if not all(os.path.exists(p) for p in pyx_paths):
            raise FileNotFoundError("fonte .pyx ausente")

        import Cython  # noqa: F401  (falha aqui => except no initialize)

        # Compila in-place a partir de src/ com nome qualificado (tcf._core.detect).
        # subprocess isola qualquer falha do toolchain (compilador ausente etc).
        code = (
            "from setuptools import setup, Extension;"
            "from Cython.Build import cythonize;"
            "setup(name='tcf_core_ext', script_args=['build_ext','--inplace'],"
            "ext_modules=cythonize([Extension('tcf._core.detect',"
            "['tcf/_core/detect.pyx'])], language_level=3))"
        )
        subprocess.run(
            [sys.executable, "-c", code],
            cwd=os.path.join(root, "src"),
            check=True,
            capture_output=True,
        )

        built = glob.glob(os.path.join(root, "src", "tcf", "_core", "detect*.pyd"))
        built += glob.glob(os.path.join(root, "src", "tcf", "_core", "detect*.so"))
        if not built:
            raise RuntimeError("build_ext nao produziu artefato")

        # Inclui o artefato no wheel e marca platform-specific.
        force = build_data.setdefault("force_include", {})
        for art in built:
            rel = os.path.relpath(art, os.path.join(root, "src"))
            force[art] = rel.replace(os.sep, "/")
        build_data["pure_python"] = False
        build_data["infer_tag"] = True
        self.app.display_info(
            f"[tcf] acelerador Cython compilado: {os.path.basename(built[0])}"
        )
