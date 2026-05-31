"""run_lote_f2.py — Fase F2 do macro M1.

Mede 6+3 dimensoes por (sintaxe x dataset canonico):

Quantitativas (medidas):
1. Bytes UTF-8 (len(tcf.encode('utf-8')))
2. Bytes pos-gzip (gzip nivel 9)
3. Bytes pos-bz2 (bz2 nivel 9)
4. Razao gzip (= 2/1)
5. Tempo encode (microsegundos, mediana de 1000 iters)
6. Tempo decode (microsegundos, mediana de 1000 iters)

Qualitativas (de f2_propriedades.py):
7. Stateful encoder/decoder + grau
8. Lookahead encode/decode
9. Complexidade encode/decode + latencia incremental

Saidas em `resultados_f2/`:
- matriz_f2.md (relatorio markdown com todas dimensoes)
- matriz_f2.csv (dados crus para analise externa)
- detalhes_qualitativos.md (descricoes das propriedades)
"""

import bz2
import csv
import gzip
import statistics
import sys
import time
from collections import OrderedDict
from pathlib import Path

THIS = Path(__file__).parent
sys.path.insert(0, str(THIS))

from online import processar, reconstroi
from run_lote import (
    _carregar_sintaxe, ler_csv, coletar_quebras_e_frags,
)
from f2_propriedades import PROPRIEDADES

SINTAXES_REGISTRADAS = [
    "M1-A-escape",
    "M1-A-escape-escopo",
    "M1-B-quote",
    "M1-E-range",
    "M1-C-sumida",
    "M1-D-slice",
]

DATASETS = [
    "D1-emails-simples",
    "D2-emails-quote-id",
    "D3-stress-substring",
    "D4-caos-mix",
]

ITERACOES_TIMING = 1000


def medir_tempo(callable_fn, n_iters=ITERACOES_TIMING):
    """Mede tempo em microsegundos. Retorna (mediana, p95, std)."""
    tempos = []
    for _ in range(n_iters):
        t0 = time.perf_counter()
        callable_fn()
        t1 = time.perf_counter()
        tempos.append((t1 - t0) * 1_000_000)  # us
    tempos.sort()
    mediana = statistics.median(tempos)
    p95 = tempos[int(n_iters * 0.95)]
    std = statistics.stdev(tempos) if len(tempos) > 1 else 0.0
    return mediana, p95, std


def medir_celula(syn, linhas, unicas, tokens, header):
    """Mede tudo para 1 (sintaxe x dataset). Retorna dict."""
    # encode 1x para pegar tcf de referencia
    tcf = syn.encode(linhas, unicas, tokens, header)
    tcf_bytes = tcf.encode("utf-8")

    bytes_utf8 = len(tcf_bytes)
    bytes_gzip = len(gzip.compress(tcf_bytes, compresslevel=9))
    bytes_bz2 = len(bz2.compress(tcf_bytes, compresslevel=9))
    razao_gzip = bytes_gzip / bytes_utf8 if bytes_utf8 > 0 else 0

    # timings
    enc_med, enc_p95, enc_std = medir_tempo(
        lambda: syn.encode(linhas, unicas, tokens, header))
    dec_med, dec_p95, dec_std = medir_tempo(
        lambda: syn.decode(tcf))

    # validacao roundtrip (1x)
    decoded = syn.decode(tcf)
    rt_ok = decoded == linhas

    return {
        "ok": rt_ok,
        "bytes_utf8": bytes_utf8,
        "bytes_gzip": bytes_gzip,
        "bytes_bz2": bytes_bz2,
        "razao_gzip": razao_gzip,
        "enc_us_mediana": enc_med,
        "enc_us_p95": enc_p95,
        "enc_us_std": enc_std,
        "dec_us_mediana": dec_med,
        "dec_us_p95": dec_p95,
        "dec_us_std": dec_std,
    }


def gerar_matriz_md(resultados, datasets, sintaxes, out_path):
    md = []
    md.append("# F2 — Matriz consolidada (M1)")
    md.append("")
    md.append(f"Sintaxes: {', '.join(sintaxes)}")
    md.append(f"Datasets: {', '.join(datasets)}")
    md.append(f"Iteracoes para timing: {ITERACOES_TIMING}")
    md.append("")
    md.append("## Bytes UTF-8 (literais)")
    md.append("")
    md.append(_tabela_metric(resultados, datasets, sintaxes,
                              "bytes_utf8", "d"))
    md.append("")
    md.append("## Bytes pos-gzip (nivel 9)")
    md.append("")
    md.append(_tabela_metric(resultados, datasets, sintaxes,
                              "bytes_gzip", "d"))
    md.append("")
    md.append("## Bytes pos-bz2 (nivel 9)")
    md.append("")
    md.append(_tabela_metric(resultados, datasets, sintaxes,
                              "bytes_bz2", "d"))
    md.append("")
    md.append("## Razao gzip (gzip/utf8) — quanto menor = ja' mais comprimido")
    md.append("")
    md.append(_tabela_metric(resultados, datasets, sintaxes,
                              "razao_gzip", ".3f"))
    md.append("")
    md.append("## Tempo encode (microsegundos, mediana)")
    md.append("")
    md.append(_tabela_metric(resultados, datasets, sintaxes,
                              "enc_us_mediana", ".1f"))
    md.append("")
    md.append("## Tempo decode (microsegundos, mediana)")
    md.append("")
    md.append(_tabela_metric(resultados, datasets, sintaxes,
                              "dec_us_mediana", ".1f"))
    md.append("")
    md.append("## Tempo encode p95 (microsegundos)")
    md.append("")
    md.append(_tabela_metric(resultados, datasets, sintaxes,
                              "enc_us_p95", ".1f"))
    md.append("")
    md.append("## Tempo decode p95 (microsegundos)")
    md.append("")
    md.append(_tabela_metric(resultados, datasets, sintaxes,
                              "dec_us_p95", ".1f"))
    md.append("")

    # Propriedades qualitativas
    md.append("## Propriedades qualitativas")
    md.append("")
    md.append("| Sintaxe | Encoder | Decoder | Lookahead enc | Lookahead dec |")
    md.append("|---|---|---|---|---|")
    for sn in sintaxes:
        p = PROPRIEDADES[sn]
        md.append(f"| {sn} | {p['encoder_stateful']} ({p['encoder_stateful_grau']}) "
                  f"| {p['decoder_stateful']} ({p['decoder_stateful_grau']}) "
                  f"| {p['lookahead_encode']} | {p['lookahead_decode']} |")
    md.append("")

    md.append("## Complexidade algoritmica")
    md.append("")
    md.append("| Sintaxe | Encode | Decode | Latencia incremental |")
    md.append("|---|---|---|---|")
    for sn in sintaxes:
        p = PROPRIEDADES[sn]
        md.append(f"| {sn} | {p['complexidade_encode_no']} "
                  f"| {p['complexidade_decode_no']} "
                  f"| {p['latencia_incremental']} |")
    md.append("")

    md.append("## Notas por sintaxe")
    md.append("")
    for sn in sintaxes:
        p = PROPRIEDADES[sn]
        md.append(f"- **{sn}**: {p['notas']}")
    md.append("")

    out_path.write_text("\n".join(md), encoding="utf-8")


