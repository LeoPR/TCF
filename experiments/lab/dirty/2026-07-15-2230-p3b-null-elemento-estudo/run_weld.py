"""WELD P3b — evidência didático→realista→massa pelo CORE (não pelo proto). RT 120% obrigatório.

Didático: as 8 formas do estudo (inputs/01). Realista: telemetria c/ leituras/alertas null (inputs/02).
Massa: fuzz seedado de arrays com elementos null (escalar+objeto, posições/counts/aninhamento variados)
— pega escapes em escala. Cada roundtrip = arquivo diffável byte-idêntico."""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[4] / "src"))
from tcf import decode, encode_hierarchical  # noqa: E402


def wjson(path, obj):
    path.write_bytes((json.dumps(obj, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def rt_arquivo(docs, stem):
    wjson(HERE / "intermediates" / f"{stem}.json", docs)
    blob = encode_hierarchical(docs)
    (HERE / "outputs" / f"{stem}.tcf").write_bytes(blob.encode("utf-8"))
    back = decode(blob)
    wjson(HERE / "outputs" / f"{stem}-rt.json", back)
    assert back == docs, f"RT FALHOU em {stem}"
    return len(blob.encode())


def _scalar(rng):
    return rng.choice(["a", "b", "ativo", "x,y", "l\\m", "..."]) if rng.random() < 0.6 \
        else str(rng.randint(0, 500))


def _gen_doc(rng, fields):
    """fields = [(nome, is_obj)] fixo do BATCH → element-kind consistente por campo (in-class)."""
    rec = {"id": f"{rng.randint(0, 9999):04d}"}
    for nome, is_obj in fields:
        k = rng.randint(0, 4)
        arr = []
        for _ in range(k):
            if rng.random() < 0.3:                      # ~30% dos elementos null
                arr.append(None)
            elif is_obj:
                arr.append({"v": _scalar(rng), "w": _scalar(rng)})
            else:
                arr.append(_scalar(rng))
        rec[nome] = arr
    return rec


def main():
    out = ["WELD P3b — null em ELEMENTO (element-mask). didático → realista → massa (RT obrigatório).", ""]
    (HERE / "intermediates").mkdir(exist_ok=True); (HERE / "outputs").mkdir(exist_ok=True)

    # (1) DIDÁTICO
    out.append("(1) DIDÁTICO — 8 formas (roundtrip diffável em outputs/):")
    did = json.loads((HERE / "inputs" / "01-didatico-null-elemento.json").read_text(encoding="utf-8"))
    for j, (nome, docs) in enumerate([(k, v) for k, v in did.items() if not k.startswith("_")], 1):
        nb = rt_arquivo(docs, f"w1-{j:02d}")
        hdr = encode_hierarchical(docs).split("\n", 1)[0]
        out.append(f"  [RT-OK] {nome}: {nb}B · header: {hdr[:70]}")

    # (2) REALISTA
    out.append("")
    out.append("(2) REALISTA — telemetria c/ leituras/alertas null (elemento-objeto E escalar):")
    real = json.loads((HERE / "inputs" / "02-realista-telemetria.json").read_text(encoding="utf-8"))
    nb = rt_arquivo(real, "w2-realista-telemetria")
    out.append(f"  [RT-OK] {len(real)} devices: {nb}B · header: {encode_hierarchical(real).split(chr(10))[0][:78]}")

    # (3) MASSA — fuzz seedado de arrays com elementos null
    out.append("")
    out.append("(3) MASSA — fuzz seedado (arrays com ~30% elementos null, escalar+objeto, aninhado):")
    rng = random.Random(20260715)
    ok = 0
    N = 6000
    cov = {"elem_null": 0, "arr_vazio": 0, "elem_obj_null": 0}
    for _ in range(N):
        fields = [(f"arr{a}", rng.random() < 0.4) for a in range(rng.randint(1, 3))]  # schema fixo do batch
        docs = [_gen_doc(rng, fields) for _ in range(rng.randint(1, 5))]
        flat = json.dumps(docs)
        if "null" in flat:
            cov["elem_null"] += 1
        if "[]" in flat:
            cov["arr_vazio"] += 1
        if any(isinstance(v, list) and any(isinstance(e, dict) for e in v) and any(e is None for e in v)
               for d in docs for v in d.values() if isinstance(v, list)):
            cov["elem_obj_null"] += 1
        assert decode(encode_hierarchical(docs)) == docs
        ok += 1
    out.append(f"  RT byte-exato: {ok}/{N} · cobertura: elem-null {cov['elem_null']} · arr-vazio "
               f"{cov['arr_vazio']} · elem-objeto-null {cov['elem_obj_null']}")

    out += ["", "VEREDITO: P3b (null em elemento) — RT em TODAS as etapas. Evidência diffável em outputs/w*.",
            "Zero engenhoca (core real). Alfabeto element-mask 2-estados; count×emask×dense alinhado."]
    (HERE / "outputs" / "00-weld-resultado.txt").write_bytes(("\n".join(out) + "\n").encode("utf-8"))
    print("\n".join(out))


if __name__ == "__main__":
    main()
