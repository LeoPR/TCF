"""ESTUDO P4a (PRÉ-WELD) — valida a IDEIA do count recursivo (didático + fuzz de profundidade).

Papel: protótipo. `proto.py` extrai a ideia, não serializa wire — por isso este script NÃO produz
`.tcf` e NÃO é dono dos artefatos do lab. A evidência de WIRE (o que foi soldado) está em `run.py`,
que passa pelo core e emite `outputs/*.tcf` + roundtrip diffável. Ver result.md.
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.stdout.reconfigure(encoding="utf-8")  # console cp1252 não imprime '∘'
from proto import P4Error, decode, encode, meta_str  # noqa: E402


def main():
    out = ["ESTUDO P4a — array-em-array via COUNT RECURSIVO. RT + meta por nível.", ""]
    (HERE / "intermediates").mkdir(exist_ok=True); (HERE / "outputs").mkdir(exist_ok=True)

    # ---------- didático (o gate do checkpoint do owner) ----------
    did = json.loads((HERE / "inputs" / "01-didatico-array-em-array.json").read_text(encoding="utf-8"))
    out.append("(1) DIDÁTICO (gate do checkpoint 2026-07-16):")
    all_ok = True
    for j, (nome, docs) in enumerate([(k, v) for k, v in did.items() if not k.startswith("_")], 1):
        try:
            fields, cols, n = encode(docs)
            back = decode(fields, cols, n)
            ok = back == docs
        except Exception as e:  # noqa: BLE001
            ok = False
            back = f"{type(e).__name__}: {e}"
        all_ok &= ok
        out.append(f"  [{'RT-OK' if ok else 'FALHA!!'}] {nome}")
        out.append(f"       meta (PEDAGÓGICO, não é wire — o wire real está em run.py): {meta_str(fields)}")
        if not ok:
            out.append(f"       obtido: {back}")
        _ = j  # artefatos são de run.py (wire real); o protótipo não serializa

    # ---------- fuzz de PROFUNDIDADE (custo + RT em escala) ----------
    out.append("")
    out.append("(2) FUZZ de profundidade (seedado; arrays aninhados até nível 4, nulls, tipos):")
    rng = random.Random(20260716)

    def gen_arr(depth, st):
        k = rng.randint(0, 3)
        if depth == 0:
            base = {"n": lambda: rng.randint(0, 99), "b": lambda: rng.random() < 0.5,
                    "s": lambda: rng.choice(["a", "b,c", "x"])}[st]
            return [None if rng.random() < 0.2 else base() for _ in range(k)]
        return [None if rng.random() < 0.15 else gen_arr(depth - 1, st) for _ in range(k)]

    ok_n, N = 0, 4000
    for _ in range(N):
        depth = rng.randint(1, 4)
        st = rng.choice(["n", "b", "s"])
        docs = [{"id": i, "m": gen_arr(depth, st)} for i in range(rng.randint(1, 4))]
        try:
            fields, cols, n = encode(docs)
            assert decode(fields, cols, n) == docs
            ok_n += 1
        except P4Error:
            raise
    out.append(f"  RT byte-exato: {ok_n}/{N} (profundidade 1-4, ~20% null por nível, n/b/s)")

    # ---------- adversarial de frame (o invariante count×emask×leaf por nível) ----------
    out.append("")
    out.append("(3) ADVERSARIAL de frame (invariantes por nível — fail-loud, nunca silencioso):")
    docs = [{"m": [[1, 2], [3]]}]
    fields, cols, n = encode(docs)
    import copy
    for nome, mutila in [
        ("count interno TRUNCADO", lambda c: c[(("m",), "count", 1)].pop()),
        ("count interno EXCEDENTE", lambda c: c[(("m",), "count", 1)].append(9)),
        ("folha faltando", lambda c: c[(("m",), "leaf")].pop()),
        ("folha sobrando", lambda c: c[(("m",), "leaf")].append("99")),
    ]:
        c2 = copy.deepcopy(cols)
        mutila(c2)
        try:
            r = decode(fields, c2, n)
            out.append(f"  [FALHA-SILENCIOSA!] {nome}: decodou {r}")
            all_ok = False
        except P4Error as e:
            out.append(f"  [fail-loud OK] {nome}: {str(e)[:50]}")

    out += ["", ("VEREDITO (da IDEIA): count recursivo faz RT no gate inteiro + fuzz de profundidade;"
                 if all_ok else "HÁ FALHA — revisar design."),
            "frames mutilados fail-loud. Estrutura (counts por nível) legível sem materializar folhas.",
            "Gramática por nível demonstrada: m#[#[]] (2 níveis), cubo#[#[#[]]] (3), com '?' por nível.",
            "NOTA: metas acima são PEDAGÓGICOS (sem sizes). Wire real + .tcf: run.py / 00-resultado.txt."]
    (HERE / "outputs" / "00-estudo-proto.txt").write_bytes(("\n".join(out) + "\n").encode("utf-8"))
    print("\n".join(out))
    assert all_ok


if __name__ == "__main__":
    main()
