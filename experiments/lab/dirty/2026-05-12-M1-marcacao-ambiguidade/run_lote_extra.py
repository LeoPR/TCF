"""run_lote_extra.py — Stress-test extra (rodada 1) para M1.E e M1.C.

DATASETS DESCARTAVEIS em `data_extra/`:
  - DE1-adversarial-E: pouca seq, K=2 dominante (range nao ajuda)
  - DE2-favoravel-E:  1-char-diff em N posicoes (refs K=7+ sequenciais)
  - DE3-adversarial-C: literais puros sempre apos ref (forca `*` sep)
  - DE4-favoravel-C: literais puros no inicio de linha (sem `*` sep)

Roda as 5 sintaxes (A, A', B, E, C) e gera matriz separada em
`resultados_extra/`. NAO afeta `resultados/` canonicos.

Apos analise: se algo escapa, anotar pra eventualmente adicionar
linhas selecionadas aos datasets D1-D4 canonicos. Esta pasta
`data_extra/` e' efemera.
"""

import csv
import importlib.util
import sys
from collections import OrderedDict
from pathlib import Path

THIS = Path(__file__).parent
sys.path.insert(0, str(THIS))

from online import processar, reconstroi, TokLit, TokRefPref, TokRefSuf
from run_lote import (
    _carregar_sintaxe, ler_csv, coletar_quebras_e_frags,
    salvar_tokens, rodar_sintaxe_em_dataset, gerar_relatorio,
)

SINTAXES_REGISTRADAS = [
    "M1-A-escape",
    "M1-A-escape-escopo",
    "M1-B-quote",
    "M1-E-range",
    "M1-C-sumida",
]

DATASETS = [
    "DE1-adversarial-E",
    "DE2-favoravel-E",
    "DE3-adversarial-C",
    "DE4-favoravel-C",
]


def main():
    base_out = THIS / "resultados_extra"
    base_out.mkdir(exist_ok=True)
    tokens_dir = base_out / "tokens"
    data_dir = THIS / "data_extra"

    print(f"=== run_lote_extra — M1 stress-test rodada 1 ===")
    print(f"Sintaxes: {SINTAXES_REGISTRADAS}")
    print(f"Datasets: {DATASETS}")
    print(f"Origem: {data_dir}")
    print()

    sintaxes_classes = []
    for folder in SINTAXES_REGISTRADAS:
        klass = _carregar_sintaxe(folder)
        sintaxes_classes.append((folder, klass))
        print(f"  [carregada] {folder} -> {klass.__name__}")
    print()

    resultados = {}
    sintaxes_nomes = [k.name for _, k in sintaxes_classes]

    for ds in DATASETS:
        print(f"-- dataset {ds} --")
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

        for _, klass in sintaxes_classes:
            syn = klass()
            out_dir = base_out / syn.name
            r = rodar_sintaxe_em_dataset(
                syn, ds, linhas, unicas, tokens,
                frags_por_no, header, out_dir)
            resultados[(syn.name, ds)] = r
            marca = "OK" if r["ok"] else f"FAIL({r['stage']})"
            print(f"  {syn.name:<22} [{marca}] {r.get('bytes', '?')} bytes")
        print()

    gerar_relatorio(resultados, DATASETS, sintaxes_nomes, base_out)
    print(f"Relatorios em: {base_out}/")
    print(f"  - matriz_comparativa.md")
    print(f"  - matriz_bytes.csv")


if __name__ == "__main__":
    main()
