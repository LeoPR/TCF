"""Roda online sem revisao em 3 datasets, valida roundtrip e
compara com exp 13 (Re-Pair batch).
"""

import csv
from collections import OrderedDict
from pathlib import Path

from decode_online import decode_online
from encode_online import encode_online
from online import processar, reconstroi

BASE = Path(__file__).parent
DATASETS = ["D2-mini", "D2-completo", "D4"]

# Numeros do exp 13 (Re-Pair batch) para comparacao
EXP13_REF_DADOS = {
    "D2-mini": 192,
    "D2-completo": 447,
    "D4": 424,
}
EXP10_REF_DADOS = {
    "D2-completo": 655,
    "D4": 505,
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


def decompor_camadas(tcf_text: str) -> tuple[int, int, int]:
    macro_lines = {"<body>", "</body>"}
    macro = ref = dados = 0
    for raw in tcf_text.splitlines(keepends=True):
        if raw.strip() in macro_lines:
            macro += len(raw)
            continue
        in_quotes = False
        for ch in raw:
            if ch == '"':
                ref += 1
                in_quotes = not in_quotes
            elif in_quotes:
                dados += 1
            else:
                ref += 1
    return macro, ref, dados


def processar_ds(nome: str) -> dict:
    header, linhas = ler_csv(BASE / "data" / f"{nome}.csv")
    seen = OrderedDict()
    for s in linhas:
        seen[s] = True
    strings_unicas = list(seen.keys())

    tokens_por_str, log_online = processar(strings_unicas, min_len=3)

    # Sanidade
    for s, tokens in zip(strings_unicas, tokens_por_str):
        rec = reconstroi(tokens, strings_unicas)
        assert rec == s, f"reconstroi falhou: {s!r} -> {rec!r}"

    tcf = encode_online(linhas, strings_unicas, tokens_por_str, header)
    (BASE / "encoded").mkdir(exist_ok=True)
    (BASE / "encoded" / f"{nome}.tcf").write_text(tcf, encoding="utf-8")

    decoded = decode_online(tcf)
    salvar_csv(BASE / "decoded" / f"{nome}.csv", header, decoded)
    rt_ok = decoded == linhas

    macro, ref, dados = decompor_camadas(tcf)

    # Relatorio textual
    rep: list[str] = []
    rep.append("=" * 80)
    rep.append(f"DATASET: {nome}")
    rep.append("=" * 80)
    rep.append(f"linhas: {len(linhas)}  unicas: {len(strings_unicas)}")
    rep.append("")
    rep.append("LOG ONLINE:")
    for ln in log_online.splitlines():
        rep.append(f"  {ln}")
    rep.append("")
    rep.append(f"TCF ({len(tcf.encode('utf-8'))} bytes):")
    for ln in tcf.splitlines():
        rep.append(f"  {ln}")
    rep.append("")
    rep.append(f"Decomposicao: macro={macro} ref={ref} dados={dados} "
               f"(ref+dados={ref+dados})")
    rep.append(f"Roundtrip: {'OK' if rt_ok else 'FALHOU'}")

    return {
        "nome": nome,
        "rt_ok": rt_ok,
        "macro": macro, "ref": ref, "dados": dados,
        "ref_dados": ref + dados,
        "relatorio": "\n".join(rep),
    }


def main():
    resultados = []
    debug_dir = BASE / "debug-output"
    debug_dir.mkdir(exist_ok=True)
    for ds in DATASETS:
        r = processar_ds(ds)
        (debug_dir / f"{ds}.txt").write_text(r["relatorio"], encoding="utf-8")
        resultados.append(r)

    print("=" * 92)
    print("Tabela consolidada — online sem revisao (exp 14) vs Re-Pair (exp 13)")
    print("-" * 92)
    print(f"{'dataset':<16} {'rt':>4} {'macro':>5} {'ref':>5} {'dados':>5} "
          f"{'ref+dados':>9} {'exp13':>6} {'delta':>7} {'exp10':>6}")
    for r in resultados:
        v13 = EXP13_REF_DADOS.get(r['nome'], 0)
        delta_13 = r['ref_dados'] - v13 if v13 else 0
        v10 = EXP10_REF_DADOS.get(r['nome'], '—')
        sinal = "+" if delta_13 >= 0 else ""
        print(f"{r['nome']:<16} {'OK' if r['rt_ok'] else 'FAIL':>4} "
              f"{r['macro']:>5} {r['ref']:>5} {r['dados']:>5} "
              f"{r['ref_dados']:>9} {v13:>6} {sinal}{delta_13:>6} "
              f"{v10:>6}")
    print()
    print("delta positivo = exp 14 maior (perdeu para Re-Pair)")
    print("Detalhes em debug-output/")


if __name__ == "__main__":
    main()
