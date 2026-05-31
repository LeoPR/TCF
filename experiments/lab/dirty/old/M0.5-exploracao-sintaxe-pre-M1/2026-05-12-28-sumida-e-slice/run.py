"""Roda exp 28 — Etapa 2 do flow semantico.

Compara v4-quote-fixed (estado da arte) vs v6-sumida (novo, com
parser stateful que omite marcacao quando idx nao existe).

Dataset: emails-quote-id (mesmo do exp 26 e 27).
"""

import csv
from collections import OrderedDict
from pathlib import Path

from online import processar, reconstroi, TokLit, Token
from syntax_compact_v4_quote_fixed import CompactV4QuoteFixedSyntax
from syntax_compact_v6_sumida import CompactV6SumidaSyntax

BASE = Path(__file__).parent
DATASETS = ["emails-quote-id", "stress-substring-meio"]
SINTAXES = [
    CompactV4QuoteFixedSyntax(),
    CompactV6SumidaSyntax(),
]


def ler_csv(path):
    with path.open(encoding="utf-8") as f:
        r = csv.reader(f)
        header = next(r)[0]
        return header, [row[0] for row in r if row]


def unidades_de_tokens(tokens_por_string):
    total = 0
    for tokens in tokens_por_string:
        for tok in tokens:
            total += len(tok.text) if isinstance(tok, TokLit) else 1
    return total


def rodar(nome, sintaxe, linhas, unicas, tokens, header):
    try:
        tcf = sintaxe.encode(linhas, unicas, tokens, header)
    except Exception as e:
        return {"status": "encode_FAIL", "bytes": -1, "tcf": "",
                "err": str(e)[:80]}

    out_dir = BASE / "encoded" / sintaxe.name
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{nome}.tcf").write_text(tcf, encoding="utf-8")

    try:
        decoded = sintaxe.decode(tcf)
    except Exception as e:
        return {"status": "decode_FAIL", "bytes": len(tcf.encode("utf-8")),
                "tcf": tcf, "err": str(e)[:80]}

    if decoded == linhas:
        return {"status": "OK", "bytes": len(tcf.encode("utf-8")), "tcf": tcf}
    for i, (a, b) in enumerate(zip(decoded, linhas)):
        if a != b:
            return {"status": "RT_FAIL", "bytes": len(tcf.encode("utf-8")),
                    "tcf": tcf, "err": f"l{i}: {a!r}!={b!r}"[:80]}
    return {"status": "RT_FAIL_size", "bytes": len(tcf.encode("utf-8")),
            "tcf": tcf, "err": "size mismatch"}


def main():
    for nome in DATASETS:
        header, linhas = ler_csv(BASE / "data" / f"{nome}.csv")
        seen = OrderedDict()
        for s in linhas:
            seen[s] = True
        unicas = list(seen.keys())
        tokens, _ = processar(unicas, min_len=3)
        for s, t in zip(unicas, tokens):
            assert reconstroi(t, unicas) == s
        unidades = unidades_de_tokens(tokens)

        print(f"=== Dataset: {nome} ===")
        print(f"  N strings: {len(linhas)}")
        print(f"  N unicas:  {len(unicas)}")
        print(f"  Unidades:  {unidades}")
        print()

        resultados = {}
        for syn in SINTAXES:
            resultados[syn.name] = rodar(nome, syn, linhas, unicas, tokens, header)

        for sn, r in resultados.items():
            tag = "OK" if r['status'] == 'OK' else r['status']
            print(f"\n--- {sn} [{tag}] {r['bytes']} bytes ---")
            if r['tcf']:
                for line in r['tcf'].splitlines():
                    print(f"  {line}")
            elif r.get('err'):
                print(f"  err: {r['err']}")

        print()
        print("Tabela:")
        bytes_v4 = resultados['compact_v4_quote_fixed']['bytes']
        bytes_v6 = resultados['compact_v6_sumida']['bytes']
        print(f"  v4-q-fix:  {bytes_v4} bytes")
        print(f"  v6-sumida: {bytes_v6} bytes")
        if bytes_v6 > 0 and bytes_v4 > 0:
            diff = bytes_v6 - bytes_v4
            pct = diff / bytes_v4 * 100
            sinal = "+" if diff >= 0 else ""
            print(f"  diff:      {sinal}{diff} ({sinal}{pct:.1f}%)")


if __name__ == "__main__":
    main()
