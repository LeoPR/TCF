"""Roda 2 datasets (D2-mini e D2-completo), gera debug textual completo
e salva em debug-output/. Analisa padroes nao detectados (substrings
que apareceriam em uma arvore mais sofisticada).
"""

import csv
from collections import Counter, OrderedDict
from pathlib import Path

from arvore_bidir_debug import (
    construir_bidir_debug,
    decompor_string_debug,
)
from patricia_instrumentado import desenhar_arvore

BASE = Path(__file__).parent
DATASETS = ["D2-mini", "D2-completo"]
MIN_PREFIXO = 3


def ler_csv(path: Path) -> tuple[str, list[str]]:
    with path.open(encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)[0]
        return header, [r[0] for r in reader if r]


def substrings_comuns(strings: list[str], min_len: int = 3,
                       min_count: int = 2) -> list[tuple[str, int]]:
    """Conta TODAS as substrings que aparecem em >= min_count strings
    distintas (cobertura), nao por posicao. Util para encontrar
    padroes 'no meio' que o Patricia greedy nao capturou.
    """
    cont: Counter = Counter()
    for s in strings:
        # registra cada substring unica desta string (sem duplicar dentro de uma)
        substrs_da_string: set[str] = set()
        for i in range(len(s)):
            for j in range(i + min_len, len(s) + 1):
                substrs_da_string.add(s[i:j])
        for sub in substrs_da_string:
            cont[sub] += 1
    return [(sub, c) for sub, c in cont.items() if c >= min_count]


def processar(nome: str) -> str:
    """Gera o relatorio textual completo para um dataset."""
    input_path = BASE / "data" / f"{nome}.csv"
    header, linhas = ler_csv(input_path)

    out: list[str] = []
    out.append("=" * 70)
    out.append(f"DATASET: {nome}")
    out.append("=" * 70)
    out.append(f"linhas: {len(linhas)}")
    out.append(f"min_prefixo: {MIN_PREFIXO}")
    out.append("")
    out.append("strings originais:")
    for i, s in enumerate(linhas):
        out.append(f"  {i+1:>3}. {s!r}")

    # Strings unicas
    seen = OrderedDict()
    for s in linhas:
        seen[s] = True
    strings_unicas = list(seen.keys())
    out.append("")
    out.append(f"strings unicas: {len(strings_unicas)}")

    # Construcao das 2 arvores com debug
    fwd_a, fwd_m, rev_a, rev_m, log_constr = construir_bidir_debug(
        linhas, min_prefixo=MIN_PREFIXO
    )
    out.append("")
    out.append(log_constr)

    # Arvore final - desenho ASCII
    out.append("")
    out.append("=" * 70)
    out.append("ARVORE FORWARD FINAL (apos todas as iteracoes)")
    out.append("=" * 70)
    out.append(desenhar_arvore(fwd_a))

    out.append("")
    out.append("=" * 70)
    out.append("ARVORE REVERSE FINAL (texto invertido — sufixos naturais)")
    out.append("=" * 70)
    # Imprime arvore reverse com des-inversao dos fragmentos textuais
    out.append("(o algoritmo trabalha sobre strings invertidas. Para leitura:")
    out.append(" cada 'fragmento' eh a parte invertida; o texto natural eh o reverso.)")
    out.append("")
    out.append(desenhar_arvore(rev_a))

    # Decomposicao por string unica
    out.append("")
    out.append("=" * 70)
    out.append("FASE C — DECOMPOSICAO POR STRING UNICA")
    out.append("=" * 70)
    for s in strings_unicas:
        (_p, _m, _x), log_d = decompor_string_debug(
            s, fwd_a, fwd_m, rev_a, rev_m, min_prefixo=MIN_PREFIXO
        )
        out.append(log_d)

    # Analise: padroes nao detectados
    out.append("")
    out.append("=" * 70)
    out.append("ANALISE — padroes intermediarios que Patricia greedy NAO capturou")
    out.append("=" * 70)
    out.append("")
    out.append("Comparativo: substrings que aparecem em >= 2 strings unicas")
    out.append("(metrica de cobertura). Inclui prefixos e sufixos detectados pelo")
    out.append("Patricia, mas tambem substrings 'no meio' que ele nunca tenta capturar.")
    out.append("")
    subs = substrings_comuns(strings_unicas, min_len=MIN_PREFIXO, min_count=2)
    subs.sort(key=lambda x: (-len(x[0]) * x[1], -len(x[0]), -x[1]))
    out.append(f"top 20 substrings por ganho potencial (len * count, desc):")
    out.append(f"  {'len':>3} {'count':>5} {'ganho':>5}  substring")
    for sub, c in subs[:20]:
        ganho = len(sub) * c
        out.append(f"  {len(sub):>3} {c:>5} {ganho:>5}  {sub!r}")

    out.append("")
    out.append("Comentario: Patricia greedy considera apenas PREFIXOS das folhas")
    out.append("top-level. Substrings que aparecem 'no meio' ou que sao prefixos")
    out.append("de pais ja absorvidos nao sao re-avaliadas. Algumas das substrings")
    out.append("acima podem ter sido capturadas (como prefixo ou sufixo); outras")
    out.append("nao.")

    return "\n".join(out)


def main():
    debug_dir = BASE / "debug-output"
    debug_dir.mkdir(exist_ok=True)
    for ds in DATASETS:
        relatorio = processar(ds)
        path = debug_dir / f"{ds}-debug.txt"
        path.write_text(relatorio, encoding="utf-8")
        print(f"escrito: {path} ({len(relatorio)} chars)")
    print()
    print("Para inspecionar:")
    for ds in DATASETS:
        print(f"  cat debug-output/{ds}-debug.txt")


if __name__ == "__main__":
    main()
