"""Roda 4 datasets x 4 ordenacoes = 16 cenarios em ambas as serializacoes.

Para cada cenario:
  - constroi arvore Patricia (mesmo algoritmo dos exps 02/03)
  - encoda em separado e em inline (formatos normalizados)
  - decodifica e valida roundtrip
  - mede tamanho real e decompoe em (macro, ref, dados)
  - calcula previsao simbolica
  - compara medida vs previsao

Imprime tabela final consolidada.
"""

import csv
from pathlib import Path

from decode_inline import decode_inline
from decode_separado import decode_separado
from encode_inline import encode_inline
from encode_separado import encode_separado
from formula import decompor, prever_inline, prever_separado
from patricia import aplicar_patricia, construir_inicial, rle_adjacente

BASE = Path(__file__).parent

DATASETS = [
    "D1-baixa-card-sem-patricia",
    "D2-alta-card-sem-patricia",
    "D3-baixa-card-com-patricia",
    "D4-alta-card-com-patricia",
]
ORDENACOES = ["original", "sorted", "random", "agrupado"]


def ler_csv(path: Path) -> tuple[str, list[str]]:
    with path.open(encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)[0]
        return header, [r[0] for r in reader if r]


def processar(dataset: str, ordenacao: str) -> dict:
    input_path = BASE / "data" / dataset / f"{ordenacao}.csv"
    header, linhas = ler_csv(input_path)

    nos, body = construir_inicial(linhas)
    nos = aplicar_patricia(nos)
    body_rle = rle_adjacente(body)

    tcf_sep = encode_separado(nos, body_rle, header)
    tcf_inl = encode_inline(nos, body_rle, header)

    (BASE / "encoded").mkdir(exist_ok=True)
    (BASE / "encoded" / f"{dataset}-{ordenacao}-separado.tcf").write_text(
        tcf_sep, encoding="utf-8")
    (BASE / "encoded" / f"{dataset}-{ordenacao}-inline.tcf").write_text(
        tcf_inl, encoding="utf-8")

    rt_sep = decode_separado(tcf_sep) == linhas
    rt_inl = decode_inline(tcf_inl) == linhas

    sep_macro, sep_ref, sep_dados = decompor(tcf_sep)
    inl_macro, inl_ref, inl_dados = decompor(tcf_inl)

    pred_sep_macro, pred_sep_ref, pred_sep_dados = prever_separado(nos, body_rle)
    pred_inl_macro, pred_inl_ref, pred_inl_dados = prever_inline(nos, body_rle)

    nos_com_ocorrencia = {nid for nid, _ in body_rle}
    n_unicas = len(nos_com_ocorrencia)
    n_pat_int = len(nos) - n_unicas

    return {
        "dataset": dataset,
        "ordenacao": ordenacao,
        "n_total": len(linhas),
        "n_unicas": n_unicas,
        "n_pat_int": n_pat_int,
        "n_body_rle": len(body_rle),
        "rt_sep": rt_sep,
        "rt_inl": rt_inl,
        "sep_total": len(tcf_sep.encode("utf-8")),
        "inl_total": len(tcf_inl.encode("utf-8")),
        "sep_macro": sep_macro, "sep_ref": sep_ref, "sep_dados": sep_dados,
        "inl_macro": inl_macro, "inl_ref": inl_ref, "inl_dados": inl_dados,
        "pred_sep_macro": pred_sep_macro,
        "pred_sep_ref": pred_sep_ref,
        "pred_sep_dados": pred_sep_dados,
        "pred_inl_macro": pred_inl_macro,
        "pred_inl_ref": pred_inl_ref,
        "pred_inl_dados": pred_inl_dados,
    }


def main():
    resultados = []
    for ds in DATASETS:
        for ord_ in ORDENACOES:
            resultados.append(processar(ds, ord_))

    # Tabela 1: contagens + roundtrip
    print("=" * 92)
    print("Tabela 1 — Estrutura e roundtrip")
    print("-" * 92)
    print(f"{'cenario':<40} {'N_tot':>5} {'N_uniq':>6} {'N_int':>5} "
          f"{'body_RLE':>8} {'rt_sep':>6} {'rt_inl':>6}")
    for r in resultados:
        nome = f"{r['dataset']}/{r['ordenacao']}"
        print(f"{nome:<40} {r['n_total']:>5} {r['n_unicas']:>6} "
              f"{r['n_pat_int']:>5} {r['n_body_rle']:>8} "
              f"{'OK' if r['rt_sep'] else 'FAIL':>6} "
              f"{'OK' if r['rt_inl'] else 'FAIL':>6}")

    # Tabela 2: previsto vs medido (valida formula)
    print()
    print("=" * 92)
    print("Tabela 2 — Previsao simbolica vs medicao real (deve bater 100%)")
    print("-" * 92)
    print(f"{'cenario':<40} {'sep_med':>8} {'sep_pred':>8} {'inl_med':>8} "
          f"{'inl_pred':>8} {'match':>6}")
    todos_batem = True
    for r in resultados:
        nome = f"{r['dataset']}/{r['ordenacao']}"
        sep_pred = r['pred_sep_macro'] + r['pred_sep_ref'] + r['pred_sep_dados']
        inl_pred = r['pred_inl_macro'] + r['pred_inl_ref'] + r['pred_inl_dados']
        match = (sep_pred == r['sep_total']) and (inl_pred == r['inl_total'])
        todos_batem = todos_batem and match
        print(f"{nome:<40} {r['sep_total']:>8} {sep_pred:>8} "
              f"{r['inl_total']:>8} {inl_pred:>8} "
              f"{'OK' if match else 'DIFF':>6}")
    print(f"\nFormula consistente em todos os 16 cenarios: "
          f"{'sim' if todos_batem else 'NAO'}")

    # Tabela 3: decomposicao por camada
    print()
    print("=" * 92)
    print("Tabela 3 — Decomposicao por camada (bytes)")
    print("-" * 92)
    print(f"{'cenario':<40} | {'sep: macro / ref / dados':<28} | "
          f"{'inl: macro / ref / dados':<28}")
    print("-" * 92)
    for r in resultados:
        nome = f"{r['dataset']}/{r['ordenacao']}"
        sep_str = f"{r['sep_macro']:>4} / {r['sep_ref']:>4} / {r['sep_dados']:>4}"
        inl_str = f"{r['inl_macro']:>4} / {r['inl_ref']:>4} / {r['inl_dados']:>4}"
        print(f"{nome:<40} | {sep_str:<28} | {inl_str:<28}")

    # Tabela 4: diferenca apenas em camada de marcadores de ref (mais relevante)
    print()
    print("=" * 92)
    print("Tabela 4 — Camada 2 (marcadores de ref): inline vs separado")
    print("-" * 92)
    print(f"{'cenario':<40} {'sep_ref':>8} {'inl_ref':>8} "
          f"{'delta':>7} {'pct':>7}")
    for r in resultados:
        nome = f"{r['dataset']}/{r['ordenacao']}"
        delta = r['inl_ref'] - r['sep_ref']
        pct = 100 * delta / r['sep_ref'] if r['sep_ref'] > 0 else 0
        sinal = "+" if delta >= 0 else ""
        print(f"{nome:<40} {r['sep_ref']:>8} {r['inl_ref']:>8} "
              f"{sinal}{delta:>6} {sinal}{pct:>5.1f}%")

    print()
    print("=" * 92)


if __name__ == "__main__":
    main()
