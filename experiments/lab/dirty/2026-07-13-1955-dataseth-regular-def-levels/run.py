"""P4 runner: refuta R1 (leaf-kinds-only) e prova R2 (def-level+kind) na forma regular.

Reproducível; escreve artifacts/ (contra-exemplo R1, streams R2, RT, bytes).
Rodar: python run.py
"""

from __future__ import annotations

from pathlib import Path

from regular import (
    decode_r1,
    decode_r2,
    derive_schema,
    encode_r1,
    encode_r2,
    leaf_paths,
    packed_bits_estimate,
)
from model_ext import from_python_ext, semantic_key
from wire_ac import encode as encode_v  # V per-instance (variante A) como baseline

ART = Path(__file__).resolve().parent / "artifacts"
ART.mkdir(exist_ok=True)

NAN, INF = float("nan"), float("inf")


def rows_of(pyrows: list[dict]):
    return [from_python_ext(r).root for r in pyrows]


def keys_of(rows):
    return [semantic_key(r) for r in rows]


def main() -> None:
    lines = []

    # ---------------------------------------------------------------- (1) FALSIFICADOR
    # ancestral-ausente vs ancestral-presente-VAZIO vs folha-null: 3 linhas distintas.
    killer_py = [
        {},                     # b ausente
        {"b": {}},              # b presente, vazio
        {"b": {"c": None}},     # b presente, c null
        {"b": {"c": NAN}},      # b presente, c NaN (especial na cadeia opcional)
    ]
    killer = rows_of(killer_py)
    schema = derive_schema(killer)
    n = len(killer)

    # R1: leaf-kinds-only — DEVE colidir nas linhas 0 e 1
    r1 = encode_r1(killer, schema)
    back1 = decode_r1(r1, schema, n)
    k_orig = keys_of(killer)
    k_back1 = keys_of(back1)
    collided = (k_back1[0] == k_back1[1]) and (k_orig[0] != k_orig[1])
    rt1_fails = k_back1 != k_orig
    assert collided and rt1_fails, "esperava a colisao estrutural do R1"
    lines.append("R1 (leaf-kinds-only): {} vs {'b':{}} COLIDEM apos decode = True  -> REFUTADO")
    lines.append(f"  streams R1 da folha b.c: {r1[('b','c')]['kinds']}  (linhas 0 e 1 identicas)")

    # R2: def-level+kind — fecha o contra-exemplo
    r2 = encode_r2(killer, schema)
    back2 = decode_r2(r2, schema, n)
    assert keys_of(back2) == k_orig, "R2 deve fechar o contra-exemplo"
    lines.append("R2 (def-level+kind): as 4 linhas RT-exatas e distintas = True")
    lines.append(f"  streams R2 da folha b.c: {r2[('b','c')]['marks']}  (cut@0 vs cut@1 vs null vs nan)")
    lines.append("")

    (ART / "01-r1-counterexample.txt").write_text(
        "linhas: {} | {'b':{}} | {'b':{'c':null}} | {'b':{'c':NaN}}\n"
        f"R1 kinds b.c : {r1[('b','c')]['kinds']}\n"
        f"R1 decode    : linhas 0 e 1 reconstroem IGUAIS (perda estrutural)\n"
        f"R2 marks b.c : {r2[('b','c')]['marks']}\n"
        f"R2 decode    : 4/4 distintas, RT-exato\n",
        encoding="utf-8",
    )

    # ---------------------------------------------------------------- (2) PERFIS RT R2
    profiles = {
        "opt-chain-specials": [
            {"a": 1, "g": {"x": {"lat": -0.0}}},
            {"a": None, "g": {}},
            {"g": {"x": {}}},
            {"a": NAN, "g": {"x": {"lat": INF}}},
            {"a": "NaN"},
        ],
        "ragged-arrays-specials": [
            {"t": []},
            {},
            {"t": [1, 2, 3]},
            {"t": [NAN, -INF]},
            {"t": ["NaN", None]},
        ],
        "mixed-regular-100": (
            [{"id": i, "v": float(i) if i % 3 else NAN, "tags": ["a", "b"][: i % 3]} for i in range(100)]
        ),
    }
    for name, pyrows in profiles.items():
        rows = rows_of(pyrows)
        sch = derive_schema(rows)
        enc = encode_r2(rows, sch)
        back = decode_r2(enc, sch, len(rows))
        ok = keys_of(back) == keys_of(rows)
        assert ok, f"RT R2 falhou em {name}"
        lines.append(f"perfil {name:24s} R2 RT = True   ({len(rows)} linhas, {len(leaf_paths(sch))} folhas)")
    lines.append("")

    # streams de amostra (inspecionavel)
    sample_rows = rows_of(profiles["opt-chain-specials"])
    sch_s = derive_schema(sample_rows)
    enc_s = encode_r2(sample_rows, sch_s)
    sample_txt = []
    for path, col in enc_s.items():
        sample_txt.append(f"{'.'.join(path):12s} marks={col['marks']}")
        if col["payloads"]:
            sample_txt.append(f"{'':12s} payloads={col['payloads']}")
        if col["counts"]:
            sample_txt.append(f"{'':12s} counts={col['counts']}")
    (ART / "02-r2-streams-sample.txt").write_text("\n".join(sample_txt) + "\n", encoding="utf-8")

    # ---------------------------------------------------------------- (3) BYTES (apos RT)
    # R2 custo dos streams: simbolos de marca (estimativa b4) + payloads como texto.
    # V per-instance como baseline (wire A do stage 2). Estimativa declarada, nao packing real.
    cmp_lines = ["perfil | folhas | marcas(simbolos) | b4-est(bytes) | payload(bytes) | V per-instance (bytes)"]
    for name, pyrows in profiles.items():
        rows = rows_of(pyrows)
        sch = derive_schema(rows)
        enc = encode_r2(rows, sch)
        n_marks = sum(len(c["marks"]) for c in enc.values())
        b4_est = packed_bits_estimate(enc, "marks") // 8
        payload_bytes = sum(
            len(str(p if not isinstance(p, tuple) else p[1] or "").encode())
            for c in enc.values()
            for p in c["payloads"]
        ) + sum(len(x) for c in enc.values() for x in c["counts"])
        v_bytes = sum(len(encode_v(from_python_ext(r), "A").encode()) for r in pyrows)
        cmp_lines.append(
            f"{name} | {len(leaf_paths(sch))} | {n_marks} | {b4_est} | {payload_bytes} | {v_bytes}"
        )
    (ART / "03-bytes-comparison.txt").write_text("\n".join(cmp_lines) + "\n", encoding="utf-8")

    (ART / "04-rt-counterproof.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("P4 regular-def-levels: all checks PASS")
    for ln in lines:
        print(" ", ln)
    print("--- bytes ---")
    print("\n".join(cmp_lines))


if __name__ == "__main__":
    main()
