"""Roda exp 24 — testa resistencia a ambiguidades.

4 datasets com gradiente de ambiguidade:
  - emails-com-id: digitos no literal
  - nomes-com-aspas: `'` no literal
  - codigos-com-arroba: `@` e `*` no literal
  - caos-mix: tudo (`'`, `*`, `@`, `[`, `]`, digitos)

4 sintaxes:
  - compact_v2 (aspas sempre): quebra com `'` no literal
  - compact_v3 (sem aspas): quebra com digito ou `*` no literal
  - compact_v4_escape (escape `\\`): cobre tudo, +1 byte/char ambiguo
  - compact_v4_quote (aspas condicionais): cobre tudo, +2 bytes/literal ambiguo

Tabela mostra bytes; sintaxes que quebram (roundtrip FAIL ou
exception) sao marcadas com 'X'.
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

BASE = Path(__file__).parent
DATASETS = ["emails-com-id", "nomes-com-aspas", "codigos-com-arroba", "caos-mix"]
SINTAXES = [
    CompactV2Syntax(),
    CompactV3Syntax(),
    CompactV4EscapeSyntax(),
    CompactV4QuoteSyntax(),
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
    """Tenta encode + decode. Retorna status e bytes."""
    try:
        tcf = sintaxe.encode(linhas, unicas, tokens, header)
    except Exception as e:
        return {"status": "encode_FAIL", "bytes": -1, "tcf": "", "err": str(e)[:60]}

    out_dir = BASE / "encoded" / sintaxe.name
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{nome}.tcf").write_text(tcf, encoding="utf-8")

    try:
        decoded = sintaxe.decode(tcf)
    except Exception as e:
        return {"status": "decode_FAIL", "bytes": len(tcf.encode("utf-8")),
                "tcf": tcf, "err": str(e)[:60]}

    if decoded == linhas:
        return {"status": "OK", "bytes": len(tcf.encode("utf-8")), "tcf": tcf}
    else:
        # primeiro diff
        for i, (a, b) in enumerate(zip(decoded, linhas)):
            if a != b:
                return {"status": "RT_FAIL",
                        "bytes": len(tcf.encode("utf-8")),
                        "tcf": tcf,
                        "err": f"linha {i}: {a!r} != {b!r}"[:60]}
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
            assert reconstroi(t, unicas) == s, f"online quebrou em {nome}"
        unid = unidades_de_tokens(tokens)
        resultados[nome] = {"unidades": unid, "n_unicas": len(unicas),
                              "n_linhas": len(linhas), "sintaxes": {}}
        for syn in SINTAXES:
            resultados[nome]["sintaxes"][syn.name] = rodar(
                nome, syn, linhas, unicas, tokens, header)

    syn_names = [s.name for s in SINTAXES]

    print("=" * 110)
    print("Tabela 1 - Bytes por sintaxe (X = sintaxe falhou neste dataset)")
    print("-" * 110)
    print(f"{'dataset':<22} {'N':>3} {'unid':>5}  " +
          "".join(f"{n:>20}" for n in syn_names))
    for nome in DATASETS:
        r = resultados[nome]
        row = f"{nome:<22} {r['n_unicas']:>3} {r['unidades']:>5}  "
        for sn in syn_names:
            sr = r['sintaxes'][sn]
            if sr['status'] != "OK":
                cell = f"X ({sr['status'][:8]})"
            else:
                cell = f"{sr['bytes']}"
            row += f"{cell:>20}"
        print(row)

    # Razao vs melhor sintaxe que funcionou para cada dataset
    print()
    print("=" * 110)
    print("Tabela 2 - Razao vs MENOR bytes do dataset (entre as que funcionaram)")
    print("-" * 110)
    print(f"{'dataset':<22}  " + "".join(f"{n:>20}" for n in syn_names))
    for nome in DATASETS:
        r = resultados[nome]
        validos = [sr['bytes'] for sr in r['sintaxes'].values()
                    if sr['status'] == 'OK']
        if not validos:
            row = f"{nome:<22}  " + "(nenhuma funcionou)"
            print(row)
            continue
        menor = min(validos)
        row = f"{nome:<22}  "
        for sn in syn_names:
            sr = r['sintaxes'][sn]
            if sr['status'] == 'OK':
                row += f"{sr['bytes']/menor:>20.3f}"
            else:
                row += f"{'X':>20}"
        print(row)

    # Status por dataset/sintaxe
    print()
    print("=" * 110)
    print("Tabela 3 - Status detalhado")
    print("-" * 110)
    for nome in DATASETS:
        print(f"\n{nome}:")
        for sn in syn_names:
            sr = resultados[nome]['sintaxes'][sn]
            if sr['status'] == 'OK':
                print(f"  {sn:<22}  OK  ({sr['bytes']} bytes)")
            else:
                print(f"  {sn:<22}  {sr['status']}: {sr.get('err', '')}")

    # TCFs lado a lado para inspecao do caos-mix
    print()
    print("=" * 110)
    print("caos-mix lado a lado (sintaxes que funcionaram)")
    print("=" * 110)
    for sn in syn_names:
        sr = resultados["caos-mix"]["sintaxes"][sn]
        print(f"\n--- {sn} (status={sr['status']}, {sr['bytes']} bytes) ---")
        if sr['tcf']:
            print(sr['tcf'], end="")


if __name__ == "__main__":
    main()
