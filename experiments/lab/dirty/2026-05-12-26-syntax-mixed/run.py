"""Roda exp 26 — comparacao enxuta em 1 dataset realista.

Dataset:
  emails-quote-id (combinacao de `'` no nome + digitos no id)

Sintaxes (so 3, as que sobrevivem como universais):
  v4-escape         escape `\\X` para todo char ambiguo
  v4-quote-fixed    aspas para literal com char ambiguo (sem disparo por `'`)
  v4-mixed          escolhe por literal: K=0 raw, K=1 escape, K>=2 quote
"""

import csv
from collections import OrderedDict
from pathlib import Path

from online import processar, reconstroi, TokLit, TokRefPref, TokRefSuf, Token
from syntax_compact_v4_escape import CompactV4EscapeSyntax
from syntax_compact_v4_quote_fixed import CompactV4QuoteFixedSyntax
from syntax_compact_v4_mixed import CompactV4MixedSyntax

BASE = Path(__file__).parent
DATASET = "emails-quote-id"
SINTAXES = [
    CompactV4EscapeSyntax(),
    CompactV4QuoteFixedSyntax(),
    CompactV4MixedSyntax(),
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
        return {"status": "encode_FAIL", "bytes": -1, "tcf": "", "err": str(e)[:80]}

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
    header, linhas = ler_csv(BASE / "data" / f"{DATASET}.csv")
    seen = OrderedDict()
    for s in linhas:
        seen[s] = True
    unicas = list(seen.keys())
    tokens, _ = processar(unicas, min_len=3)
    for s, t in zip(unicas, tokens):
        assert reconstroi(t, unicas) == s
    unidades = unidades_de_tokens(tokens)

    print(f"Dataset: {DATASET}")
    print(f"  N strings: {len(linhas)}")
    print(f"  N unicas: {len(unicas)}")
    print(f"  Unidades de informacao: {unidades}")
    print()

    # Mostrar literais que serao emitidos com seus K (chars ambiguos)
    from syntax_compact_v4_mixed import CompactV4MixedSyntax
    v = CompactV4MixedSyntax()
    qq = v._coletar_quebras(unicas, tokens)
    print("Fragmentos literais (com K = chars ambiguos):")
    print("-" * 70)
    for eid, t_list in enumerate(tokens, start=1):
        s = unicas[eid - 1]
        pos = 0
        for tok in t_list:
            if isinstance(tok, TokLit):
                sl, el = pos, pos + len(tok.text)
                qs = sorted(q for q in qq[eid] if sl < q < el)
                pts = [sl] + qs + [el]
                for i in range(len(pts) - 1):
                    a, b = pts[i], pts[i + 1]
                    frag = s[a:b]
                    k = sum(1 for c in frag if c.isdigit() or c == '*')
                    print(f"  eid={eid} [{a}:{b}] K={k}  {frag!r}")
                pos = el
            else:
                pos += tok.length

    print()
    print("=" * 70)
    print("Comparacao das 3 sintaxes")
    print("-" * 70)

    resultados = {}
    for s in SINTAXES:
        resultados[s.name] = rodar(DATASET, s, linhas, unicas, tokens, header)

    for sn, r in resultados.items():
        if r['status'] == 'OK':
            print(f"\n{sn} ({r['bytes']} bytes):")
        else:
            print(f"\n{sn} ({r['status']}): {r.get('err', '')}")
        if r['tcf']:
            for line in r['tcf'].splitlines():
                print(f"  {line}")

    print()
    print("=" * 70)
    print("Tabela final")
    print("-" * 70)
    print(f"{'sintaxe':<25} {'bytes':>6}  {'razao':>6}")
    validos = [r['bytes'] for r in resultados.values() if r['status'] == 'OK']
    menor = min(validos) if validos else 0
    for sn, r in resultados.items():
        if r['status'] == 'OK':
            print(f"{sn:<25} {r['bytes']:>6}  {r['bytes']/menor:>6.3f}")
        else:
            print(f"{sn:<25} {'X':>6}  {r['status']}")


if __name__ == "__main__":
    main()
