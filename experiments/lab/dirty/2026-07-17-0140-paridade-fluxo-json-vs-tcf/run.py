"""CRITÉRIO EXECUTÁVEL do fluxo do owner — o caminho JSON vs o caminho TCF.

    dataset -> encode -> json -> TRANSMITE -> recebe -> json -> decode -> dataset
    dataset -> encode -> tcf  -> TRANSMITE -> recebe -> tcf  -> decode -> dataset

CRITÉRIO:  ∀D:  J-RT-TX(D)  ⟹  T-RT(D)
"se o caminho JSON faz round-trip ATRAVÉS DA TRANSMISSÃO, o caminho TCF tem de fazer também".

A etapa TRANSMITE é o que torna o critério honesto: mede-se sobre BYTES (UTF-8), não sobre o
str em memória — é o que o owner descreve ("transmite......recebe").

3 níveis medidos por caso:
  N0  = caminho JSON realista  (ensure_ascii=False -> bytes UTF-8 -> loads)
  N0a = caminho JSON ASCII     (ensure_ascii=True: o escape \\uXXXX "salva" casos não-UTF-8)
  N1  = conformidade I-JSON (RFC 7493, o perfil INTEROPERÁVEL restrito)

Veredito por caso: PARIDADE · LACUNA (json faz, TCF não => viola o critério) ·
TCF-SUPERIOR (TCF faz ou recusa honestamente onde o json perde) · AMBOS-RECUSAM.
Zero mudança em src/tcf.
"""
from __future__ import annotations

import json
import math
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3] / "src"))
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

from tcf import decode, encode_hierarchical  # noqa: E402

I_JSON_INT_MAX = 2 ** 53 - 1          # RFC 7493: inteiros seguros (IEEE 754 double)


def j_rt(docs, *, ensure_ascii: bool):
    """Caminho JSON COM a etapa de transmissão (str -> bytes UTF-8 -> str -> loads)."""
    try:
        txt = json.dumps(docs, ensure_ascii=ensure_ascii)
        wire = txt.encode("utf-8")                      # <-- TRANSMITE
        back = json.loads(wire.decode("utf-8"))
        return ("RT" if back == docs else "DIVERGE"), len(wire)
    except Exception as e:                              # noqa: BLE001
        return f"{type(e).__name__}", 0


def t_rt(docs):
    """Caminho TCF com a mesma etapa de transmissão."""
    try:
        wire = encode_hierarchical(docs).encode("utf-8")   # <-- TRANSMITE
        back = decode(wire.decode("utf-8"))
        return ("RT" if back == docs else "DIVERGE"), len(wire)
    except Exception as e:                              # noqa: BLE001
        return f"{type(e).__name__}", 0


def ijson_check(v, path="$") -> list[str]:
    """Conformidade I-JSON (RFC 7493) do VALOR — devolve lista de violações."""
    out = []
    if isinstance(v, dict):
        chaves = list(v.keys())
        coagidas = [k if isinstance(k, str) else json.dumps(k)[1:-1] if not isinstance(k, str) else k
                    for k in chaves]
        # chave não-str vira str no dump -> pode COLIDIR (a duplicata fabricada)
        serial = []
        for k in chaves:
            if isinstance(k, str):
                serial.append(k)
            elif k is None:
                serial.append("null")
            elif isinstance(k, bool):
                serial.append("true" if k else "false")
            elif isinstance(k, (int, float)):
                serial.append(str(k))
            else:
                out.append(f"{path}: chave de tipo {type(k).__name__} não é serializável")
                continue
        if len(serial) != len(set(serial)):
            dups = sorted({s for s in serial if serial.count(s) > 1})
            out.append(f"{path}: nomes DUPLICADOS após serialização {dups} (RFC 7493 §2.3 MUST NOT)")
        del coagidas
        for k, sub in v.items():
            if isinstance(k, str):
                out += _str_check(k, f"{path}.{k}", "nome")
            out += ijson_check(sub, f"{path}.{k}")
    elif isinstance(v, (list, tuple)):
        if isinstance(v, tuple):
            out.append(f"{path}: tuple não existe no modelo JSON (vira array; tipo não volta)")
        for i, sub in enumerate(v):
            out += ijson_check(sub, f"{path}[{i}]")
    elif isinstance(v, str):
        out += _str_check(v, path, "string")
    elif isinstance(v, bool) or v is None:
        pass
    elif isinstance(v, int):
        if abs(v) > I_JSON_INT_MAX:
            out.append(f"{path}: inteiro |{v}| > 2^53-1 (RFC 7493 §2.2: fora da faixa segura)")
    elif isinstance(v, float):
        if not math.isfinite(v):
            out.append(f"{path}: não-finito ({v}) — RFC 8259 §6 não permite; I-JSON idem")
    return out


def _str_check(s: str, path: str, papel: str) -> list[str]:
    try:
        s.encode("utf-8")
    except UnicodeEncodeError:
        return [f"{path}: {papel} contém surrogate solto — não é UTF-8 (RFC 7493 §2.1 MUST)"]
    return []