def _tabela_metric(resultados, datasets, sintaxes, metric, fmt):
    out = []
    out.append("| dataset | " + " | ".join(sintaxes) + " |")
    out.append("|" + "|".join("---" for _ in range(len(sintaxes) + 1)) + "|")
    for ds in datasets:
        row = [ds]
        valores = {}
        for sn in sintaxes:
            r = resultados[(sn, ds)]
            if r["ok"]:
                v = r[metric]
                valores[sn] = v
                row.append(f"{v:{fmt}}")
            else:
                row.append("X")
        # destacar vencedor (menor) com bold
        if valores:
            vencedor_v = min(valores.values())
            for i, sn in enumerate(sintaxes):
                if sn in valores and valores[sn] == vencedor_v:
                    # idx i+1 (offset dataset)
                    row[i + 1] = f"**{row[i + 1]}**"
        out.append("| " + " | ".join(row) + " |")
    # linha total
    row = ["**TOTAL**"]
    totais = {sn: 0 for sn in sintaxes}
    counts = {sn: 0 for sn in sintaxes}
    for ds in datasets:
        for sn in sintaxes:
            r = resultados[(sn, ds)]
            if r["ok"]:
                totais[sn] += r[metric]
                counts[sn] += 1
    for sn in sintaxes:
        if counts[sn] > 0:
            row.append(f"**{totais[sn]:{fmt}}**")
        else:
            row.append("X")
    out.append("| " + " | ".join(row) + " |")
    return "\n".join(out)


def gerar_csv(resultados, datasets, sintaxes, out_path):
    cols = ["dataset", "sintaxe", "ok", "bytes_utf8", "bytes_gzip",
            "bytes_bz2", "razao_gzip", "enc_us_mediana", "enc_us_p95",
            "enc_us_std", "dec_us_mediana", "dec_us_p95", "dec_us_std"]
    with out_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for ds in datasets:
            for sn in sintaxes:
                r = resultados[(sn, ds)]
                row = [ds, sn, "OK" if r["ok"] else "FAIL"]
                for c in cols[3:]:
                    row.append(f"{r[c]:.4f}" if isinstance(r[c], float)
                                else r[c])
                w.writerow(row)


def main():
    base_out = THIS / "resultados_f2"
    base_out.mkdir(exist_ok=True)

    print(f"=== F2 — Fase 2 do macro M1 ===")
    print(f"Sintaxes: {SINTAXES_REGISTRADAS}")
    print(f"Datasets canonicos: {DATASETS}")
    print(f"Timing iterations: {ITERACOES_TIMING}")
    print()

    sintaxes_classes = []
    for folder in SINTAXES_REGISTRADAS:
        klass = _carregar_sintaxe(folder)
        sintaxes_classes.append((folder, klass))
    sintaxes_nomes = [k.name for _, k in sintaxes_classes]

    resultados = {}

    for ds in DATASETS:
        print(f"-- {ds} --")
        header, linhas = ler_csv(THIS / "data" / f"{ds}.csv")
        seen = OrderedDict()
        for s in linhas:
            seen[s] = True
        unicas = list(seen.keys())
        tokens, _ = processar(unicas, min_len=3)
        for s, t in zip(unicas, tokens):
            assert reconstroi(t, unicas) == s

        for _, klass in sintaxes_classes:
            syn = klass()
            r = medir_celula(syn, linhas, unicas, tokens, header)
            resultados[(syn.name, ds)] = r
            marca = "OK" if r["ok"] else "FAIL"
            print(f"  {syn.name:<22} [{marca}] "
                  f"utf8={r['bytes_utf8']:>4} gzip={r['bytes_gzip']:>4} "
                  f"bz2={r['bytes_bz2']:>4} "
                  f"enc={r['enc_us_mediana']:>6.1f}us "
                  f"dec={r['dec_us_mediana']:>6.1f}us")
        print()

    gerar_matriz_md(resultados, DATASETS, sintaxes_nomes,
                     base_out / "matriz_f2.md")
    gerar_csv(resultados, DATASETS, sintaxes_nomes,
               base_out / "matriz_f2.csv")
    print(f"Saidas em: {base_out}/")
    print(f"  - matriz_f2.md")
    print(f"  - matriz_f2.csv")


if __name__ == "__main__":
    main()
