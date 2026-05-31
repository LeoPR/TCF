"""Teste M1.A' em D1-D4. TCF + decode contra-prova."""

import csv
import sys
from collections import OrderedDict
from pathlib import Path

THIS = Path(__file__).parent
MACRO = THIS.parent
sys.path.insert(0, str(MACRO))

from online import processar, reconstroi, TokLit
from syntax import M1AEscapeEscopoSyntax

DATASETS = ["D1-emails-simples", "D2-emails-quote-id",
             "D3-stress-substring", "D4-caos-mix"]


def ler_csv(path):
    with path.open(encoding="utf-8") as f:
        r = csv.reader(f)
        next(r)
        return [row[0] for row in r if row]


def main():
    syn = M1AEscapeEscopoSyntax()
    print(f"=== Teste M1.A' (escape escopo) em 4 datasets ===\n")
    for nome in DATASETS:
        linhas = ler_csv(MACRO / "data" / f"{nome}.csv")
        seen = OrderedDict()
        for s in linhas:
            seen[s] = True
        unicas = list(seen.keys())
        tokens, _ = processar(unicas, min_len=3)
        for s, t in zip(unicas, tokens):
            assert reconstroi(t, unicas) == s

        try:
            tcf = syn.encode(linhas, unicas, tokens, "")
        except Exception as e:
            print(f"=== {nome} [encode_FAIL] ({e}) ===\n")
            continue

        try:
            decoded = syn.decode(tcf)
        except Exception as e:
            print(f"=== {nome} [decode_FAIL] ({e}) ===\n")
            continue

        rt_ok = decoded == linhas
        n_bytes = len(tcf.encode("utf-8"))

        out = THIS / "encoded"
        out.mkdir(exist_ok=True)
        (out / f"{nome}.tcf").write_text(tcf, encoding="utf-8")
        dec_dir = THIS / "decoded"
        dec_dir.mkdir(exist_ok=True)
        with (dec_dir / f"{nome}.csv").open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["item"])
            for line in decoded:
                w.writerow([line])

        marca = "OK" if rt_ok else "RT_FAIL"
        print(f"=== {nome} [{marca}] {n_bytes} bytes ===")
        print(f"\n--- TCF (encode) ---")
        for line in tcf.splitlines():
            print(f"  {line}")
        print(f"\n--- Decode (contra-prova) ---")
        for i, line in enumerate(decoded, 1):
            orig = linhas[i - 1] if i - 1 < len(linhas) else "(faltando)"
            marca_linha = " " if line == orig else "X"
            print(f"  [{marca_linha}] {line}")
        if rt_ok:
            print(f"\n  -> {len(decoded)} linhas reconstruidas IGUAIS ao input")
        else:
            n_iguais = sum(1 for a, b in zip(decoded, linhas) if a == b)
            print(f"\n  -> {n_iguais}/{len(linhas)} linhas iguais")
        print()


if __name__ == "__main__":
    main()
