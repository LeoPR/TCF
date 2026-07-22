"""Runner do TCF.8H-tabelão: entrada JSON -> denormaliza -> encode multi-col real
(RLE de pai) -> #TCF.8H -> decode -> re-aninha -> volta ao JSON original.

Estrutura (convenção de labs): inputs/ intermediates/ outputs/ com extensão real.
Rodar: python run.py
"""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path

from tabelao_h import (
    denormalize,
    derive_tree,
    encode_h,
    decode_h,
    _dfs_leaf_names,
)
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "src"))
from tcf import encode as tcf_encode  # noqa: E402

HERE = Path(__file__).resolve().parent
INP, INTER, OUT = HERE / "inputs", HERE / "intermediates", HERE / "outputs"
INTER.mkdir(exist_ok=True)
OUT.mkdir(exist_ok=True)


def write_lf(path: Path, text: str) -> None:
    """LF-only, UTF-8 (TCF é LF-only; evita o CRLF do write_text no Windows, que
    inflaria os bytes e quebraria os sizes do header medidos em LF)."""
    path.write_bytes(text.encode("utf-8"))


def denorm_csv(cols: dict) -> str:
    n = len(next(iter(cols.values())))
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(list(cols))
    for i in range(n):
        w.writerow([cols[c][i] for c in cols])
    return buf.getvalue()


def rle_annot(cols: dict, tree: list) -> str:
    out = []
    for name in _dfs_leaf_names(tree):
        body = tcf_encode(cols[name])
        out.append(f"### coluna '{name}'  (tcf.encode do tabelão)")
        out.append(body if body.endswith("\n") else body + "\n")
    return "\n".join(out)


def byte_ladder(records: list) -> str:
    base = encode_h(records, last_omits=False, omit_closes=False)
    lo = encode_h(records, last_omits=True, omit_closes=False)
    full = encode_h(records, last_omits=True, omit_closes=True)
    m = lambda b: b.split("\n", 1)[0][len("#TCF.8H "):]  # noqa: E731
    return (
        f"base (todos sizes, closes explícitos)   meta={m(base)!r}  total={len(base.encode())} B\n"
        f"+última-folha-sem-size                   meta={m(lo)!r}  total={len(lo.encode())} B\n"
        f"+omit-closes (CONSAGRADO, default)       meta={m(full)!r}  total={len(full.encode())} B\n"
    )


def process(tag: str, src_name: str, canon_name: str, tcf_name: str, rt_name: str, log: list):
    records = json.loads((INP / src_name).read_text(encoding="utf-8"))
    tree = derive_tree(records)
    cols = denormalize(records, tree)

    # intermediários VISÍVEIS: a tabela denormalizada (o "tabelão") + RLE por coluna
    write_lf(INTER / f"{tag}-denormalizado.csv", denorm_csv(cols))
    write_lf(INTER / f"{tag}-rle-por-coluna.txt", rle_annot(cols, tree))
    canon = json.dumps(records, ensure_ascii=False, indent=2) + "\n"
    write_lf(INTER / canon_name, canon)

    # saída .tcf real + roundtrip .json diffável
    blob = encode_h(records)
    write_lf(OUT / tcf_name, blob)
    back = decode_h(blob)
    rt = json.dumps(back, ensure_ascii=False, indent=2) + "\n"
    write_lf(OUT / rt_name, rt)

    ok = back == records
    identical = rt == canon
    assert ok and identical, f"RT falhou em {tag}"
    log.append(f"== {tag} ({src_name}) ==")
    log.append(f"árvore: {tree}")
    log.append(f"tabelão: {len(next(iter(cols.values())))} linhas x {len(cols)} colunas")
    log.append(f"decode(encode)==original: {ok}")
    log.append(f"outputs/{rt_name} BYTE-IDÊNTICO a intermediates/{canon_name}: {identical}")
    log.append(f"wire outputs/{tcf_name}: {(OUT / tcf_name).stat().st_size} B  "
               f"(JSON original {len((INP / src_name).read_text(encoding='utf-8').encode())} B)")
    log.append("")
    return records


def main() -> None:
    log = ["CONTRA-PROVA — TCF.8H tabelão (denormaliza + RLE de pai + re-aninha)", ""]

    r1 = process("01-telefones", "01-pessoas-telefones.json",
                 "03-telefones-canonico.json", "01-telefones.tcf",
                 "05-telefones.roundtrip.json", log)
    r2 = process("02-pedidos", "02-pessoas-pedidos.json",
                 "04-pedidos-canonico.json", "02-pedidos.tcf",
                 "06-pedidos.roundtrip.json", log)

    # escada de bytes do header (como o lab 1830 mostrou)
    write_lf(OUT / "07-header-byte-ladder.txt",
             "### 01-pessoas-telefones\n" + byte_ladder(r1) +
             "\n### 02-pessoas-pedidos\n" + byte_ladder(r2))

    write_lf(OUT / "08-contraprova.txt", "\n".join(log) + "\n")

    print("tcf8h-tabelão: all checks PASS")
    print("\n".join(log))
    print("--- wire 01-telefones.tcf ---")
    print((OUT / "01-telefones.tcf").read_text(encoding="utf-8"))
    print("--- wire 02-pedidos.tcf ---")
    print((OUT / "02-pedidos.tcf").read_text(encoding="utf-8"))
    print("--- header byte ladder ---")
    print((OUT / "07-header-byte-ladder.txt").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
