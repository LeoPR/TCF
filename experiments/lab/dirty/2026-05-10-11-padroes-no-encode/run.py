"""Roda analise de padroes nos 4 datasets do exp 10.

Para cada dataset:
  1. Constroi as 2 arvores Patricia (forward + reverse) — codigo do exp 10
  2. Decompoe cada string unica em (pref, mid, suf) — codigo do exp 10
  3. Lista pares (mid, suf) e (pref, mid) com count >= 2
  4. Estima ganho potencial em bytes se cada par fosse fatorado

Output em debug-output/<dataset>-padroes.txt e tabela consolidada
no stdout.
"""

import csv
from collections import OrderedDict
from pathlib import Path

from analise_padroes import (
    _alocar_eids,
    coletar_padroes_mid_suf,
    coletar_padroes_pref_mid,
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

# Tamanhos do exp 10 (ref + dados) para comparar com ganho potencial
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

    eids_pref, eids_suf = _alocar_eids(decomps)
    padroes_ms = coletar_padroes_mid_suf(decomps, eids_suf)
    padroes_pm = coletar_padroes_pref_mid(decomps, eids_pref)

    # Relatorio textual
    out = []
    out.append("=" * 80)
    out.append(f"DATASET: {nome}")
    out.append("=" * 80)
    out.append(f"linhas: {len(linhas)}    unicas: {len(strings_unicas)}")
    out.append(f"tamanho ref+dados (exp 10): {EXP10_REF_DADOS[nome]} bytes")
    out.append("")
    out.append("Decomposicoes (do exp 10):")
    for s, d in decomps.items():
        p = d.prefix_text or "-"
        x = d.suffix_text or "-"
        out.append(f"  {s:<32} pref={p!r:<16} mid={d.middle!r:<10} suf={x!r}")

    out.append("")
    out.append("-" * 80)
    out.append("Padroes (mid, suf) com count >= 2:")
    if not padroes_ms:
        out.append("  (nenhum)")
    else:
        out.append(f"  {'count':>5} {'mid':<10} {'suf':<14} {'econ/oc':>7} "
                   f"{'custo_decl':>10} {'ganho':>7}")
        for p in padroes_ms:
            mid, suf = p.par
            out.append(f"  {p.count:>5} {mid!r:<10} {suf!r:<14} "
                       f"{p.economia_por_oc:>7} {p.custo_decl:>10} "
                       f"{p.ganho_liquido:>+7}")

    out.append("")
    out.append("-" * 80)
    out.append("Padroes (pref, mid) com count >= 2:")
    if not padroes_pm:
        out.append("  (nenhum)")
    else:
        out.append(f"  {'count':>5} {'pref':<16} {'mid':<10} {'econ/oc':>7} "
                   f"{'custo_decl':>10} {'ganho':>7}")
        for p in padroes_pm:
            pref, mid = p.par
            out.append(f"  {p.count:>5} {pref!r:<16} {mid!r:<10} "
                       f"{p.economia_por_oc:>7} {p.custo_decl:>10} "
                       f"{p.ganho_liquido:>+7}")

    ganho_total_ms = sum(p.ganho_liquido for p in padroes_ms
                         if p.ganho_liquido > 0)
    ganho_total_pm = sum(p.ganho_liquido for p in padroes_pm
                         if p.ganho_liquido > 0)
    out.append("")
    out.append("-" * 80)
    out.append(f"Ganho potencial total (so padroes com ganho > 0):")
    out.append(f"  (mid, suf): {ganho_total_ms} bytes")
    out.append(f"  (pref, mid): {ganho_total_pm} bytes")
    out.append(f"  SOMA: {ganho_total_ms + ganho_total_pm} bytes "
               f"({100*(ganho_total_ms + ganho_total_pm) / EXP10_REF_DADOS[nome]:.1f}% de exp 10)")
    out.append("")
    out.append("ATENCAO: ganhos NAO sao aditivos diretos quando os mesmos pares")
    out.append("se sobrepoem (mesma string pode ser fatorada por (mid,suf) ou")
    out.append("(pref,mid), nao ambos). Limite superior, nao previsao exata.")

    return {
        "nome": nome,
        "ganho_ms": ganho_total_ms,
        "ganho_pm": ganho_total_pm,
        "soma": ganho_total_ms + ganho_total_pm,
        "exp10": EXP10_REF_DADOS[nome],
        "relatorio": "\n".join(out),
    }


def main():
    resultados = []
    debug_dir = BASE / "debug-output"
    debug_dir.mkdir(exist_ok=True)
    for ds in DATASETS:
        r = analisar(ds)
        (debug_dir / f"{ds}-padroes.txt").write_text(r["relatorio"],
                                                      encoding="utf-8")
        resultados.append(r)

    # Tabela consolidada
    print("=" * 84)
    print("Tabela consolidada — ganho potencial por fatorizacao de padroes")
    print("-" * 84)
    print(f"{'dataset':<32} {'exp10':>6} {'ganho_ms':>9} {'ganho_pm':>9} "
          f"{'soma':>6} {'%':>5}")
    for r in resultados:
        pct = 100 * r['soma'] / r['exp10']
        print(f"{r['nome']:<32} {r['exp10']:>6} {r['ganho_ms']:>9} "
              f"{r['ganho_pm']:>9} {r['soma']:>6} {pct:>4.1f}%")
    print()
    print("Detalhes salvos em debug-output/")


if __name__ == "__main__":
    main()
