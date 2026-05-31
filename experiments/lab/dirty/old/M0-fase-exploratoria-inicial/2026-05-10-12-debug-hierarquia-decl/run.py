"""Roda analise nos 4 datasets. Para cada:
  1. Reaplica decomposicao do exp 10 (com avos)
  2. Identifica pref/suf texts que tem pai Patricia ignorado
  3. Estima ganho/custo se decl fosse hierarquica
  4. Gera debug-output/<dataset>.txt
"""

import csv
from collections import OrderedDict
from pathlib import Path

from analise_hierarquia import (
    analisar_prefs,
    analisar_sufs,
    estimar_economia,
)
from arvore_bidir import construir_bidir, decompor_strings

BASE = Path(__file__).parent
DATASETS = [
    "D1-emails-um-dominio",
    "D2-emails-multi-dominio",
    "D3-urls-path-comum",
    "D4-urls-multi-recurso",
]
MIN_PREFIXO = 3

EXP10_REF_DADOS = {
    "D1-emails-um-dominio": 494,
    "D2-emails-multi-dominio": 655,
    "D3-urls-path-comum": 372,
    "D4-urls-multi-recurso": 505,
}


def ler_csv(path: Path) -> tuple[str, list[str]]:
    with path.open(encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)[0]
        return header, [r[0] for r in reader if r]


def analisar(nome: str) -> dict:
    header, linhas = ler_csv(BASE / "data" / f"{nome}.csv")
    fwd_a, fwd_m, rev_a, rev_m = construir_bidir(linhas, min_prefixo=MIN_PREFIXO)
    seen = OrderedDict()
    for s in linhas:
        seen[s] = True
    strings_unicas = list(seen.keys())
    decomps = decompor_strings(strings_unicas, fwd_a, fwd_m, rev_a, rev_m,
                               min_prefixo=MIN_PREFIXO)

    prefs_com_pai = analisar_prefs(decomps, fwd_a)
    sufs_com_pai = analisar_sufs(decomps, rev_a)

    est_pref = estimar_economia(prefs_com_pai, compartilhamento=True)
    est_suf = estimar_economia(sufs_com_pai, compartilhamento=True)

    out = []
    out.append("=" * 84)
    out.append(f"DATASET: {nome}")
    out.append("=" * 84)
    out.append(f"linhas: {len(linhas)}    unicas: {len(strings_unicas)}")
    out.append(f"tamanho ref+dados (exp 10): {EXP10_REF_DADOS[nome]} bytes")
    out.append("")

    out.append("PREF texts com pai Patricia ignorado:")
    if not prefs_com_pai:
        out.append("  (nenhum)")
    else:
        for p in prefs_com_pai:
            out.append(f"  pref={p.texto!r:<40} n={p.n_strings}")
            out.append(f"    pai={p.pai_texto!r}  extra={p.extra!r}")
    out.append("")
    out.append(f"  decl folha (atual): {est_pref['bytes_antes_total']} chars")
    out.append(f"  decl filho_de + pais ({est_pref['n_pais_unicos']}): "
               f"{est_pref['bytes_depois_total']} + {est_pref['custo_decl_pais']} = "
               f"{est_pref['bytes_depois_total'] + est_pref['custo_decl_pais']} chars")
    sinal = "+" if est_pref['delta_liquido'] >= 0 else ""
    out.append(f"  delta liquido: {sinal}{est_pref['delta_liquido']} chars")

    out.append("")
    out.append("SUF texts com pai Patricia ignorado:")
    if not sufs_com_pai:
        out.append("  (nenhum)")
    else:
        for s in sufs_com_pai:
            out.append(f"  suf={s.texto!r:<40} n={s.n_strings}")
            out.append(f"    pai={s.pai_texto!r}  extra={s.extra!r}")
    out.append("")
    out.append(f"  decl folha (atual): {est_suf['bytes_antes_total']} chars")
    out.append(f"  decl filho_de + pais ({est_suf['n_pais_unicos']}): "
               f"{est_suf['bytes_depois_total']} + {est_suf['custo_decl_pais']} = "
               f"{est_suf['bytes_depois_total'] + est_suf['custo_decl_pais']} chars")
    sinal = "+" if est_suf['delta_liquido'] >= 0 else ""
    out.append(f"  delta liquido: {sinal}{est_suf['delta_liquido']} chars")

    delta_total = est_pref['delta_liquido'] + est_suf['delta_liquido']
    out.append("")
    out.append(f"DELTA TOTAL (pref + suf) se decl fosse hierarquica: "
               f"{'+' if delta_total >= 0 else ''}{delta_total} chars")
    if delta_total < 0:
        pct = -100 * delta_total / EXP10_REF_DADOS[nome]
        out.append(f"  => economia de {-delta_total} chars ({pct:.1f}% de exp 10)")
    else:
        pct = 100 * delta_total / EXP10_REF_DADOS[nome]
        out.append(f"  => PERDA de {delta_total} chars ({pct:.1f}% de exp 10)")

    return {
        "nome": nome,
        "delta_pref": est_pref['delta_liquido'],
        "delta_suf": est_suf['delta_liquido'],
        "delta_total": delta_total,
        "n_prefs": est_pref['n_items'],
        "n_pais_pref": est_pref['n_pais_unicos'],
        "n_sufs": est_suf['n_items'],
        "n_pais_suf": est_suf['n_pais_unicos'],
        "relatorio": "\n".join(out),
    }


def main():
    resultados = []
    debug_dir = BASE / "debug-output"
    debug_dir.mkdir(exist_ok=True)
    for ds in DATASETS:
        r = analisar(ds)
        (debug_dir / f"{ds}.txt").write_text(r["relatorio"], encoding="utf-8")
        resultados.append(r)

    print("=" * 92)
    print("Tabela consolidada — ganho potencial de decl hierarquica para pref/suf")
    print("-" * 92)
    print(f"{'dataset':<32} {'n_prefs':>7} {'pais_p':>6} "
          f"{'n_sufs':>6} {'pais_s':>6} {'d_pref':>7} {'d_suf':>6} "
          f"{'d_total':>8}")
    for r in resultados:
        print(f"{r['nome']:<32} {r['n_prefs']:>7} {r['n_pais_pref']:>6} "
              f"{r['n_sufs']:>6} {r['n_pais_suf']:>6} "
              f"{r['delta_pref']:>+7} {r['delta_suf']:>+6} "
              f"{r['delta_total']:>+8}")
    print()
    print("Negativo = economia esperada. Positivo = perda.")
    print("Detalhes em debug-output/")


if __name__ == "__main__":
    main()
