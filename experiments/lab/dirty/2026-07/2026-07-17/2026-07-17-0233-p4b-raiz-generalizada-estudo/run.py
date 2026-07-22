"""ESTUDO P4b — raiz generalizada: gate do parecer + byte-compat + adversarial + fuzz.

Cada caso: .tcf inspecionável + roundtrip ARQUIVO byte-idêntico ao canônico (assert + diff).
"""
from __future__ import annotations

import json
import random
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[3] / "src"))
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

from proto import decode_root, encode_root  # noqa: E402
from tcf import encode_hierarchical as _core_encode  # noqa: E402
from tcf.hierarchical import HierarchicalError  # noqa: E402


def slug(s: str) -> str:
    flat = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return "-".join("".join(c if c.isalnum() or c in " -" else " " for c in flat).split())[:38].lower()


def wjson(p: Path, obj) -> bytes:
    b = (json.dumps(obj, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    p.write_bytes(b)
    return b


# o GATE do parecer (as 8 formas) + formas extra do funil J1
CASOS = [
    ("dataset classico (INTACTO)", [{"id": 1, "nome": "Ana"}, {"id": 2, "nome": "Bob"}]),
    ("objeto unico", {"device": "s1", "leituras": [1.5, 2.5], "ok": True}),
    ("objeto unico aninhado", {"a": {"b": [1, 2]}, "c": None}),
    ("objeto VAZIO", {}),
    ("array de escalares", [1, 2, 3]),
    ("array de strings", ["a", "b"]),
    ("array-em-array na raiz", [[1, 2], [3]]),
    ("array com null (P3b na raiz)", [1, None, 2]),
    ("escalar int", 42),
    ("escalar float", 9.75),
    ("escalar bool", True),
    ("string", "texto"),
    ("string VAZIA", ""),
    ("string multilinha (escape)", "linha1\nlinha2"),
    ("null na raiz", None),
    ("lista vazia []", []),
    ("[{}] um registro vazio", [{}]),
    ("[{},{}] dois registros vazios", [{}, {}]),
    ("[{},{a}] ragged com vazio (dataset J0)", [{}, {"a": 1}]),
]


def main():
    for d in ("inputs", "intermediates", "outputs"):
        (HERE / d).mkdir(exist_ok=True)
    out = ["ESTUDO P4b — raiz generalizada (#D/#O/#V sobre a API pública; core INTOCADO).", ""]
    out.append("(1) GATE do parecer + J1 (roundtrip ARQUIVO byte-idêntico; tipo da raiz EXATO):")
    ok_all = True
    for j, (nome, raiz) in enumerate(CASOS, 1):
        stem = f"{j:02d}-{slug(nome)}"
        canon = wjson(HERE / "intermediates" / f"{stem}.json", raiz)
        wjson(HERE / "inputs" / f"{stem}.json", raiz)
        wire = encode_root(raiz)
        (HERE / "outputs" / f"{stem}.tcf").write_bytes(wire.encode("utf-8"))
        back = decode_root(wire)
        got = wjson(HERE / "outputs" / f"{stem}-rt.json", back)
        rt = (back == raiz and type(back) is type(raiz) and got == canon)
        ok_all &= rt
        header = wire.split("\n")[0]
        out.append(f"  [{'RT-OK' if rt else 'FALHA!!'}] {nome:<40} {header[:44]}")

    # ---------- byte-compat: dataset J0 NÃO muda 1 byte ----------
    out.append("")
    out.append("(2) BYTE-COMPAT do dataset (J0): wire idêntico ao core puro:")
    ds = [{"id": 1, "nome": "Ana", "tags": ["x", "y"]}, {"id": 2, "nome": "Bob", "tags": []}]
    identico = encode_root(ds) == _core_encode(ds)
    ok_all &= identico
    out.append(f"  encode_root(dataset) == encode_hierarchical(dataset)? {identico}   <- 0 bytes de diferença")

    # ---------- custo do discriminador ----------
    out.append("")
    out.append("(3) CUSTO do discriminador (só quem NÃO é dataset paga):")
    for nome, raiz in [("dataset", ds), ("objeto unico", {"a": 1, "b": "x"}),
                       ("array escalares", [1, 2, 3]), ("escalar", 42), ("null", None), ("[]", [])]:
        w = encode_root(raiz)
        out.append(f"  {nome:<18} {len(w.encode()):>4}B   {w.split(chr(10))[0][:40]}")

    # ---------- adversarial ----------
    out.append("")
    out.append("(4) ADVERSARIAL (blob adulterado/estrangeiro → fail-loud tipado):")
    probes = [
        ("#D sem contagem", "#TCF.8H#D\n"),
        ("#D contagem lixo", "#TCF.8H#Dxx\n"),
        ("#D negativo", "#TCF.8H#D-1\n"),
        ("#D unicode digit", "#TCF.8H#D٣\n"),
        ("#D com corpo apendado", "#TCF.8H#D2\nlixo\n"),
        ("#O com 2 registros", encode_root({"a": 1}).replace("#O", "#O", 1).replace("\n\\1\n", "\n\\2\n") if False else None),
        ("root-kind desconhecido", "#TCF.8H#X\n"),
        ("# sozinho", "#TCF.8H#\n"),
    ]
    for nome, blob in probes:
        if blob is None:
            continue
        try:
            r = decode_root(blob)
            out.append(f"  [FALHA-SILENCIOSA!] {nome}: aceitou {r!r}")
            ok_all = False
        except HierarchicalError as e:
            out.append(f"  [fail-loud OK] {nome:<26} {str(e)[:52]}")
    # #O adulterado pra 2 registros (constrói de verdade: dataset de 2 com prefixo #O)
    w2 = _core_encode([{"a": "1"}, {"a": "2"}]).replace("#TCF.8H", "#TCF.8H#O", 1)
    try:
        r = decode_root(w2)
        out.append(f"  [FALHA-SILENCIOSA!] #O com 2 registros: aceitou {r!r}")
        ok_all = False
    except HierarchicalError as e:
        out.append(f"  [fail-loud OK] {'#O com 2 registros':<26} {str(e)[:52]}")
    # #V adulterado: 2 campos
    wv = _core_encode([{"": "x", "b": "y"}]).replace("#TCF.8H", "#TCF.8H#V", 1)
    try:
        r = decode_root(wv)
        out.append(f"  [FALHA-SILENCIOSA!] #V com 2 campos: aceitou {r!r}")
        ok_all = False
    except HierarchicalError as e:
        out.append(f"  [fail-loud OK] {'#V com 2 campos':<26} {str(e)[:52]}")

    # ---------- distinções que NÃO podem colapsar ----------
    out.append("")
    out.append("(5) DISTINÇÕES preservadas (tipo exato, nunca o envelope):")
    tri = [([], "#D0"), ([{}], "#D1"), ({}, "#V"), (None, "#V"), ("", "#V"), (0, "#V"), (False, "#V")]
    for raiz, esperado in tri:
        w = encode_root(raiz)
        back = decode_root(w)
        ok = back == raiz and type(back) is type(raiz)
        ok_all &= ok
        out.append(f"  {str(raiz)!r:>6} -> {w.split(chr(10))[0]:<16} -> {back!r:>6}  tipo-exato={ok}")
    # dataset [{"":"x"}] (campo vazio LEGÍTIMO de J0) ≠ envelope #V
    ds_vazio = [{"": "x"}]
    w = encode_root(ds_vazio)
    ok = decode_root(w) == ds_vazio and not w.startswith("#TCF.8H#")
    ok_all &= ok
    out.append(f"  [{'OK' if ok else 'FALHA'}] dataset [{{'':'x'}}] segue DATASET (sem #): {w.split(chr(10))[0]!r}")

    # ---------- fuzz ----------
    out.append("")
    rng = random.Random(20260717)

    def gen_root(depth=0):
        k = rng.randint(0, 9)
        if depth > 2 or k < 4:
            return rng.choice([42, "x", True, None, 9.5, "", [1, 2], {"a": 1}])
        if k < 6:
            return [gen_root(depth + 1) for _ in range(rng.randint(0, 3))
                    ] if rng.random() < 0.5 else {"f" + str(i): gen_root(depth + 1) for i in range(rng.randint(0, 3))}
        if k < 8:
            return [{"a": rng.randint(0, 9), "b": rng.choice(["x", None])} for _ in range(rng.randint(1, 3))]
        return rng.choice([[], [{}], [{}, {}], {}])

    okf, N, fora = 0, 8000, 0
    for _ in range(N):
        raiz = gen_root()
        try:
            back = decode_root(encode_root(raiz))
            okf += (back == raiz and type(back) is type(raiz))
        except HierarchicalError:
            fora += 1                                   # listas mistas (P5) etc. — fail-loud esperado
    out.append(f"(6) FUZZ seedado de raízes: RT tipo-exato {okf}/{N - fora} (fora-da-classe fail-loud: {fora})")
    ok_all &= (okf == N - fora)

    out += ["", ("VEREDITO: #D/#O/#V cobre o gate inteiro do parecer + J1, dataset byte-idêntico,"
                 if ok_all else "HÁ FALHA — revisar desenho."),
            "envelope NUNCA escapa, adversarial fail-loud, fuzz tipo-exato. Pronto pro weld."]
    (HERE / "outputs" / "00-resultado.txt").write_bytes(("\n".join(out) + "\n").encode("utf-8"))
    print("\n".join(out))
    assert ok_all


if __name__ == "__main__":
    main()
