"""Roda exp 23 — 5 sintaxes em D2-mini + D2-completo.

Foco: comparacao detalhada de 5 sintaxes nos 2 datasets menores
para iterar rapido sobre variacoes da sintaxe.

Sintaxes testadas:
  verbose      — exp 16
  compact_v1   — exp 21 (`@N:`, `@N<K`, `'X'`, `=N`)
  compact_v1b  — exp 23 NOVO (v1 sem `@N:`)
  compact_v2   — exp 22 (idx por fragmento, com `'X'`)
  compact_v3   — exp 23 NOVO (v2 sem aspas, `*` entre literais)

Todas geram TCF lossless. Tabela comparativa de bytes.
"""

import csv
from collections import OrderedDict
from pathlib import Path

from online import processar, reconstroi, TokLit, Token
from syntax_base import Syntax
from syntax_verbose import VerboseSyntax
from syntax_compact_v1 import CompactV1Syntax
from syntax_compact_v1b import CompactV1bSyntax
from syntax_compact_v2 import CompactV2Syntax
from syntax_compact_v3 import CompactV3Syntax

BASE = Path(__file__).parent
DATASETS = ["D2-mini", "D2-completo"]
SINTAXES = [
    VerboseSyntax(),
    CompactV1Syntax(),
    CompactV1bSyntax(),
    CompactV2Syntax(),
    CompactV3Syntax(),
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
    tcf = sintaxe.encode(linhas, unicas, tokens, header)
    out_dir = BASE / "encoded" / sintaxe.name
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{nome}.tcf").write_text(tcf, encoding="utf-8")
    decoded = sintaxe.decode(tcf)
    rt_ok = decoded == linhas
    if not rt_ok:
        for i, (a, b) in enumerate(zip(decoded, linhas)):
            if a != b:
                print(f"  RT FAIL {sintaxe.name} {nome} linha {i}: "
                      f"{a!r} != {b!r}")
                break
    return {"bytes": len(tcf.encode("utf-8")), "rt": rt_ok, "tcf": tcf}


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
                              "n_linhas": len(linhas), "sintaxes": {}}
        for syn in SINTAXES:
            r = rodar(nome, syn, linhas, unicas, tokens, header)
            resultados[nome]["sintaxes"][syn.name] = r

    # Tabela de bytes
    print("=" * 100)
    print("Tabela 1 - Bytes por sintaxe x dataset")
    print("-" * 100)
    syn_names = [s.name for s in SINTAXES]
    header_str = f"{'dataset':<14} {'N':>4} {'unid':>5}  " + "".join(
        f"{n:>13}" for n in syn_names)
    print(header_str)
    for nome in DATASETS:
        r = resultados[nome]
        row = f"{nome:<14} {r['n_unicas']:>4} {r['unidades']:>5}  "
        for sn in syn_names:
            b = r['sintaxes'][sn]['bytes']
            row += f"{b:>13}"
        print(row)

    print()
    print("=" * 100)
    print("Tabela 2 - Razao vs verbose (menor = melhor)")
    print("-" * 100)
    header_str = f"{'dataset':<14}  " + "".join(
        f"{n:>13}" for n in syn_names)
    print(header_str)
    for nome in DATASETS:
        r = resultados[nome]
        verbose_b = r['sintaxes']['verbose']['bytes']
        row = f"{nome:<14}  "
        for sn in syn_names:
            b = r['sintaxes'][sn]['bytes']
            row += f"{b/verbose_b:>13.3f}"
        print(row)

    print()
    print("=" * 100)
    print("Tabela 3 - Razao vs compact_v1 (menor = melhor que v1)")
    print("-" * 100)
    header_str = f"{'dataset':<14}  " + "".join(
        f"{n:>13}" for n in syn_names)
    print(header_str)
    for nome in DATASETS:
        r = resultados[nome]
        v1_b = r['sintaxes']['compact_v1']['bytes']
        row = f"{nome:<14}  "
        for sn in syn_names:
            b = r['sintaxes'][sn]['bytes']
            row += f"{b/v1_b:>13.3f}"
        print(row)

    falhas = []
    for nome in DATASETS:
        for sn, r in resultados[nome]["sintaxes"].items():
            if not r["rt"]:
                falhas.append(f"{nome}/{sn}")
    print()
    if not falhas:
        total_runs = len(DATASETS) * len(SINTAXES)
        print(f"Roundtrip OK em {total_runs}/{total_runs} runs.")
    else:
        print(f"FALHAS: {falhas}")

    # Imprimir TCFs lado a lado para D2-mini
    print()
    print("=" * 100)
    print("D2-mini lado a lado")
    print("=" * 100)
    for sn in syn_names:
        print(f"\n--- {sn} ({resultados['D2-mini']['sintaxes'][sn]['bytes']} bytes) ---")
        print(resultados["D2-mini"]["sintaxes"][sn]["tcf"], end="")


if __name__ == "__main__":
    main()