def gen_casos():
    """(nome, dataset, comentario) — dataset = list[dict], a forma que o TCF aceita hoje."""
    return [
        # --- controle: deve dar PARIDADE ---
        ("escalares comuns", [{"id": 1, "nome": "Ana", "ok": True, "v": 1.5, "n": None}], "baseline"),
        ("aninhado", [{"a": {"b": [1, 2]}, "c": [{"d": "x"}]}], "estrutura"),
        ("unicode", [{"a": "café 中文 🎉"}], "UTF-8 real"),
        ("NFC vs NFD", [{unicodedata.normalize("NFC", "café"): 1,
                         unicodedata.normalize("NFD", "café"): 2}], "chaves distintas"),
        ("tab em valor", [{"a": "x\ty"}], ""),
        ("nul \\x00 em valor", [{"a": "x\x00y"}], ""),
        ("-0.0", [{"a": -0.0}], ""),
        ("0.1+0.2", [{"a": 0.1 + 0.2}], "precisão"),
        ("array vazio", [{"a": []}], ""),
        ("objeto vazio", [{"a": {}, "b": 1}], ""),
        ("null em campo", [{"a": None, "b": 1}], "P3a"),
        ("ragged (chave tardia)", [{"a": 1, "c": 2}, {"a": 3, "obs": "o", "c": 4}], "ordem de chaves"),

        # --- categoria A: lacunas de CAPACIDADE (json faz, TCF não) ---
        ("chave vazia ''", [{"": "x", "a": 1}], "A: JSON válido comum"),
        ("\\n em valor", [{"a": "x\ny"}], "A: JSON válido comum"),
        ("chave com \\n", [{"a\nb": "x"}], "A"),

        # --- categoria C: defeitos do json (ele aceita e perde/corrompe) ---
        ("NaN", [{"a": float("nan")}], "C: RFC 8259 §6 proíbe"),
        ("+Infinity", [{"a": float("inf")}], "C: RFC 8259 §6 proíbe"),
        ("-Infinity", [{"a": float("-inf")}], "C"),
        ("tuple", [{"a": (1, 2)}], "C: tipo não volta"),
        ("chave int", [{1: "x"}], "C"),
        ("chave int + str (DUPLICATA)", [{1: "x", "1": "y"}], "C: json FABRICA duplicata"),
        ("chave bool", [{True: "x"}], "C"),
        ("chave None", [{None: "x"}], "C"),
        ("lone surrogate em valor", [{"a": "\ud800"}], "C: não é UTF-8"),
        ("int > 2^53 (I-JSON)", [{"a": 2 ** 53 + 1}], "C: fora da faixa segura I-JSON"),
        ("int gigante 10**30", [{"a": 10 ** 30}], "C: idem"),
    ]


def veredito(j, t, ijson_ok):
    """O critério: J-RT ⟹ T-RT."""
    j_ok, t_ok = (j == "RT"), (t == "RT")
    if j_ok and t_ok:
        return "PARIDADE"
    if j_ok and not t_ok:
        return "LACUNA" if ijson_ok else "TCF-ESTRITO"   # se o json só "passa" fora do I-JSON, não é lacuna
    if t_ok and not j_ok:
        return "TCF-SUPERIOR"
    return "AMBOS-RECUSAM"


def main():
    for d in ("inputs", "intermediates", "outputs"):
        (HERE / d).mkdir(exist_ok=True)
    out = ["CRITÉRIO DO FLUXO — J-RT-TX(D) ⟹ T-RT(D)  ('se o json faz, o tcf tem de fazer')",
           "TRANSMITE medido em BYTES UTF-8 (não no str em memória). N1 = I-JSON (RFC 7493).", ""]
    linhas = []
    for nome, docs, com in gen_casos():
        j, jb = j_rt(docs, ensure_ascii=False)
        ja, _ = j_rt(docs, ensure_ascii=True)
        t, tb = t_rt(docs)
        viol = ijson_check(docs)
        ijson_ok = not viol
        v = veredito(j, t, ijson_ok)
        linhas.append((nome, j, ja, t, "OK" if ijson_ok else "viola", v, com, viol, jb, tb))

    out.append(f"    {'caso':<30}{'json':>9}{'json-ascii':>12}{'tcf':>20}{'I-JSON':>8}  veredito")
    for nome, j, ja, t, ij, v, com, viol, jb, tb in linhas:
        out.append(f"    {nome:<30}{j:>9}{ja:>12}{t[:19]:>20}{ij:>8}  {v}")

    out.append("")
    out.append("VIOLAÇÕES I-JSON detectadas (RFC 7493 — o perfil INTEROPERÁVEL):")
    for nome, *_rest, viol, _jb, _tb in linhas:
        for x in viol:
            out.append(f"    {nome:<30} {x}")

    out.append("")
    cont = {}
    for _n, _j, _ja, _t, _ij, v, *_r in linhas:
        cont[v] = cont.get(v, 0) + 1
    out.append("PLACAR: " + " · ".join(f"{k}={v}" for k, v in sorted(cont.items())))
    lac = [n for n, _j, _ja, _t, _ij, v, *_r in linhas if v == "LACUNA"]
    out.append("")
    out.append(f"LACUNAS REAIS (json I-JSON-conforme faz RT, TCF não) = {len(lac)}:")
    for n in lac:
        out.append(f"    - {n}")
    sup = [n for n, _j, _ja, _t, _ij, v, *_r in linhas if v in ("TCF-SUPERIOR", "TCF-ESTRITO")]
    out.append(f"TCF recusa onde o json NÃO é interoperável = {len(sup)}: {', '.join(sup)}")

    # ---- raiz (P4b): eixo separado ----
    out.append("")
    out.append("RAIZ (eixo separado — P4b; o TCF aceita só list[dict] hoje):")
    for nome, v in [("objeto único", {"a": 1}), ("array de escalares", [1, 2]), ("escalar", 42),
                    ("string", "x"), ("null", None), ("array vazio", []), ("[{}]", [{}])]:
        jj, _ = j_rt(v, ensure_ascii=False)
        tt, _ = t_rt(v)
        out.append(f"    {nome:<22} json={jj:<9} tcf={tt[:34]:<36} {'LACUNA(P4b)' if jj == 'RT' and tt != 'RT' else ''}")

    (HERE / "outputs" / "00-resultado.txt").write_bytes(("\n".join(out) + "\n").encode("utf-8"))
    print("\n".join(out))


if __name__ == "__main__":
    main()
