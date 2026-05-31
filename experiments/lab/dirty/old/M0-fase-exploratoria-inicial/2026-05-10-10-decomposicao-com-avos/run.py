"""Roda 4 datasets, mostra:
  - Distribuicao das decomposicoes (compostas / so pref / so suf / folhas)
  - Bytes ref+dados lado a lado vs exp 08 (numeros do exp 08 hardcoded)
  - Decomposicao detalhada de D2-mini-like (so D2 completo neste exp)
"""

import csv
from collections import OrderedDict
from pathlib import Path

from arvore_bidir import construir_bidir, decompor_strings
from decode_composto import decode_composto
from encode_composto import encode_composto
from formula import decompor

BASE = Path(__file__).parent
DATASETS = [
    "D1-emails-um-dominio",
    "D2-emails-multi-dominio",
    "D3-urls-path-comum",
    "D4-urls-multi-recurso",
]
MIN_PREFIXO = 3

# Numeros do exp 08 (min_prefixo=3) — para comparacao lado a lado
EXP08_REF_DADOS = {
    "D1-emails-um-dominio": 494,
    "D2-emails-multi-dominio": 610,
    "D3-urls-path-comum": 372,
    "D4-urls-multi-recurso": 505,
}


def ler_csv(path: Path) -> tuple[str, list[str]]:
    with path.open(encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)[0]
        return header, [r[0] for r in reader if r]


def salvar_csv(path: Path, header: str, linhas: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([header])
        for v in linhas:
            writer.writerow([v])


def processar(nome: str) -> dict:
    input_path = BASE / "data" / f"{nome}.csv"
    header, linhas = ler_csv(input_path)

    fwd_a, fwd_m, rev_a, rev_m = construir_bidir(linhas, min_prefixo=MIN_PREFIXO)

    seen = OrderedDict()
    for s in linhas:
        seen[s] = True
    strings_unicas = list(seen.keys())

    decomp = decompor_strings(strings_unicas, fwd_a, fwd_m, rev_a, rev_m,
                              min_prefixo=MIN_PREFIXO)

    # Sanidade
    for s, d in decomp.items():
        assert d.reconstroi() == s, f"decomp invalida para {s!r}: {d}"

    tcf = encode_composto(linhas, decomp, header)
    encoded_path = BASE / "encoded" / f"{nome}.tcf"
    encoded_path.parent.mkdir(parents=True, exist_ok=True)
    encoded_path.write_text(tcf, encoding="utf-8")

    decoded = decode_composto(tcf)
    salvar_csv(BASE / "decoded" / f"{nome}.csv", header, decoded)
    rt_ok = decoded == linhas

    macro, ref, dados = decompor(tcf)

    n_compostas = sum(1 for d in decomp.values() if d.prefix_text and d.suffix_text)
    n_so_pref = sum(1 for d in decomp.values() if d.prefix_text and not d.suffix_text)
    n_so_suf = sum(1 for d in decomp.values() if d.suffix_text and not d.prefix_text)
    n_folhas = sum(1 for d in decomp.values() if not d.prefix_text and not d.suffix_text)

    return {
        "dataset": nome,
        "linhas": len(linhas),
        "n_unicas": len(strings_unicas),
        "n_compostas": n_compostas,
        "n_so_pref": n_so_pref,
        "n_so_suf": n_so_suf,
        "n_folhas": n_folhas,
        "rt_ok": rt_ok,
        "total": len(tcf.encode("utf-8")),
        "macro": macro,
        "ref": ref,
        "dados": dados,
        "ref_mais_dados": ref + dados,
        "tcf": tcf,
        "decomp": decomp,
    }


def main():
    resultados = [processar(ds) for ds in DATASETS]

    print("=" * 92)
    print("Tabela 1 — Roundtrip")
    print("-" * 92)
    print(f"{'dataset':<32} {'linhas':>6} {'unicas':>6} {'rt':>4}")
    for r in resultados:
        print(f"{r['dataset']:<32} {r['linhas']:>6} {r['n_unicas']:>6} "
              f"{'OK' if r['rt_ok'] else 'FAIL':>4}")

    print()
    print("=" * 92)
    print("Tabela 2 — Distribuicao das decomposicoes (compostas / so_pref / so_suf / folhas)")
    print("-" * 92)
    print(f"{'dataset':<32} {'unicas':>6} {'compostas':>10} {'so_pref':>8} "
          f"{'so_suf':>7} {'folhas':>7}")
    for r in resultados:
        print(f"{r['dataset']:<32} {r['n_unicas']:>6} "
              f"{r['n_compostas']:>10} {r['n_so_pref']:>8} "
              f"{r['n_so_suf']:>7} {r['n_folhas']:>7}")

    print()
    print("=" * 92)
    print("Tabela 3 — Bytes ref+dados — exp 10 (com avos) vs exp 08 (so pai imediato)")
    print("-" * 92)
    print(f"{'dataset':<32} {'exp08':>6} {'exp10':>6} {'delta':>7} {'menor':>7}")
    for r in resultados:
        v08 = EXP08_REF_DADOS[r['dataset']]
        v10 = r['ref_mais_dados']
        delta = v10 - v08
        sinal = "+" if delta >= 0 else ""
        menor = "exp10" if v10 < v08 else ("exp08" if v08 < v10 else "empate")
        print(f"{r['dataset']:<32} {v08:>6} {v10:>6} {sinal}{delta:>6} {menor:>7}")

    print()
    print("=" * 92)
    print("Tabela 4 — Decomposicao detalhada de D2 (o caso problema)")
    print("-" * 92)
    r_d2 = next(r for r in resultados if "D2" in r['dataset'])
    for s, d in r_d2['decomp'].items():
        p = d.prefix_text or "-"
        x = d.suffix_text or "-"
        m = d.middle
        print(f"  {s:<32} pref={p!r:<18} mid={m!r:<14} suf={x!r}")

    # TCFs completos para D1 e D2
    print()
    for r in resultados:
        if r['dataset'] not in ("D1-emails-um-dominio", "D2-emails-multi-dominio"):
            continue
        print("=" * 92)
        print(f"TCF: {r['dataset']}")
        print("-" * 92)
        for ln in r['tcf'].splitlines():
            print(f"  {ln}")
        print()


if __name__ == "__main__":
    main()
