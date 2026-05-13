"""Roda exp 25 — 6 sintaxes nos 4 datasets ambiguos do exp 24.

Sintaxes:
  - compact_v2 (referencia exp 22)
  - compact_v3 (referencia exp 23)
  - compact_v4_escape (exp 24)
  - compact_v4_quote (exp 24, com bug)
  - compact_v4_quote_fixed (NOVO — fix do bug)
  - compact_v5_adapt_escape (NOVO — substituicao + escape)
  - compact_v5_adapt_quote (NOVO — substituicao + aspas)

Datasets:
  - emails-com-id      (digitos em literais)
  - nomes-com-aspas    (`'` em literais)
  - codigos-com-arroba (`*`, digitos)
  - caos-mix           (varios)
"""

import csv
from collections import OrderedDict
from pathlib import Path

from online import processar, reconstroi, TokLit, Token
from syntax_base import Syntax
from syntax_compact_v2 import CompactV2Syntax
from syntax_compact_v3 import CompactV3Syntax
from syntax_compact_v4_escape import CompactV4EscapeSyntax
from syntax_compact_v4_quote import CompactV4QuoteSyntax
from syntax_compact_v4_quote_fixed import CompactV4QuoteFixedSyntax
from syntax_compact_v5_adapt_escape import CompactV5AdaptEscapeSyntax
from syntax_compact_v5_adapt_quote import CompactV5AdaptQuoteSyntax

BASE = Path(__file__).parent
DATASETS = ["emails-com-id", "nomes-com-aspas", "codigos-com-arroba", "caos-mix"]
SINTAXES = [
    CompactV2Syntax(),
    CompactV3Syntax(),
    CompactV4EscapeSyntax(),
    CompactV4QuoteSyntax(),
    CompactV4QuoteFixedSyntax(),
    CompactV5AdaptEscapeSyntax(),
    CompactV5AdaptQuoteSyntax(),
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
        return {"status": "encode_FAIL", "bytes": -1, "tcf": "", "err": str(e)[:70]}

    out_dir = BASE / "encoded" / sintaxe.name
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{nome}.tcf").write_text(tcf, encoding="utf-8")

    try:
        decoded = sintaxe.decode(tcf)
    except Exception as e:
        return {"status": "decode_FAIL", "bytes": len(tcf.encode("utf-8")),
                "tcf": tcf, "err": str(e)[:70]}

    if decoded == linhas:
        return {"status": "OK", "bytes": len(tcf.encode("utf-8")), "tcf": tcf}
    else:
        for i, (a, b) in enumerate(zip(decoded, linhas)):
            if a != b:
                return {"status": "RT_FAIL", "bytes": len(tcf.encode("utf-8")),
                        "tcf": tcf,
                        "err": f"l{i}: {a!r}!={b!r}"[:70]}
        return {"status": "RT_FAIL_size", "bytes": len(tcf.encode("utf-8")),
                "tcf": tcf, "err": "size mismatch"}


def main():
    print(f"Rodando {len(DATASETS)} datasets x {len(SINTAXES)} sintaxes...")
    print()
    resultados = {}
    for nome in DATASETS:
        header, linhas = ler_csv(BASE / "data" / f"{nome}.csv")
        seen = OrderedDict()
        for s in linhas:
            seen[s] = True
        unicas = list(seen.keys())
        tokens, _ = processar(unicas, min_len=3)
        for s, t in zip(unicas, tokens):
            assert reconstroi(t, unicas) == s
        unid = unidades_de_tokens(tokens)
        resultados[nome] = {"unidades": unid, "n_unicas": len(unicas),
                              "sintaxes": {}}
        for syn in SINTAXES:
            resultados[nome]["sintaxes"][syn.name] = rodar(
                nome, syn, linhas, unicas, tokens, header)

    syn_names = [s.name for s in SINTAXES]

    print("=" * 130)
    print("Tabela 1 - Bytes (X = sintaxe falhou)")
    print("-" * 130)
    abrev = {
        "compact_v2": "v2",
        "compact_v3": "v3",
        "compact_v4_escape": "v4-esc",
        "compact_v4_quote": "v4-q",
        "compact_v4_quote_fixed": "v4-q-fix",
        "compact_v5_adapt_escape": "v5-a-esc",
        "compact_v5_adapt_quote": "v5-a-q",
    }
    print(f"{'dataset':<22} {'N':>3} {'unid':>5}  " +
          "".join(f"{abrev[n]:>10}" for n in syn_names))
    for nome in DATASETS:
        r = resultados[nome]
        row = f"{nome:<22} {r['n_unicas']:>3} {r['unidades']:>5}  "
        for sn in syn_names:
            sr = r['sintaxes'][sn]
            cell = f"{sr['bytes']}" if sr['status'] == "OK" else "X"
            row += f"{cell:>10}"
        print(row)

    print()
    print("=" * 130)
    print("Tabela 2 - Razao vs MENOR bytes (entre as que funcionaram)")
    print("-" * 130)
    print(f"{'dataset':<22}  " + "".join(f"{abrev[n]:>10}" for n in syn_names))
    for nome in DATASETS:
        r = resultados[nome]
        validos = [sr['bytes'] for sr in r['sintaxes'].values()
                    if sr['status'] == 'OK']
        if not validos:
            print(f"{nome:<22}  (nenhuma funcionou)")
            continue
        menor = min(validos)
        row = f"{nome:<22}  "
        for sn in syn_names:
            sr = r['sintaxes'][sn]
            if sr['status'] == 'OK':
                row += f"{sr['bytes']/menor:>10.3f}"
            else:
                row += f"{'X':>10}"
        print(row)

    print()
    print("=" * 130)
    print("Status / TCF lado a lado para cada dataset")
    print("=" * 130)
    for nome in DATASETS:
        print(f"\n--- {nome} ---")
        for sn in syn_names:
            sr = resultados[nome]["sintaxes"][sn]
            tag = abrev[sn]
            if sr['status'] == 'OK':
                print(f"\n  [{tag}] {sr['bytes']} bytes:")
                for line in sr['tcf'].splitlines():
                    print(f"    {line}")
            else:
                print(f"  [{tag}] {sr['status']}: {sr.get('err', '')}")

    falhas = []
    for nome in DATASETS:
        for sn, r in resultados[nome]["sintaxes"].items():
            if r["status"] != "OK":
                falhas.append(f"{nome}/{sn}")


if __name__ == "__main__":
    main()
