"""SINTETICOS DE CONTROLE do fluxo hierarquico — navegacao medida (buckets + mecanismos).

Fonte unica dos casos/decomposicao: tests/fixtures/control_synthetics_h.py (o lab e o
teste de pins leem O MESMO gerador — sem drift). Cada caso: .tcf inspecionavel +
roundtrip ARQUIVO byte-identico (assert) + decomposicao meta/controle/folhas.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

from tcf import decode, encode_hierarchical  # noqa: E402
from tests.fixtures.control_synthetics_h import decompose, gen_cases  # noqa: E402


def wjson(path: Path, obj) -> bytes:
    b = (json.dumps(obj, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    path.write_bytes(b)
    return b


def main():
    for d in ("inputs", "intermediates", "outputs"):
        (HERE / d).mkdir(exist_ok=True)
    out = ["SINTETICOS DE CONTROLE — navegacao do fluxo .8H (buckets meta/controle/folhas).",
           "Vies declarado: casos de DESIGN construidos pra OBSERVAR mecanismos, nao pra ganhar bytes.", ""]
    tab = ["caso;n_docs;json_B;tcf_B;meta_B;controle_B;folhas_B;pct_folhas;n_cols_controle"]

    linhas = []
    for j, (key, (desc, mecanismo, docs)) in enumerate(gen_cases().items(), 1):
        stem = f"{j:02d}-{key}"
        wjson(HERE / "inputs" / f"{stem}.json", docs)
        canon = wjson(HERE / "intermediates" / f"{stem}.json", docs)
        wire = encode_hierarchical(docs)
        (HERE / "outputs" / f"{stem}.tcf").write_bytes(wire.encode("utf-8"))
        back = decode(wire)
        got = wjson(HERE / "outputs" / f"{stem}-rt.json", back)
        assert back == docs and got == canon, f"RT FALHOU em {stem}"

        d = decompose(wire)
        njson = len(json.dumps(docs, ensure_ascii=False, separators=(",", ":")).encode())
        pct_f = 100.0 * d["folhas"] / d["total"]
        tab.append(f"{key};{len(docs)};{njson};{d['total']};{d['meta']};{d['controle']};"
                   f"{d['folhas']};{pct_f:.1f};{d['n_cols_controle']}")
        linhas.append((key, desc, mecanismo, len(docs), njson, d, pct_f))

    out.append("(1) NAVEGACAO — pra onde os bytes vao (RT-validado caso a caso):")
    out.append(f"    {'caso':<24}{'docs':>5}{'json':>7}{'tcf':>7}{'meta':>6}{'ctrl':>6}"
               f"{'folhas':>7}{'%f':>6}{'#ctrl':>6}")
    for key, desc, mecanismo, n, njson, d, pct_f in linhas:
        out.append(f"    {key:<24}{n:>5}{njson:>7}{d['total']:>7}{d['meta']:>6}"
                   f"{d['controle']:>6}{d['folhas']:>7}{pct_f:>5.1f}%{d['n_cols_controle']:>5}")

    out.append("")
    out.append("(2) LEITURA por mecanismo (o que cada caso observa):")
    for key, desc, mecanismo, n, njson, d, pct_f in linhas:
        out.append(f"    {key}: {desc}")
        out.append(f"        alvo: {mecanismo}")
        cols = " · ".join(f"{p}/{k}={b}B" for p, k, b in d["cols"])
        out.append(f"        colunas: {cols}")

    # pares/asserts de navegacao que o teste vai pinar
    d2 = dict(zip([l[0] for l in linhas], [l[5] for l in linhas]))
    out.append("")
    out.append("(3) PARES DE CONTROLE:")
    c02, c03 = d2["c02-telemetria-array"], d2["c03-telemetria-split"]
    out.append(f"    fan-out-split (H-HIER-FANOUT-SPLIT-01): array={c02['total']}B vs "
               f"split={c03['total']}B -> delta={c02['total'] - c03['total']:+d}B "
               f"({100.0 * (c02['total'] - c03['total']) / c02['total']:.1f}% do array)")
    c06 = d2["c06-null-elemento"]
    out.append(f"    emask densa (H-HIER-EMASK-SPARSE-01): controle={c06['controle']}B vs "
               f"folhas={c06['folhas']}B (razao {c06['controle'] / c06['folhas']:.2f})")
    c01 = d2["c01-uniforme"]
    out.append(f"    baseline uniforme: {c01['n_cols_controle']} colunas de controle (esperado 0)")

    (HERE / "outputs" / "00-resultado.txt").write_bytes(("\n".join(out) + "\n").encode("utf-8"))
    (HERE / "outputs" / "01-navegacao.csv").write_bytes(("\n".join(tab) + "\n").encode("utf-8"))
    print("\n".join(out))


if __name__ == "__main__":
    main()
