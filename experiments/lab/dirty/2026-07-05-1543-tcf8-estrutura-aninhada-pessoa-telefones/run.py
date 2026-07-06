"""run.py — experimento auto-contido: documento pessoa → 2 tabelas → 2 blocos TCF.8 aninhados.

FOCO: ESTRUTURA (não performance). Estágios: ENTRADA → TRADUÇÃO (JSON→tabelas + árvore) →
TCF.8 ANINHADO (2 blocos um após o outro, envelope auto-descritivo) → DECODE (volta ao JSON).
Usa só `structlib.py` (local) + `tcf` (biblioteca; NÃO toca src). `python run.py` regenera tudo.
"""
from __future__ import annotations
import csv
import io
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(HERE))
from tcf import encode, decode      # noqa: E402
import structlib as S               # noqa: E402

ART = HERE / "artifacts"
ART.mkdir(exist_ok=True)


def write(name, text): (ART / name).write_text(text, encoding="utf-8", newline="\n")


def csv_text(table):
    buf = io.StringIO(); w = csv.writer(buf, lineterminator="\n"); cols = list(table)
    w.writerow(cols)
    for i in range(len(next(iter(table.values()))) if table else 0):
        w.writerow([table[c][i] for c in cols])
    return buf.getvalue()


def main():
    src = json.loads((HERE / "inputs" / "S4-pessoa-telefones.json").read_text(encoding="utf-8"))

    # 01 — ENTRADA
    write("01-entrada-S4-pessoa.json", json.dumps(src, ensure_ascii=False, indent=2) + "\n")

    # 02 — TRADUÇÃO (JSON aninhado → tabelas + árvore auto-descritiva)
    tree, tables = S.to_tables(src)
    write("02-traducao-tabela-pessoa.csv", csv_text(tables["root"]))
    write("02-traducao-tabela-telefones.csv", csv_text(tables["telefones"]))
    arvore = ("# árvore (o que a estrutura precisa saber pra reconstruir)\n"
              "ROOT object\n"
              "  nome       : scalar         -> bloco 'root', coluna 'nome', linha 0\n"
              "  telefones  : array<{tel}>   -> bloco 'telefones', cada linha = 1 objeto {tel}\n\n"
              "esquema (machine): " + json.dumps(tree, ensure_ascii=False) + "\n")
    write("02-traducao-arvore.txt", arvore)

    # 03 — TCF.8: cada tabela vira 1 bloco TCF.8; depois os DOIS aninhados um após o outro
    leaf_pessoa = S.encode_leaf(tables["root"], encode)
    leaf_tel = S.encode_leaf(tables["telefones"], encode)
    write("03-tcf8-bloco-pessoa.tcf.txt", leaf_pessoa if leaf_pessoa.endswith("\n") else leaf_pessoa + "\n")
    write("03-tcf8-bloco-telefones.tcf.txt", leaf_tel if leaf_tel.endswith("\n") else leaf_tel + "\n")
    nested = S.nest(src, encode)
    write("03-tcf8-aninhado.tcf.txt", nested)

    # 04 — DECODE (o caminho de volta: envelope → blocos → JSON) — prova que funciona
    recon = S.unnest(nested, decode)
    ok = recon == src
    D = ["# DECODE — desaninha o envelope, decoda os 2 blocos TCF.8, reconstrói o JSON", "",
         f"reconstruído == entrada ? {'OK' if ok else 'MISMATCH'}", "",
         "--- envelope aninhado (o que foi decodado) ---", nested,
         "--- JSON reconstruído (deve ser idêntico à entrada) ---",
         json.dumps(recon, ensure_ascii=False, indent=2)]
    if not ok:
        D += ["", "!! entrada original:", json.dumps(src, ensure_ascii=False, indent=2)]
    write("04-decode-roundtrip.txt", "\n".join(D) + "\n")

    print("Artefatos em", ART)
    for p in sorted(ART.iterdir()):
        print(f"  {p.name:34s} {p.stat().st_size:6d} B")
    print("\nDECODE:", "reconstrói o JSON de entrada (OK)" if ok else "!! ver 04-decode-roundtrip.txt")
    print("\n--- 03-tcf8-aninhado.tcf.txt (a estrutura, pra inspecionar/redesenhar) ---")
    print(nested)


if __name__ == "__main__":
    main()
