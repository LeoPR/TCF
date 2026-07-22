"""ESTUDO P1 — presença/ragged: exemplos vistoriáveis + medições + contraprovas.

Roda os 3 clássicos ragged (inputs/*.json) pelo protótipo (proto.py):
  intermediates/NN-*.json  = entrada canônica (LF, re-serializada)  — o que entra
  outputs/NN-*.tcf         = o wire #TCF.8H com máscara              — o que trafega
  outputs/NN-*-rt.json     = decode                                  — DIFFÁVEL byte-idêntico
Depois: (M1) custo da máscara isolado + colapso RLE em escala; (M2) contraprova do
sentinela ""; (M3) compat: dado uniforme fica BYTE-IDÊNTICO ao weld atual; (M4) bytes
vs JSON compacto. Zero mudança em src/tcf.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[3] / "src"))

from proto import decode_h, encode_h  # noqa: E402
from tcf import decode as tcf_decode, encode as tcf_encode, encode_hierarchical  # noqa: E402


def wjson(path, obj):
    path.write_bytes((json.dumps(obj, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def wtext(path, s):
    path.write_bytes(s.encode("utf-8"))


def main():
    out = ["ESTUDO P1 — presença/ragged (def-level) no #TCF.8H", ""]
    inter, outs = HERE / "intermediates", HERE / "outputs"
    inter.mkdir(exist_ok=True); outs.mkdir(exist_ok=True)

    # ---------- RT dos 3 clássicos ragged (arquivos diffáveis) ----------
    out.append("RT dos clássicos ragged (roundtrip = ARQUIVO diffável):")
    for f in sorted((HERE / "inputs").glob("*.json")):
        docs = json.loads(f.read_text(encoding="utf-8"))
        wjson(inter / f.name, docs)                       # canônico LF
        blob = encode_h(docs)
        wtext(outs / f"{f.stem}.tcf", blob)
        back = decode_h(blob)
        wjson(outs / f"{f.stem}-rt.json", back)
        ok = back == docs
        njson = len(json.dumps(docs, ensure_ascii=False, separators=(",", ":")).encode())
        out.append(f"  [{'OK' if ok else 'FALHA'}] {f.name}: RT={ok} · tcf={len(blob.encode()):>4}B "
                   f"vs json-compacto={njson:>4}B · header: {blob.split(chr(10))[0][:100]}")
        assert ok, f"RT falhou em {f.name}"

    # ---------- M1: custo da máscara isolado + colapso RLE em escala ----------
    out += ["", "M1 — custo da MÁSCARA (coluna de controle, comprimida pelo L1):"]
    for n, raro in ((100, True), (100, False), (2000, True), (2000, False)):
        # 'raro' = ausente a cada 20 (regime API tipico); senao alternado (pior caso p/ RLE)
        recs = []
        for i in range(n):
            r = {"id": f"{i:05d}", "campo": f"valor-{i}"}
            if (i % 20 != 0) if raro else (i % 2 == 0):
                r["opcional"] = f"extra-{i}"
            recs.append(r)
        mask_vals = ["." if "opcional" in r else "-" for r in recs]
        mask_bytes = len(tcf_encode(mask_vals).encode())
        total = len(encode_h(recs).encode())
        assert decode_h(encode_h(recs)) == recs
        out.append(f"  n={n:>4} regime={'raro(1/20 ausente)' if raro else 'alternado(1/2)'}: "
                   f"máscara={mask_bytes:>4}B ({mask_bytes/n:.2f} B/registro) · blob total={total}B")
    out.append("  → máscara regular colapsa por RLE (runs de '.'); alternada paga ~1 B/linha + \\n.")

    # ---------- M2: contraprova do SENTINELA '' (a alternativa barata é LOSSY) ----------
    out += ["", "M2 — contraprova: sentinela '' NO LUGAR da máscara é LOSSY:"]
    a = [{"x": "1", "op": ""}, {"x": "2"}]               # op VAZIO no rec 0; AUSENTE no rec 1
    sent = [{"x": r["x"], "op": r.get("op", "")} for r in a]   # coercao sentinela
    out.append(f"  entrada: {a!r}")
    out.append(f"  com sentinela '' os dois registros viram: {sent!r} → ''-vazio e ausente COLIDEM")
    blob = encode_h(a)
    ok = decode_h(blob) == a
    out.append(f"  com MÁSCARA: RT={ok} (preserva ''≠ausente) — por isso presença precisa de canal próprio.")
    assert ok

    # ---------- M3: compatibilidade — dado UNIFORME fica byte-idêntico ao weld ----------
    out += ["", "M3 — compat: dado SEM ragged → wire BYTE-IDÊNTICO ao weld atual (src/tcf):"]
    uni = [{"nome": "Ana", "tels": ["a", "b"], "end": {"rua": "R1", "cid": "SP"}},
           {"nome": "Bob", "tels": [], "end": {"rua": "R2", "cid": "SP"}}]
    p, w = encode_h(uni), encode_hierarchical(uni)
    out.append(f"  proto == weld: {p == w} ({len(p.encode())}B) — campos uniformes não pagam nada,")
    out.append("  '?' só aparece onde há raggedness real (deduzido do dado, como o resto do header).")
    assert p == w and tcf_decode(w) == uni

    # ---------- M4: escala realista com raggedness (API-like) ----------
    out += ["", "M4 — escala API-like (n=1000, 3 opcionais com frequências 90%/50%/5%):"]
    import random
    rng = random.Random(20260715)
    recs = []
    for i in range(1000):
        r = {"id": f"{i:06d}", "nome": f"cliente-{i:04d}"}
        if rng.random() < 0.90:
            r["email"] = f"c{i}@exemplo.com.br"
        if rng.random() < 0.50:
            r["telefone"] = f"+55 11 9{i%10000:04d}-{i%9999:04d}"
        if rng.random() < 0.05:
            r["obs"] = f"nota especial {i}"
        recs.append(r)
    blob = encode_h(recs)
    assert decode_h(blob) == recs
    njson = len(json.dumps(recs, ensure_ascii=False, separators=(",", ":")).encode())
    ntcf = len(blob.encode())
    out.append(f"  RT=True · tcf={ntcf}B vs json-compacto={njson}B ({100*(1-ntcf/njson):.1f}% menor)")
    out.append("  (JSON 'paga' ausência omitindo nome+valor; TCF paga máscara mas NUNCA repete nome —")
    out.append("   quanto mais registros, mais o header fixo dilui.)")

    # ---------- M5: bordas de forma ----------
    out += ["", "M5 — bordas de forma (RT em cada):"]
    bordas = {
        "objeto opcional COM filho opcional": [
            {"a": "1", "cfg": {"tema": "dark", "fonte": "14"}},
            {"a": "2"},                                   # cfg ausente
            {"a": "3", "cfg": {"tema": "light"}},         # cfg presente, fonte ausente
        ],
        "opcional presente em SO' 1 registro": [
            {"x": "1"}, {"x": "2"}, {"x": "3", "raro": "sim"}, {"x": "4"},
        ],
        "ordem de chave heterogenea (dict == ignora ordem)": [
            {"a": "1", "b": "2"}, {"b": "3", "a": "4"},
        ],
        "array opcional: ausente vs vazio vs cheio": [
            {"n": "A", "tags": ["x", "y"]}, {"n": "B", "tags": []}, {"n": "C"},
        ],
        "opcional dentro de array de objetos (mask por INSTANCIA)": [
            {"g": [{"v": "1", "op": "a"}, {"v": "2"}]},
            {"g": []},
            {"g": [{"v": "3"}, {"v": "4", "op": "b"}, {"v": "5"}]},
        ],
    }
    for nome, docs in bordas.items():
        ok = decode_h(encode_h(docs)) == docs
        out.append(f"  [{'OK' if ok else 'FALHA'}] {nome}: RT={ok}")
        assert ok, nome

    # fail-loud declarados (P1 nao engole o que e' de P2/P3)
    out += ["", "M5b — fail-loud declarado (fronteiras de P1):"]
    import proto
    for nome, docs in {"null em valor (P3)": [{"x": None}],
                       "nome com '?' sem escape": None}.items():
        if docs is None:
            # '?' em NOME agora e' estrutural -> tem que ser escapado e fazer RT
            d = [{"tem?duvida": "sim"}]
            ok = decode_h(encode_h(d)) == d
            out.append(f"  [{'OK' if ok else 'FALHA'}] nome com '?' e' ESCAPADO e faz RT: {ok}")
            assert ok
            continue
        try:
            encode_h(docs)
            out.append(f"  [FALHA] {nome}: NAO deu fail-loud")
            raise AssertionError(nome)
        except proto.P1Error as e:
            out.append(f"  [OK] {nome}: P1Error ({str(e)[:60]})")

    wtext(outs / "00-medicoes.txt", "\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
