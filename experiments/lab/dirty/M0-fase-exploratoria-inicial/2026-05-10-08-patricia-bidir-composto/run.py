"""Roda 4 datasets x 2 thresholds (min_prefixo = 2 e 3) = 8 cenarios.

Para cada:
  1. Constroi 2 arvores Patricia (forward + reverse)
  2. Decompoe cada string unica em (pref, middle, suf)
  3. Encoda em sintaxe composta
  4. Decodifica e valida roundtrip
  5. Mede ref + dados (camada 2 + camada 1, comparacao valida)
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
THRESHOLDS = [3, 2]


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


def processar(nome: str, min_prefixo: int) -> dict:
    input_path = BASE / "data" / f"{nome}.csv"
    header, linhas = ler_csv(input_path)

    fwd_a, fwd_m, rev_a, rev_m = construir_bidir(linhas, min_prefixo=min_prefixo)

    # strings unicas em ordem de aparicao
    seen = OrderedDict()
    for s in linhas:
        seen[s] = True
    strings_unicas = list(seen.keys())

    decomp = decompor_strings(strings_unicas, fwd_a, fwd_m, rev_a, rev_m,
                              min_prefixo=min_prefixo)

    # Sanidade: cada decomposicao reconstroi a string original
    for s, d in decomp.items():
        assert d.reconstroi() == s, f"decomposicao invalida para {s!r}: {d}"

    tcf = encode_composto(linhas, decomp, header)
    encoded_path = BASE / "encoded" / f"{nome}-min{min_prefixo}.tcf"
    encoded_path.parent.mkdir(parents=True, exist_ok=True)
    encoded_path.write_text(tcf, encoding="utf-8")

    decoded = decode_composto(tcf)
    salvar_csv(BASE / "decoded" / f"{nome}-min{min_prefixo}.csv", header, decoded)
    rt_ok = decoded == linhas

    macro, ref, dados = decompor(tcf)

    n_strings_com_pref = sum(1 for d in decomp.values() if d.prefix_text)
    n_strings_com_suf = sum(1 for d in decomp.values() if d.suffix_text)
    n_strings_compostas = sum(
        1 for d in decomp.values() if d.prefix_text and d.suffix_text
    )
    n_strings_folhas = sum(
        1 for d in decomp.values()
        if not d.prefix_text and not d.suffix_text
    )

    return {
        "dataset": nome,
        "min_prefixo": min_prefixo,
        "linhas": len(linhas),
        "n_unicas": len(strings_unicas),
        "n_com_pref": n_strings_com_pref,
        "n_com_suf": n_strings_com_suf,
        "n_compostas": n_strings_compostas,
        "n_folhas": n_strings_folhas,
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
    resultados = []
    for ds in DATASETS:
        for mp in THRESHOLDS:
            resultados.append(processar(ds, mp))

    # Tabela 1: roundtrip
    print("=" * 96)
    print("Tabela 1 — Roundtrip (8 cenarios = 4 datasets x 2 thresholds)")
    print("-" * 96)
    print(f"{'dataset':<32} {'min_p':>5} {'linhas':>6} {'unicas':>6} {'rt':>4}")
    for r in resultados:
        print(f"{r['dataset']:<32} {r['min_prefixo']:>5} "
              f"{r['linhas']:>6} {r['n_unicas']:>6} "
              f"{'OK' if r['rt_ok'] else 'FAIL':>4}")

    # Tabela 2: classificacao das strings (caso por string)
    print()
    print("=" * 96)
    print("Tabela 2 — Distribuicao das strings unicas por caso")
    print("-" * 96)
    print(f"{'dataset':<32} {'min_p':>5} {'unicas':>6} {'compostas':>10} "
          f"{'so_pref':>8} {'so_suf':>8} {'folhas':>7}")
    for r in resultados:
        so_pref = r['n_com_pref'] - r['n_compostas']
        so_suf = r['n_com_suf'] - r['n_compostas']
        print(f"{r['dataset']:<32} {r['min_prefixo']:>5} {r['n_unicas']:>6} "
              f"{r['n_compostas']:>10} {so_pref:>8} {so_suf:>8} "
              f"{r['n_folhas']:>7}")

    # Tabela 3: ref + dados por cenario
    print()
    print("=" * 96)
    print("Tabela 3 — Bytes ref+dados por cenario (comparacao valida)")
    print("-" * 96)
    print(f"{'dataset':<32} {'min_p':>5} {'macro':>5} {'ref':>5} "
          f"{'dados':>5} {'ref+dados':>9}")
    for r in resultados:
        print(f"{r['dataset']:<32} {r['min_prefixo']:>5} {r['macro']:>5} "
              f"{r['ref']:>5} {r['dados']:>5} {r['ref_mais_dados']:>9}")

    # Tabela 4: comparacao entre thresholds
    print()
    print("=" * 96)
    print("Tabela 4 — Comparacao threshold 3 vs 2 (ref+dados)")
    print("-" * 96)
    print(f"{'dataset':<32} {'min3':>5} {'min2':>5} {'delta':>6} {'menor':>7}")
    by_ds = {}
    for r in resultados:
        by_ds.setdefault(r['dataset'], {})[r['min_prefixo']] = r['ref_mais_dados']
    for ds, vals in by_ds.items():
        v3 = vals[3]
        v2 = vals[2]
        delta = v2 - v3
        sinal = "+" if delta >= 0 else ""
        menor = "min3" if v3 < v2 else ("min2" if v2 < v3 else "empate")
        print(f"{ds:<32} {v3:>5} {v2:>5} {sinal}{delta:>5} {menor:>7}")

    # Imprime decomposicoes + TCF
    for r in resultados:
        print()
        print("=" * 96)
        print(f"Cenario: {r['dataset']}  (min_prefixo={r['min_prefixo']})")
        print("-" * 96)
        print("  Decomposicao das strings unicas:")
        for s, d in r['decomp'].items():
            p = f'"{d.prefix_text}"' if d.prefix_text else "-"
            m = f'"{d.middle}"'
            x = f'"{d.suffix_text}"' if d.suffix_text else "-"
            print(f"    {s!r:<40} -> pref={p:<14} mid={m:<14} suf={x}")
        print()
        print("  TCF:")
        for ln in r['tcf'].splitlines():
            print(f"    {ln}")


if __name__ == "__main__":
    main()
