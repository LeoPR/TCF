"""Manifesto de baseline — o que precisa ser CONGELADO pra .8 vs .9 valer.

O owner (2026-07-21): "o processo precisa repetir de forma statisticamente
similar pro .9 pra gente ter comparacao depois." Comparacao so' vale se as duas
rodadas partirem do MESMO ponto congelado. O manifesto e' esse ponto.

Congela: seed, sha da matriz (cases.json), versao do tcf, git HEAD (+ dirty),
python/plataforma, e — CRITICO — QUAIS compressores existem no ambiente. Quando
a evidencia .8 original foi gerada, o brotli NAO estava no venv e caiu em
fallback SILENCIOSO; um manifesto que registra "brotli: ausente" impede que o
.9 compare macas com laranjas sem perceber.

    python -m bench_perf.manifest            # escreve o manifesto
    python -m bench_perf.manifest --check    # valida sem escrever (aborta se sujo)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
REPO = AQUI.parent.parent


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _git(*args: str) -> str:
    try:
        return subprocess.run(["git", "-C", str(REPO), *args],
                              capture_output=True, text=True, timeout=15).stdout.strip()
    except Exception:
        return ""


def _compressores() -> dict:
    """Registra presenca E versao de cada compressor. Ausente = registrado como
    ausente, nunca fallback calado."""
    out: dict = {}
    import gzip
    import zlib
    out["gzip"] = {"presente": True, "zlib_version": zlib.ZLIB_VERSION}
    for nome, mod in (("brotli", "brotli"), ("zstandard", "zstandard"),
                      ("lz4", "lz4")):
        try:
            m = __import__(mod)
            v = getattr(m, "__version__", None) or getattr(m, "version", "?")
            out[nome] = {"presente": True, "versao": str(v)}
        except ImportError:
            out[nome] = {"presente": False}
    return out


def gerar() -> dict:
    sys.path.insert(0, str(REPO / "src"))
    import tcf
    cases = AQUI / "cases.json"
    cj = json.loads(cases.read_text(encoding="utf-8")) if cases.exists() else {}
    sujo = bool(_git("status", "--porcelain"))
    return {
        "schema": "perf-baseline-09/manifest-v1",
        "gerado_por": "bench_perf.manifest",
        "seed": cj.get("seed"),
        "cases_sha256": _sha256(cases) if cases.exists() else None,
        "n_casos": cj.get("n_casos"),
        "tcf_version": getattr(tcf, "__version__", "?"),
        "git": {
            "head": _git("rev-parse", "HEAD"),
            "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
            "dirty": sujo,        # arvore suja = baseline nao-reproduzivel
        },
        "python": {
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
        },
        "plataforma": {
            "system": platform.system(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "cpu_count": __import__("os").cpu_count(),
        },
        "compressores": _compressores(),
        "cython_accel": _cython_ativo(),
    }


def _cython_ativo() -> bool:
    try:
        from tcf.composicional.syntax import _detect_compositions_accelerated
        return bool(_detect_compositions_accelerated)
    except Exception:
        return False


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Manifesto de baseline de performance")
    ap.add_argument("--check", action="store_true",
                    help="valida (aborta se arvore suja / compressor declarado ausente)")
    # vai pro dir de resultados (gitignored) — e' artefato de run, nao fonte
    _default = REPO / "experiments" / "results" / "perf-baseline" / "BASELINE-MANIFEST.json"
    ap.add_argument("--out", default=str(_default))
    args = ap.parse_args(argv)

    m = gerar()
    problemas = []
    if m["git"]["dirty"]:
        problemas.append("arvore git SUJA — baseline nao seria reproduzivel")
    if m["seed"] is None:
        problemas.append("cases.json ausente ou sem seed — gere a matriz antes")

    if args.check:
        print(json.dumps(m, ensure_ascii=False, indent=1))
        for p in problemas:
            print(f"  PROBLEMA: {p}", file=sys.stderr)
        return 1 if problemas else 0

    Path(args.out).write_text(json.dumps(m, ensure_ascii=False, indent=1),
                              encoding="utf-8", newline="\n")
    print(f"manifesto -> {args.out}")
    print(f"  seed={m['seed']} cases_sha={str(m['cases_sha256'])[:12]} "
          f"tcf={m['tcf_version']} git={m['git']['head'][:8]}"
          f"{' DIRTY' if m['git']['dirty'] else ''}")
    print(f"  compressores: " + ", ".join(
        f"{k}={'ok' if v.get('presente') else 'AUSENTE'}" for k, v in m["compressores"].items()))
    for p in problemas:
        print(f"  AVISO: {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
