"""Roda exp 22 (compact_v2 — idx automatico por fragmento) nos 21
datasets, comparando lado a lado com verbose e compact_v1.

Algoritmo intocado. So a sintaxe muda.
"""

import csv
from collections import OrderedDict
from pathlib import Path

from online import processar, reconstroi, TokLit, Token
from syntax_base import Syntax
from syntax_verbose import VerboseSyntax
from syntax_compact_v1 import CompactV1Syntax
from syntax_compact_v2 import CompactV2Syntax

BASE = Path(__file__).parent

GRUPO1 = ["D2-mini", "D2-completo", "D4"]
GRUPO2 = ["urls", "uuids", "iso-timestamps", "ips", "cpfs", "codigos"]
GRUPO3 = [f"{fam}-N{n:04d}" for fam in ("urls", "iso", "ips", "codigos")
          for n in (50, 200, 1000)]
TODOS = GRUPO1 + GRUPO2 + GRUPO3


def ler_csv(path: Path) -> tuple[str, list[str]]:
    with path.open(encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)[0]
        return header, [r[0] for r in reader if r]


def unidades_de_tokens(tokens_por_string: list[list[Token]]) -> int:
    total = 0
    for tokens in tokens_por_string:
        for tok in tokens:
            total += len(tok.text) if isinstance(tok, TokLit) else 1
    return total


def rodar_sintaxe(nome: str, linhas: list[str], unicas: list[str],
                    tokens, header: str, sintaxe: Syntax) -> dict:
    try:
        tcf = sintaxe.encode(linhas, unicas, tokens, header)
    except NotImplementedError as e:
        return {"tcf_bytes": -1, "rt_ok": False, "skip": str(e)}

    out_dir = BASE / "encoded" / sintaxe.name
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{nome}.tcf").write_text(tcf, encoding="utf-8")

    decoded = sintaxe.decode(tcf)
    rt_ok = decoded == linhas
    if not rt_ok:
        # diagnostico
        for i, (a, b) in enumerate(zip(decoded, linhas)):
            if a != b:
                print(f"  {sintaxe.name} {nome} linha {i}: {a!r} != {b!r}")
                break

    return {"tcf_bytes": len(tcf.encode("utf-8")), "rt_ok": rt_ok}


def rodar_caso(nome: str) -> dict:
    path = BASE / "data" / f"{nome}.csv"
    header, linhas = ler_csv(path)
    seen = OrderedDict()
    for s in linhas:
        seen[s] = True
    strings_unicas = list(seen.keys())

    tokens_por_str, _log = processar(strings_unicas, min_len=3)
    for s, tokens in zip(strings_unicas, tokens_por_str):
        rec = reconstroi(tokens, strings_unicas)
        assert rec == s, f"reconstroi falhou {nome}: {s!r} -> {rec!r}"

    r_v = rodar_sintaxe(nome, linhas, strings_unicas, tokens_por_str,
                          header, VerboseSyntax())
    r_c1 = rodar_sintaxe(nome, linhas, strings_unicas, tokens_por_str,
                           header, CompactV1Syntax())
    r_c2 = rodar_sintaxe(nome, linhas, strings_unicas, tokens_por_str,
                           header, CompactV2Syntax())

    return {
        "nome": nome,
        "n_unicas": len(strings_unicas),
        "n_linhas": len(linhas),
        "unidades": unidades_de_tokens(tokens_por_str),
        "verbose": r_v,
        "compact_v1": r_c1,
        "compact_v2": r_c2,
    }


def main():
    print(f"Rodando {len(TODOS)} datasets em 3 sintaxes...")
    print()
    resultados = [rodar_caso(nome) for nome in TODOS]

    print("=" * 110)
    print("Tabela 1 - Bytes por sintaxe")
    print("-" * 110)
    print(f"{'dataset':<22} {'unid':>6} {'verbose':>8} {'compact_v1':>11} "
          f"{'compact_v2':>11}  {'v2/v1':>6} {'v2/verb':>8}")
    tot_v = tot_c1 = tot_c2 = 0
    for r in resultados:
        v = r['verbose']['tcf_bytes']
        c1 = r['compact_v1']['tcf_bytes']
        c2 = r['compact_v2']['tcf_bytes']
        if c2 == -1:
            c2_str = "skip"
            ratio_21 = ratio_2v = "—"
        else:
            c2_str = f"{c2}"
            ratio_21 = f"{c2/c1:.3f}"
            ratio_2v = f"{c2/v:.3f}"
            tot_c2 += c2
        tot_v += v
        tot_c1 += c1
        rt_marks = (
            "v" if r['verbose']['rt_ok'] else "x"
        ) + (
            "1" if r['compact_v1']['rt_ok'] else "x"
        ) + (
            "2" if r['compact_v2']['rt_ok'] else "x"
        )
        print(f"{r['nome']:<22} {r['unidades']:>6} {v:>8} {c1:>11} "
              f"{c2_str:>11}  {ratio_21:>6} {ratio_2v:>8}  [{rt_marks}]")

    print("-" * 110)
    print(f"{'TOTAL':<22} {'':>6} {tot_v:>8} {tot_c1:>11} {tot_c2:>11}  "
          f"{tot_c2/tot_c1:>6.3f} {tot_c2/tot_v:>8.3f}")

    print()
    print("=" * 110)
    print("Tabela 2 - Custo bytes/unidade")
    print("-" * 110)
    print(f"{'dataset':<22} {'unid':>6} {'b/u verb':>10} {'b/u c1':>10} {'b/u c2':>10}")
    for r in resultados:
        u = r['unidades']
        v = r['verbose']['tcf_bytes']
        c1 = r['compact_v1']['tcf_bytes']
        c2 = r['compact_v2']['tcf_bytes']
        print(f"{r['nome']:<22} {u:>6} {v/u:>10.2f} {c1/u:>10.2f} "
              f"{c2/u if c2 > 0 else 0:>10.2f}")

    falhas = []
    for r in resultados:
        for syn_name in ('verbose', 'compact_v1', 'compact_v2'):
            if not r[syn_name]['rt_ok'] and r[syn_name]['tcf_bytes'] != -1:
                falhas.append(f"{r['nome']}/{syn_name}")
    print()
    if not falhas:
        print(f"Roundtrip OK em {len(resultados)*3} runs (3 sintaxes x {len(resultados)} datasets)")
    else:
        print(f"FALHAS: {falhas}")


if __name__ == "__main__":
    main()
