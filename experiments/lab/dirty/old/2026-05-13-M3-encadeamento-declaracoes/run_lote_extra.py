"""run_lote_extra.py — M3 com datasets enviesados.

Roda em data_extra/ para investigar regime onde encadeamento
poderia compensar (hierarquia profunda) ou nao.

Saidas vao para resultados_extra/ e <micro>/output_extra/,
<micro>/decoded_extra/, <micro>/debug_extra/ (separadas dos
canonicos).
"""

import csv
import sys
from collections import OrderedDict
from pathlib import Path

THIS = Path(__file__).parent
sys.path.insert(0, str(THIS))

from online import processar, reconstroi
from run_lote import (
    _carregar_sintaxe, ler_csv, coletar_quebras_e_frags,
    salvar_tokens, gerar_relatorio,
)

SINTAXES_REGISTRADAS = [
    "M3-A-no-compartilhado",
    "M3-B-encadeamento",
]

DATASETS = [
    "DE7-hierarquia-profunda",
]


def rodar_micro_em_dataset_extra(syn, nome_ds, linhas, unicas, tokens,
                                    frags_por_no, header, micro_dir):
    """Versao para data_extra: escreve em output_extra/, decoded_extra/,
    debug_extra/ para nao misturar com canonicos."""
    output_dir = micro_dir / "output_extra"
    decoded_dir = micro_dir / "decoded_extra"
    debug_dir = micro_dir / "debug_extra"
    output_dir.mkdir(parents=True, exist_ok=True)
    decoded_dir.mkdir(parents=True, exist_ok=True)
    debug_dir.mkdir(parents=True, exist_ok=True)

    try:
        tcf = syn.encode(linhas, unicas, tokens, header)
    except Exception as e:
        (debug_dir / f"{nome_ds}.txt").write_text(
            f"ENCODE FAILED: {e}\n", encoding="utf-8")
        return {"ok": False, "stage": "encode", "err": str(e), "bytes": -1}

    (output_dir / f"{nome_ds}.tcf").write_text(tcf, encoding="utf-8")
    n_bytes = len(tcf.encode("utf-8"))

    try:
        decoded = syn.decode(tcf)
    except Exception as e:
        (debug_dir / f"{nome_ds}.txt").write_text(
            f"DECODE FAILED: {e}\n\nTCF:\n{tcf}\n", encoding="utf-8")
        return {"ok": False, "stage": "decode", "err": str(e),
                "bytes": n_bytes, "tcf": tcf}

    with (decoded_dir / f"{nome_ds}.csv").open(
            "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow([header])
        for line in decoded:
            w.writerow([line])

    rt_ok = decoded == linhas

    debug = []
    debug.append(f"# Debug extra — sintaxe={syn.name} dataset={nome_ds}")
    debug.append(f"# bytes={n_bytes}  roundtrip={'OK' if rt_ok else 'FAIL'}")
    debug.append("")
    debug.append("INPUT:")
    for i, l in enumerate(linhas, 1):
        debug.append(f"  [{i}] {l}")
    debug.append("")
    debug.append("TCF:")
    for line in tcf.splitlines():
        debug.append(f"  {line}")
    debug.append("")
    debug.append("DECODE:")
    for i, line in enumerate(decoded, 1):
        orig = linhas[i - 1] if i - 1 < len(linhas) else "(?)"
        marca = " " if line == orig else "X"
        debug.append(f"  [{marca}] {line}")
    (debug_dir / f"{nome_ds}.txt").write_text(
        "\n".join(debug), encoding="utf-8")
    return {"ok": rt_ok, "stage": "complete", "bytes": n_bytes, "tcf": tcf}


def main():
    base_out = THIS / "resultados_extra"
    base_out.mkdir(exist_ok=True)
    tokens_dir = base_out / "tokens"
    data_dir = THIS / "data_extra"

    print(f"=== run_lote_extra — M3 (datasets enviesados) ===")
    print(f"Sintaxes: {SINTAXES_REGISTRADAS}")
    print(f"Datasets: {DATASETS}")
    print()

    sintaxes_classes = []
    for folder in SINTAXES_REGISTRADAS:
        klass = _carregar_sintaxe(folder)
        sintaxes_classes.append((folder, klass))
    sintaxes_nomes = [k.name for _, k in sintaxes_classes]

    resultados = {}
    for ds in DATASETS:
        print(f"-- {ds} --")
        header, linhas = ler_csv(data_dir / f"{ds}.csv")
        seen = OrderedDict()
        for s in linhas:
            seen[s] = True
        unicas = list(seen.keys())
        tokens, _ = processar(unicas, min_len=3)
        for s, t in zip(unicas, tokens):
            assert reconstroi(t, unicas) == s

        frags_por_no = coletar_quebras_e_frags(unicas, tokens)
        salvar_tokens(ds, unicas, tokens, frags_por_no, tokens_dir)

        for folder, klass in sintaxes_classes:
            syn = klass()
            micro_dir = THIS / folder
            r = rodar_micro_em_dataset_extra(
                syn, ds, linhas, unicas, tokens,
                frags_por_no, header, micro_dir)
            resultados[(syn.name, ds)] = r
            marca = "OK" if r["ok"] else f"FAIL({r['stage']})"
            print(f"  {syn.name:<25} [{marca}] {r.get('bytes', '?')} bytes")
        print()

    gerar_relatorio(resultados, DATASETS, sintaxes_nomes, base_out)
    print(f"Relatorios em: {base_out}/")


if __name__ == "__main__":
    main()
