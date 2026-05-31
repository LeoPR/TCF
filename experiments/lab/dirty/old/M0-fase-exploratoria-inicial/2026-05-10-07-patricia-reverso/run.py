"""Para cada um dos 4 datasets, encoda em forward e em reverse,
decodifica ambos, valida roundtrip, e reporta camada 2 (marcadores
de referencia) lado a lado.

Sem heuristica de escolha automatica. O objetivo e isolar o efeito
do espelho.
"""

import csv
from pathlib import Path

from decode_bidir import decode_bidir
from encode_bidir import encode_direcao
from formula import decompor
from patricia import aplicar_patricia, construir_inicial, desenhar_arvore

BASE = Path(__file__).parent

DATASETS = [
    "D1-emails-um-dominio",
    "D2-emails-multi-dominio",
    "D3-urls-path-comum",
    "D4-urls-multi-recurso",
]


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


def construir_arvore_para_visualizacao(linhas: list[str], direcao: str):
    if direcao == "reverse":
        linhas = [s[::-1] for s in linhas]
    nos, _ = construir_inicial(linhas)
    nos = aplicar_patricia(nos)
    return nos


def processar(nome: str) -> dict:
    input_path = BASE / "data" / f"{nome}.csv"
    header, linhas = ler_csv(input_path)

    r: dict = {"dataset": nome, "linhas": len(linhas)}

    for direcao in ("forward", "reverse"):
        tcf = encode_direcao(linhas, direcao, header)
        encoded_path = BASE / "encoded" / f"{nome}-{direcao}.tcf"
        encoded_path.parent.mkdir(parents=True, exist_ok=True)
        encoded_path.write_text(tcf, encoding="utf-8")

        decoded = decode_bidir(tcf)
        decoded_path = BASE / "decoded" / f"{nome}-{direcao}.csv"
        salvar_csv(decoded_path, header, decoded)

        rt_ok = decoded == linhas
        macro, ref, dados = decompor(tcf)

        nos_vis = construir_arvore_para_visualizacao(linhas, direcao)
        n_top = sum(1 for n in nos_vis.values() if n.pai_id is None)
        n_filhos = sum(1 for n in nos_vis.values() if n.pai_id is not None)

        r[direcao] = {
            "tcf": tcf,
            "rt_ok": rt_ok,
            "total": len(tcf.encode("utf-8")),
            "macro": macro,
            "ref": ref,
            "dados": dados,
            "n_nos": len(nos_vis),
            "n_top": n_top,
            "n_filhos": n_filhos,
            "arvore": desenhar_arvore(nos_vis),
        }
    return r


def main():
    resultados = [processar(ds) for ds in DATASETS]

    # Tabela 1: roundtrip
    print("=" * 92)
    print("Tabela 1 — Roundtrip (8 verificacoes)")
    print("-" * 92)
    print(f"{'dataset':<32} {'linhas':>6} {'rt_fwd':>7} {'rt_rev':>7}")
    for r in resultados:
        print(f"{r['dataset']:<32} {r['linhas']:>6} "
              f"{'OK' if r['forward']['rt_ok'] else 'FAIL':>7} "
              f"{'OK' if r['reverse']['rt_ok'] else 'FAIL':>7}")

    # Tabela 2: estrutura da arvore por direcao
    print()
    print("=" * 92)
    print("Tabela 2 — Estrutura da arvore por direcao (n_nos / n_top / n_filhos)")
    print("-" * 92)
    print(f"{'dataset':<32} {'forward':<24} {'reverse':<24}")
    for r in resultados:
        f_str = f"{r['forward']['n_nos']:>3} / {r['forward']['n_top']:>3} / {r['forward']['n_filhos']:>3}"
        v_str = f"{r['reverse']['n_nos']:>3} / {r['reverse']['n_top']:>3} / {r['reverse']['n_filhos']:>3}"
        print(f"{r['dataset']:<32} {f_str:<24} {v_str:<24}")

    # Tabela 3: camada 2 (marcadores) lado a lado
    print()
    print("=" * 92)
    print("Tabela 3 — Camada 2 (marcadores de ref) — NAO comparavel diretamente")
    print("            (arvores diferentes em fwd vs rev — ver Tabela 5)")
    print("-" * 92)
    print(f"{'dataset':<32} {'fwd_ref':>8} {'rev_ref':>8} {'delta':>8}")
    for r in resultados:
        f = r['forward']['ref']
        v = r['reverse']['ref']
        delta = v - f
        sinal = "+" if delta >= 0 else ""
        print(f"{r['dataset']:<32} {f:>8} {v:>8} {sinal}{delta:>7}")

    # Tabela 5: ref + dados (comparacao valida — exclui macros constantes)
    print()
    print("=" * 92)
    print("Tabela 5 — ref + dados (comparacao valida) — qual direcao tem menos bytes")
    print("-" * 92)
    print(f"{'dataset':<32} {'fwd_(r+d)':>10} {'rev_(r+d)':>10} "
          f"{'delta':>8} {'dir_menor':>10}")
    for r in resultados:
        f = r['forward']['ref'] + r['forward']['dados']
        v = r['reverse']['ref'] + r['reverse']['dados']
        delta = v - f
        sinal = "+" if delta >= 0 else ""
        menor = "forward" if f < v else ("reverse" if v < f else "empate")
        print(f"{r['dataset']:<32} {f:>10} {v:>10} {sinal}{delta:>7} {menor:>10}")

    # Tabela 4: decomposicao completa
    print()
    print("=" * 92)
    print("Tabela 4 — Decomposicao completa (macro / ref / dados)")
    print("-" * 92)
    print(f"{'dataset':<32} {'forward':<24} {'reverse':<24}")
    for r in resultados:
        f_str = f"{r['forward']['macro']:>3} / {r['forward']['ref']:>4} / {r['forward']['dados']:>4}"
        v_str = f"{r['reverse']['macro']:>3} / {r['reverse']['ref']:>4} / {r['reverse']['dados']:>4}"
        print(f"{r['dataset']:<32} {f_str:<24} {v_str:<24}")

    # Arvore + TCF de cada cenario
    for r in resultados:
        print()
        print("=" * 92)
        print(f"Cenario: {r['dataset']}")
        for direcao in ("forward", "reverse"):
            d = r[direcao]
            print("-" * 92)
            print(f"  Direcao: {direcao}")
            print(f"  Arvore:")
            for ln in d["arvore"].splitlines():
                print(f"    {ln}")
            print(f"  TCF:")
            for ln in d["tcf"].splitlines():
                print(f"    {ln}")


if __name__ == "__main__":
    main()
