"""Especiais (null/NaN/Inf/ausencia) — FORMATOS LADO A LADO, com dados realistas.

Refeito a pedido do owner (2026-07-13): os labs anteriores provaram semantica com
fixtures pobres; este mostra os FORMATOS com clareza para a decisao. Para cada
entrada realista: (1) a entrada visivel, (2) o fluxo semantico interno (kind por
valor), (3) o ARQUIVO de saida em cada formato candidato, (4) o roundtrip explicito
de volta ao original. Sem veredito: material de decisao.

Entradas:
  01-clientes-api.json      JSON PADRAO aninhado (null, campo ausente, {} vazio,
                            arrays ragged) — JSON padrao nao carrega NaN.
  02-telemetria-jsonlike    export Python real (json.dumps allow_nan=True emite
                            NaN/Infinity) — gramatica DECLARADA JSON+constantes.
  03-sensores (tabular)     colunas TIPADAS sem hierarquia — o problema null/NaN/
                            Inf independe de hierarquia (pedido do owner).

Formatos por entrada:
  hierarquicas : A  (per-instance, tag por ocorrencia — wire do lab 1835)
                 RH (regular: schema por coluna + stream def+kind + payload via
                     tcf.encode REAL do core — generaliza HK/lab 1921 + lab 1955)
  tabular      : HOJE (stringify + tcf.encode real — o comportamento atual; a
                     PERDA aparece no roundtrip, honesta)
                 FK  (kind-channel por coluna + payload tcf.encode real — mesmo
                     alfabeto de kinds do RH, SEM os cuts estruturais)

Alfabeto de marcas (1 char/ocorrencia — candidato em estudo, nao gramatica final):
  s=string  i=integer  d=decimal-finito  t=true  f=false
  z=null    q=NaN      p=+Inf            m=-Inf
  a=array-presente     0..9=cut@i (a cadeia quebrou no elemento i)   [so' hierarquico]

Zero mudanca em src/tcf (uso read-only de encode/decode p/ payloads).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_D = HERE.parents[0]
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(_D / "2026-07-13-dataseth-json-bridge"))
sys.path.insert(0, str(_D / "2026-07-13-1835-dataseth-special-scalars"))
sys.path.insert(0, str(_D / "2026-07-13-1955-dataseth-regular-def-levels"))

from tcf import decode as tcf_decode, encode as tcf_encode  # noqa: E402  (core REAL)
from dataset_h import DatasetH, HArray, HObject, HScalar  # noqa: E402
from model_ext import from_jsonlike, from_python_ext, semantic_key  # noqa: E402
from wire_ac import decode as decode_a, encode as encode_a  # noqa: E402
from regular import decode_r2, derive_schema, encode_r2, leaf_paths  # noqa: E402

INP = HERE / "inputs"          # entradas com extensao real (.json/.csv)
INTER = HERE / "intermediates"  # fluxo interno/semantica/canonicos
OUT = HERE / "outputs"          # saidas com extensao real (.tcf/.json) + contraprova
INTER.mkdir(exist_ok=True)
OUT.mkdir(exist_ok=True)

MARK2CHAR = {
    "null": "z", "nan": "q", "pos_inf": "p", "neg_inf": "m",
    "false": "f", "true": "t", "str": "s", "int": "i", "num": "d", "present": "a",
}
CHAR2MARK = {v: k for k, v in MARK2CHAR.items()}


def mark_char(mark: str) -> str:
    if mark.startswith("cut@"):
        return mark[4:]
    return MARK2CHAR[mark]


def char_mark(ch: str) -> str:
    if ch.isdigit():
        return f"cut@{ch}"
    return CHAR2MARK[ch]


def to_python_ext(node):
    """Adaptador de SAIDA: DatasetH -> primitivas Python (kinds -> floats especiais)."""
    if isinstance(node, HScalar):
        k = node.type_name
        if k == "nan":
            return float("nan")
        if k == "pos_inf":
            return float("inf")
        if k == "neg_inf":
            return float("-inf")
        return node.value
    if isinstance(node, HArray):
        return [to_python_ext(i) for i in node.items]
    return {n: to_python_ext(c) for n, c in node.fields}


def dumps(py) -> str:
    return json.dumps(py, ensure_ascii=False, indent=2)  # allow_nan default: emite NaN/Infinity


# ------------------------------------------------------------ formato RH (arquivo)

def rh_write(name: str, rows: list, out_path: Path) -> None:
    schema = derive_schema(rows)
    cols = encode_r2(rows, schema)
    buf = bytearray()
    buf += f"#PROTO.RH {name}\nR {len(rows)}\n".encode()
    for path, kind in leaf_paths(schema):
        dotted = ".".join(path) + ("[]" if kind == "array" else "")
        col = cols[path]
        chars = "".join(mark_char(m) for m in col["marks"])
        buf += f"{'A' if kind == 'array' else 'C'} {dotted} {chars}\n".encode()
        if kind == "array":
            buf += f"n {dotted} {','.join(col['counts'])}\n".encode()
            echars = "".join(MARK2CHAR[k] for k, _ in col["payloads"])
            buf += f"E {dotted} {echars}\n".encode()
            texts = [pay for k, pay in col["payloads"] if k in ("str", "int", "num")]
        else:
            texts = list(col["payloads"])
        if texts:
            blob = tcf_encode(texts).encode()
            buf += f"P {dotted} {len(blob)}\n".encode()
            buf += blob + b"\n"
    out_path.write_bytes(bytes(buf))


def rh_read(path: Path) -> list:
    data = path.read_bytes()
    lines_iter = _byte_lines(data)
    magic = next(lines_iter)[0]
    assert magic.startswith(b"#PROTO.RH")
    n_rows = int(next(lines_iter)[0].split()[1])
    schema: dict = {}
    cols: dict = {}
    order: list = []
    pend: dict = {}
    for line, pos in lines_iter:
        tagpart = line.split(b" ", 2)
        tag = tagpart[0].decode()
        if tag in ("C", "A"):
            dotted = tagpart[1].decode()
            chars = tagpart[2].decode() if len(tagpart) > 2 else ""
            is_arr = dotted.endswith("[]")
            names = (dotted[:-2] if is_arr else dotted).split(".")
            _schema_add(schema, names, "array" if is_arr else "leaf")
            p = tuple(names)
            order.append(p)
            cols[p] = {"marks": [char_mark(c) for c in chars], "payloads": [], "counts": []}
            pend[dotted] = p
        elif tag == "n":
            p = pend[tagpart[1].decode()]
            raw = tagpart[2].decode().strip() if len(tagpart) > 2 else ""
            cols[p]["counts"] = raw.split(",") if raw else []
        elif tag == "E":
            p = pend[tagpart[1].decode()]
            chars = tagpart[2].decode() if len(tagpart) > 2 else ""
            cols[p]["_ekinds"] = [CHAR2MARK[c] for c in chars]
        elif tag == "P":
            p = pend[tagpart[1].decode()]
            blen = int(tagpart[2])
            blob = data[pos : pos + blen]
            cols[p]["_texts"] = tcf_decode(blob.decode())
            lines_iter = _byte_lines(data, pos + blen + 1)  # pula blob + \n
    # reconstruir payloads na forma que decode_r2 espera
    for p, col in cols.items():
        texts = col.pop("_texts", [])
        ekinds = col.pop("_ekinds", None)
        if ekinds is not None:  # array: tuplas (kind, texto|None)
            it = iter(texts)
            col["payloads"] = [
                (k, next(it) if k in ("str", "int", "num") else None) for k in ekinds
            ]
        else:
            col["payloads"] = texts
    return decode_r2(cols, schema, n_rows)


def _schema_add(schema: dict, names: list[str], kind: str) -> None:
    cur = schema
    for name in names[:-1]:
        cur = cur.setdefault(name, {"kind": "object", "fields": {}})["fields"]
    cur.setdefault(names[-1], {"kind": kind})


def _byte_lines(data: bytes, start: int = 0):
    pos = start
    while pos < len(data):
        nl = data.find(b"\n", pos)
        if nl == -1:
            break
        yield data[pos:nl], nl + 1
        pos = nl + 1


# ------------------------------------------------------------ formato FK (tabular)

def fk_write(name: str, table: dict, out_path: Path) -> None:
    n = len(next(iter(table.values())))
    buf = bytearray()
    buf += f"#PROTO.FK {name}\nR {n}\n".encode()
    for cname, cells in table.items():
        marks, texts = [], []
        for cell in cells:
            node = from_python_ext(cell).root
            k = node.type_name
            if k == "boolean":
                marks.append("t" if node.value else "f")
            elif k == "string":
                marks.append("s"); texts.append(node.value)
            elif k == "integer":
                marks.append("i"); texts.append(str(node.value))
            elif k == "number":
                marks.append("d"); texts.append(repr(node.value))
            else:
                marks.append(MARK2CHAR[k])  # z q p m
        buf += f"C {cname} {''.join(marks)}\n".encode()
        if texts:
            blob = tcf_encode(texts).encode()
            buf += f"P {cname} {len(blob)}\n".encode()
            buf += blob + b"\n"
    out_path.write_bytes(bytes(buf))


def fk_read(path: Path) -> dict:
    data = path.read_bytes()
    it = _byte_lines(data)
    assert next(it)[0].startswith(b"#PROTO.FK")
    next(it)  # R
    table: dict = {}
    pend: str | None = None
    for line, pos in it:
        parts = line.split(b" ", 2)
        tag = parts[0].decode()
        if tag == "C":
            cname = parts[1].decode()
            chars = parts[2].decode() if len(parts) > 2 else ""
            table[cname] = {"marks": chars, "texts": []}
            pend = cname
        elif tag == "P":
            blen = int(parts[2])
            table[pend]["texts"] = tcf_decode(data[pos : pos + blen].decode())
            it = _byte_lines(data, pos + blen + 1)
    out: dict = {}
    for cname, col in table.items():
        cells, ti = [], iter(col["texts"])
        for ch in col["marks"]:
            if ch == "s":
                cells.append(next(ti))
            elif ch == "i":
                cells.append(int(next(ti)))
            elif ch == "d":
                cells.append(float(next(ti)))
            elif ch == "t":
                cells.append(True)
            elif ch == "f":
                cells.append(False)
            elif ch == "z":
                cells.append(None)
            elif ch == "q":
                cells.append(float("nan"))
            elif ch == "p":
                cells.append(float("inf"))
            elif ch == "m":
                cells.append(float("-inf"))
        out[cname] = cells
    return out


# ------------------------------------------------------------ fluxo semantico

def render_flow(title: str, rows: list) -> str:
    schema = derive_schema(rows)
    cols = encode_r2(rows, schema)
    out = [f"### {title} — kind por valor (linhas -> colunas-de-folha)"]
    for path, kind in leaf_paths(schema):
        dotted = ".".join(path) + ("[]" if kind == "array" else "")
        col = cols[path]
        chars = "".join(mark_char(m) for m in col["marks"])
        out.append(f"  {dotted:24s} {chars}")
        if kind == "array" and col["counts"]:
            out.append(f"  {'':24s} counts={','.join(col['counts'])}")
        pays = col["payloads"]
        if pays:
            shown = [p if not isinstance(p, tuple) else (p[1] if p[1] is not None else f"<{p[0]}>") for p in pays]
            out.append(f"  {'':24s} payloads={shown[:6]}{'...' if len(shown) > 6 else ''}")
    return "\n".join(out)


# ------------------------------------------------------------ main

SENSORES = {  # origem TIPADA (Python/driver de sensor) — tabular SEM hierarquia
    "estacao":       ["PA-001", "PA-002", "PA-003", "PA-004", "PA-005", "PA-006"],
    "temperatura_c": [21.4, float("nan"), 24.0, 19.8, float("nan"), 22.7],
    "variacao_pct":  [1.8, float("nan"), float("inf"), -2.4, 0.0, -0.0],
    "amostras":      [90, 0, 90, 88, 0, 91],
    "obs":           ["", "sensor em manutencao", "janela anterior zerada",
                      "None", None, "nan"],
}
# obs realista: linha 3 tem a STRING "None" (upstream ja' stringificou) e a linha 4
# tem null de verdade; linha 5 tem a STRING "nan" (export anterior). E' o cenario
# classico de dupla-stringificacao que o formato precisa distinguir.


def main() -> None:
    rt_log = []

    # ============ ENTRADA 1: clientes (JSON padrao) ============
    src1 = (INP / "01-clientes-api.json").read_text(encoding="utf-8")
    doc1 = DatasetH.from_json(src1)                # adaptador JSON padrao (lab-ponte)
    rows1 = [r for r in doc1.root.items]           # registros

    # ============ ENTRADA 2: telemetria (JSON-like declarado) ============
    src2 = (INP / "02-telemetria-jsonlike.json").read_text(encoding="utf-8")
    doc2 = from_jsonlike(src2)
    rows2 = [r for r in doc2.root.items]

    # ============ ENTRADA 3: sensores tabular ============
    # Origem TIPADA (SENSORES, driver/Arrow) + o export stringly em inputs/03 (CSV).
    # O CSV E' a prova da colisao: linhas 4 e 5 tem obs='None' identico vindo de
    # verdades diferentes (string literal vs null exportado).
    import csv as _csv
    with (INP / "03-sensores-tabular.csv").open(encoding="utf-8", newline="") as f:
        r = _csv.reader(f)
        header = next(r)
        csv_cols = {h: [] for h in header}
        for rowv in r:
            for h, v in zip(header, rowv):
                csv_cols[h].append(v)
    # consistencia: o CSV e' exatamente o str() da origem tipada
    assert csv_cols == {c: [str(v) for v in cells] for c, cells in SENSORES.items()}, \
        "inputs/03 divergiu da origem tipada"
    tbl_render = ["estacao | temperatura_c | variacao_pct | amostras | obs", "---"]
    for i in range(6):
        tbl_render.append(" | ".join(repr(SENSORES[c][i]) for c in SENSORES))
    (INTER / "01-sensores-origem-tipada.txt").write_text(
        "origem TIPADA (driver/Arrow) — o CSV em inputs/03 e' o export str() dela.\n"
        "reparar: obs linha3='None' (string) vs linha4=None (null) — NO CSV os dois viram 'None';\n"
        "obs linha5='nan' (string) vs temperatura linha1=nan (float); variacao -0.0 vs 0.0.\n\n"
        + "\n".join(tbl_render) + "\n",
        encoding="utf-8",
    )

    # ============ FLUXO SEMANTICO ============
    flow = [render_flow("clientes (JSON padrao)", rows1), "",
            render_flow("telemetria (JSON-like declarado)", rows2), "",
            "### sensores tabular — kind por celula (mesmo alfabeto, SEM cuts)"]
    for cname, cells in SENSORES.items():
        chars = []
        for cell in cells:
            node = from_python_ext(cell).root
            k = node.type_name
            chars.append("t" if (k == "boolean" and node.value) else
                         "f" if k == "boolean" else
                         {"string": "s", "integer": "i", "number": "d"}.get(k) or MARK2CHAR[k])
        flow.append(f"  {cname:16s} {''.join(chars)}")
    (INTER / "02-fluxo-semantico.txt").write_text("\n".join(flow) + "\n", encoding="utf-8")

    # canonicos (p/ diff byte-a-byte com os roundtrips em outputs/)
    (INTER / "03-clientes-canonico.json").write_text(
        dumps(to_python_ext(doc1.root)) + "\n", encoding="utf-8")
    (INTER / "04-telemetria-canonico.json").write_text(
        dumps(to_python_ext(doc2.root)) + "\n", encoding="utf-8")

    # ============ SAIDAS + ROUNDTRIP ============
    def rt_hier(tag: str, doc: DatasetH, rows: list, na: str, nrh: str, nrt: str, canon: str) -> None:
        # A per-instance
        pa = OUT / na
        pa.write_text(encode_a(doc, "A"), encoding="utf-8")
        back = decode_a(pa.read_text(encoding="utf-8"), "A")
        ok_a = semantic_key(back.root) == semantic_key(doc.root)
        # RH regular
        pr = OUT / nrh
        rh_write(tag, rows, pr)
        rows_back = rh_read(pr)
        ok_rh = [semantic_key(r) for r in rows_back] == [semantic_key(r) for r in rows]
        assert ok_a and ok_rh, f"RT falhou em {tag}"
        # roundtrip como ARQUIVO .json — diffavel contra o canonico em intermediates/
        deco = dumps([to_python_ext(r) for r in rows_back]) + "\n"
        (OUT / nrt).write_text(deco, encoding="utf-8")
        canon_txt = (INTER / canon).read_text(encoding="utf-8")
        identical = deco == canon_txt
        assert identical
        rt_log.append(f"== {tag} ==")
        rt_log.append(f"A  per-instance : semantico identico = {ok_a} ({na}, {pa.stat().st_size} B)")
        rt_log.append(f"RH regular      : semantico identico = {ok_rh} ({nrh}, {pr.stat().st_size} B)")
        rt_log.append(f"roundtrip       : outputs/{nrt} BYTE-IDENTICO a intermediates/{canon} = {identical}")
        rt_log.append("")

    rt_hier("clientes", doc1, rows1,
            "01-clientes.A.tcf", "02-clientes.RH.tcf",
            "07-clientes.roundtrip.json", "03-clientes-canonico.json")
    rt_hier("telemetria", doc2, rows2,
            "03-telemetria.A.tcf", "04-telemetria.RH.tcf",
            "08-telemetria.roundtrip.json", "04-telemetria-canonico.json")

    # tabular HOJE (o CSV stringly de inputs/03 + tcf real) — a perda aparece
    ph = OUT / "05-sensores.HOJE.tcf"
    ph.write_text(tcf_encode(csv_cols), encoding="utf-8")
    hoje_back = tcf_decode(ph.read_text(encoding="utf-8"))
    losses = []
    if hoje_back["obs"][3] == hoje_back["obs"][4]:
        losses.append("obs: 'None'(string, l3) e None(null, l4) viraram AMBOS 'None' — indistinguiveis")
    if hoje_back["temperatura_c"][1] == "nan" and SENSORES["obs"][5] == "nan":
        losses.append("temperatura nan(float) e obs 'nan'(string) soletram IGUAL apos str() — tipo perdido")
    losses.append("todos os numeros viraram string ('21.4' etc.) — tipo perdido em TODA celula")
    rt_log.append("== sensores tabular — HOJE (CSV stringly de inputs/03 + tcf.encode real) ==")
    rt_log.append(f"blob: {ph.name} ({ph.stat().st_size} B); RT das STRINGS do CSV = {hoje_back == csv_cols}")
    rt_log.append("PERDAS vs origem tipada (por isso RT tipado = False):")
    rt_log += [f"  - {l}" for l in losses]
    rt_log.append("")

    # tabular FK (kind-channel + tcf real) — lossless
    pf = OUT / "06-sensores.FK.tcf"
    fk_write("sensores", SENSORES, pf)
    fk_back = fk_read(pf)
    ok_fk = all(
        [semantic_key(from_python_ext(v).root) for v in fk_back[c]]
        == [semantic_key(from_python_ext(v).root) for v in SENSORES[c]]
        for c in SENSORES
    )
    assert ok_fk, "RT FK falhou"
    rt_lines = ["linha | original -> decodificado (tipado)"]
    for i in range(6):
        o = {c: SENSORES[c][i] for c in SENSORES}
        d = {c: fk_back[c][i] for c in SENSORES}
        rt_lines.append(f"l{i}: {o!r}")
        rt_lines.append(f"  -> {d!r}")
    (OUT / "09-sensores.FK.roundtrip.txt").write_text("\n".join(rt_lines) + "\n", encoding="utf-8")
    rt_log.append("== sensores tabular — FK (kind-channel + payload tcf.encode real) ==")
    rt_log.append(f"arquivo: {pf.name} ({pf.stat().st_size} B); RT TIPADO semantico = {ok_fk}")
    rt_log.append("linha a linha em outputs/09-sensores.FK.roundtrip.txt")
    (OUT / "10-roundtrip-contraprova.txt").write_text("\n".join(rt_log) + "\n", encoding="utf-8")

    # ============ BYTES ============
    sizes = ["entrada | formato | arquivo | bytes"]
    for f, label, nm in [("01-clientes.A.tcf", "clientes", "A per-instance"),
                         ("02-clientes.RH.tcf", "clientes", "RH regular"),
                         ("03-telemetria.A.tcf", "telemetria", "A per-instance"),
                         ("04-telemetria.RH.tcf", "telemetria", "RH regular")]:
        sizes.append(f"{label} | {nm} | outputs/{f} | {(OUT / f).stat().st_size}")
    sizes.append(f"clientes | JSON original | inputs/01-clientes-api.json | {len(src1.encode())}")
    sizes.append(f"telemetria | JSON-like original | inputs/02-telemetria-jsonlike.json | {len(src2.encode())}")
    sizes.append(f"sensores | CSV original | inputs/03-sensores-tabular.csv | {(INP / '03-sensores-tabular.csv').stat().st_size}")
    sizes.append(f"sensores | HOJE stringify | outputs/{ph.name} | {ph.stat().st_size}")
    sizes.append(f"sensores | FK kind-channel | outputs/{pf.name} | {pf.stat().st_size}")
    (OUT / "11-bytes.txt").write_text("\n".join(sizes) + "\n", encoding="utf-8")

    print("especiais-formatos-lado-a-lado: all checks PASS")
    print("\n".join(sizes))


if __name__ == "__main__":
    main()
