"""Roda exp 21 (sintaxe compacta v1) nos 21 datasets do exp 20.

Para cada dataset:
1. Algoritmo `online.py` produz tokens (uma unica vez)
2. Encode com VerboseSyntax + roundtrip
3. Encode com CompactV1Syntax + roundtrip
4. Compara bytes lado a lado

Hipotese: CompactV1Syntax produz TCFs com menos bytes em todos
os datasets, mantendo roundtrip.

Algoritmo nao muda (`online.py` intocado). So a serializacao
muda — TCFs sao representacoes diferentes da mesma estrutura.
"""

import csv
from collections import OrderedDict
from pathlib import Path

from online import processar, reconstroi, TokLit, Token
from syntax_base import Syntax
from syntax_verbose import VerboseSyntax
from syntax_compact_v1 import CompactV1Syntax

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


def processar_uma_sintaxe(nome: str, linhas: list[str], unicas: list[str],
                            tokens, header: str, sintaxe: Syntax) -> dict:
    """Encode + decode + medicoes para uma sintaxe."""
    tcf = sintaxe.encode(linhas, unicas, tokens, header)
    out_dir = BASE / "encoded" / sintaxe.name
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{nome}.tcf").write_text(tcf, encoding="utf-8")

    decoded = sintaxe.decode(tcf)
    rt_ok = decoded == linhas
    if not rt_ok:
        print(f"  RT FAIL em {nome}/{sintaxe.name}")
        for i, (a, b) in enumerate(zip(decoded, linhas)):
            if a != b:
                print(f"    linha {i}: {a!r} != {b!r}")
                break

    return {
        "tcf_bytes": len(tcf.encode("utf-8")),
        "rt_ok": rt_ok,
        "tcf": tcf,
    }


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
        assert rec == s, f"reconstroi falhou em {nome}: {s!r} -> {rec!r}"

    r_verbose = processar_uma_sintaxe(
        nome, linhas, strings_unicas, tokens_por_str, header, VerboseSyntax())
    r_compact = processar_uma_sintaxe(
        nome, linhas, strings_unicas, tokens_por_str, header, CompactV1Syntax())

    return {
        "nome": nome,
        "n_unicas": len(strings_unicas),
        "unidades": unidades_de_tokens(tokens_por_str),
        "bytes_verbose": r_verbose["tcf_bytes"],
        "bytes_compact": r_compact["tcf_bytes"],
        "rt_verbose": r_verbose["rt_ok"],
        "rt_compact": r_compact["rt_ok"],
    }


def main():
    print(f"Rodando {len(TODOS)} datasets em 2 sintaxes (verbose + compact_v1)...")
    print()
    resultados: list[dict] = []
    for nome in TODOS:
        r = rodar_caso(nome)
        resultados.append(r)

    print("=" * 100)
    print("Tabela 1 - Bytes por sintaxe, em cada dataset")
    print("-" * 100)
    print(f"{'dataset':<22} {'rt_v':>4} {'rt_c':>4} {'unid':>6} "
          f"{'verbose':>8} {'compact':>8} {'reducao':>9} {'razao':>8}")
    total_v = 0
    total_c = 0
    for r in resultados:
        v = r['bytes_verbose']
        c = r['bytes_compact']
        red = v - c
        razao = c / v if v else 0
        total_v += v
        total_c += c
        print(f"{r['nome']:<22} {'OK' if r['rt_verbose'] else 'FAIL':>4} "
              f"{'OK' if r['rt_compact'] else 'FAIL':>4} "
              f"{r['unidades']:>6} {v:>8} {c:>8} {red:>+8} {razao:>7.3f}")

    print("-" * 100)
    print(f"{'TOTAL':<22} {'':>4} {'':>4} {'':>6} "
          f"{total_v:>8} {total_c:>8} {total_v - total_c:>+8} "
          f"{total_c/total_v:>7.3f}")

    print()
    print("=" * 100)
    print("Tabela 2 - Razao bytes/unidades (custo medio por unidade de informacao)")
    print("-" * 100)
    print(f"{'dataset':<22} {'unid':>6} {'b_v':>7} {'bv/u':>8} {'b_c':>7} {'bc/u':>8}")
    for r in resultados:
        u = r['unidades']
        v = r['bytes_verbose']
        c = r['bytes_compact']
        bvu = v / u if u else 0
        bcu = c / u if u else 0
        print(f"{r['nome']:<22} {u:>6} {v:>7} {bvu:>8.2f} {c:>7} {bcu:>8.2f}")

    falhas_v = [r for r in resultados if not r['rt_verbose']]
    falhas_c = [r for r in resultados if not r['rt_compact']]
    print()
    if not falhas_v and not falhas_c:
        print(f"Roundtrip OK em {len(resultados)}/{len(resultados)} para ambas sintaxes.")
    else:
        if falhas_v:
            print(f"VERBOSE falhas: {[r['nome'] for r in falhas_v]}")
        if falhas_c:
            print(f"COMPACT falhas: {[r['nome'] for r in falhas_c]}")


if __name__ == "__main__":
    main()
