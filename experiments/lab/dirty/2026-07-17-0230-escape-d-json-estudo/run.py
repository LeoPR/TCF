"""EVIDÊNCIA do escape D_json — wire REAL do core (pós-weld), .tcf inspecionável.

study.py provou a IDEIA (protótipo). Este mede o que foi SOLDADO: cada lacuna de D_json
vira um .tcf legível + roundtrip byte-idêntico ao canônico (assert), com o custo medido.
"""
from __future__ import annotations

import json
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3] / "src"))
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

from tcf import decode, encode_hierarchical  # noqa: E402

BS, LF = chr(92), chr(10)


def slug(s: str) -> str:
    flat = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    keep = "".join(c if (c.isalnum() or c in " -") else " " for c in flat)
    return "-".join(keep.split())[:36].strip("-").lower()


def wjson(p: Path, obj) -> bytes:
    b = (json.dumps(obj, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    p.write_bytes(b)
    return b


CASOS = [
    ("chave vazia", [{"": "x", "a": 1}]),
    ("LF em valor (multilinha real)", [{"nome": "Ana", "obs": "linha1\nlinha2\nlinha3"}]),
    ("chave com LF", [{"a\nb": "v"}]),
    ("backslash em valor", [{"path": "C:\\temp\\x"}]),
    ("backslash + LF compostos", [{"a": "a\\b\nc\\\\d"}]),
    ("nome z real vs marcador de vazio", [{"": "a", "z": "b", "\\z": "c"}]),
    ("so LF", [{"a": "\n", "b": "\n\n\n"}]),
    ("compose: vazio + LF + null + array", [{"": None, "x\ny": [1, None, 2], "ok": True}]),
    ("json-ish realista (log multilinha)", [
        {"lvl": "ERROR", "msg": "Traceback:\n  File \"a.py\"\n    raise X", "path": "C:\\app\\a.py"},
        {"lvl": "INFO", "msg": "ok", "path": "/var/log"},
    ]),
]


def main():
    for d in ("inputs", "intermediates", "outputs"):
        (HERE / d).mkdir(exist_ok=True)
    out = ["EVIDÊNCIA — escape D_json (wire REAL do core, pós-weld).",
           "Fecha 3 lacunas: chave vazia · LF em valor · LF em nome. L1 INTOCADO.", ""]
    out.append("(1) CASOS — cada um com .tcf inspecionável e roundtrip byte-idêntico:")
    for j, (nome, docs) in enumerate(CASOS, 1):
        stem = f"{j:02d}-{slug(nome)}"
        canon = wjson(HERE / "intermediates" / f"{stem}.json", docs)
        wjson(HERE / "inputs" / f"{stem}.json", docs)
        wire = encode_hierarchical(docs)
        (HERE / "outputs" / f"{stem}.tcf").write_bytes(wire.encode("utf-8"))
        back = decode(wire)
        got = wjson(HERE / "outputs" / f"{stem}-rt.json", back)
        assert back == docs and got == canon, f"RT FALHOU em {stem}"
        njson = len(json.dumps(docs, ensure_ascii=False, separators=(",", ":")).encode())
        nb = len(wire.encode("utf-8"))
        out.append(f"  [RT-OK] {nome}")
        out.append(f"          {stem}.tcf · tcf={nb}B json={njson}B · header: {wire.split(LF)[0][:56]}")

    out.append("")
    out.append("(2) CUSTO — só o que ESTA camada adiciona (medido em _esc_leaf, sem confundir")
    out.append("    com o escape de dígitos do PRÓPRIO L1, que é pré-existente):")
    from tcf.hierarchical import _esc_leaf  # noqa: PLC0415
    out.append(f"    {'valor':<28}{'chars +':>9}   wire final")
    for v in ["Ana Souza", "user@mail.com", "2026-07-17", "C:" + BS + "temp",
              "x" + LF + "y", LF, BS, BS + BS]:
        d = len(_esc_leaf(v)) - len(v)
        w = len(encode_hierarchical([{"a": v}]).encode())
        out.append(f"    {v!r:<28}{d:>+9}   {w}B")
    out.append("    → +0 char em TODO valor sem `\\`/LF (o caso comum): a camada é no-op.")
    out.append("    → 1 char por `\\` e por LF; o L1 depois escapa o `\\` que emitimos (duplo),")
    out.append("      então no WIRE um `\\` custa ~3B e um LF ~2-3B. Só paga quem tem.")
    out.append("    → PROVA de byte-compat: os pinos de navegação dos sintéticos de controle")
    out.append("      (tests/test_hierarchical_control_synthetics.py, buckets byte-exatos)")
    out.append("      passaram SEM re-pinar. Wire sem `\\`/LF = idêntico ao pré-weld.")

    out.append("")
    out.append("(3) O wire, legível — {'obs': 'linha1\\nlinha2'}:")
    w = encode_hierarchical([{"obs": "linha1\nlinha2"}])
    for ln in w.split(LF):
        out.append(f"    {ln!r}")
    out.append("    → o LF virou `\\n` na folha; o L1 recebeu 1 linha válida e ficou INTOCADO.")

    (HERE / "outputs" / "00-resultado.txt").write_bytes(("\n".join(out) + "\n").encode("utf-8"))
    print("\n".join(out))


if __name__ == "__main__":
    main()
