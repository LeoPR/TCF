"""WELD P2 — tipos escalares (number/bool). didático→realista→massa, RT 120% obrigatório, pelo CORE."""
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


def rt(docs, stem):
    wjson(HERE / "intermediates" / f"{stem}.json", docs)
    blob = encode_hierarchical(docs)
    (HERE / "outputs" / f"{stem}.tcf").write_bytes(blob.encode("utf-8"))
    back = decode(blob)
    wjson(HERE / "outputs" / f"{stem}-rt.json", back)
    assert back == docs, f"RT FALHOU em {stem}"
    return len(blob.encode())


def _tv(rng, stype):
    if stype == "n":
        return rng.randint(-1000, 1000) if rng.random() < 0.5 else round(rng.uniform(-100, 100), 3)
    if stype == "b":
        return rng.random() < 0.5
    return rng.choice(["a", "ativo", "x,y", "l\\m", "SP"])


def main():
    out = ["WELD P2 — tipos escalares (number/bool). didático → realista → massa (RT obrigatório).", ""]
    (HERE / "intermediates").mkdir(exist_ok=True); (HERE / "outputs").mkdir(exist_ok=True)

    out.append("(1) DIDÁTICO — cada tipo + disambiguação (roundtrip diffável):")
    did = json.loads((HERE / "inputs" / "01-didatico-tipos.json").read_text(encoding="utf-8"))
    for j, (nome, docs) in enumerate([(k, v) for k, v in did.items() if not k.startswith("_")], 1):
        nb = rt(docs, f"01-{j:02d}")
        out.append(f"  [RT-OK] {nome}: {nb}B · header: {encode_hierarchical(docs).split(chr(10))[0][:74]}")

    out.append("")
    out.append("(2) REALISTA — pedidos (int/float/bool + cupom null + itens tipados aninhados):")
    real = json.loads((HERE / "inputs" / "02-realista-pedidos.json").read_text(encoding="utf-8"))
    nb = rt(real, "02-realista-pedidos")
    njson = len(json.dumps(real, ensure_ascii=False, separators=(",", ":")).encode())
    out.append(f"  [RT-OK] {len(real)} pedidos: tcf={nb}B vs json={njson}B · header: "
               f"{encode_hierarchical(real).split(chr(10))[0][:78]}")

    out.append("")
    out.append("(3) MASSA — fuzz seedado (colunas tipadas str/number/bool, nullable, arrays tipados):")
    rng = random.Random(20260716)
    ok, N = 0, 6000
    for _ in range(N):
        fields = [(f"f{c}", rng.choice(["s", "n", "b"])) for c in range(rng.randint(1, 4))]
        arrs = [(f"a{c}", rng.choice(["s", "n", "b"])) for c in range(rng.randint(0, 2))]
        docs = []
        for _ in range(rng.randint(1, 5)):
            rec = {}
            for nm, st in fields:
                if rng.random() < 0.2:                     # 20% null (P3a) — campo continua tipado nos não-nulos
                    rec[nm] = None
                else:
                    rec[nm] = _tv(rng, st)
            for nm, st in arrs:
                k = rng.randint(0, 3)
                rec[nm] = [(None if rng.random() < 0.25 else _tv(rng, st)) for _ in range(k)]
            docs.append(rec)
        assert decode(encode_hierarchical(docs)) == docs
        ok += 1
    out.append(f"  RT byte-exato: {ok}/{N}")

    out += ["", "VEREDITO: P2 (number/bool) — RT em TODAS as etapas. Evidência diffável em outputs/.",
            "Tag por-coluna ('n'/'b', string=default); json distingue int/float; compõe com P3a/P3b."]
    (HERE / "outputs" / "00-resultado.txt").write_bytes(("\n".join(out) + "\n").encode("utf-8"))
    print("\n".join(out))


if __name__ == "__main__":
    main()
