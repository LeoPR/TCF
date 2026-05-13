"""Roda Re-Pair em 3 datasets, valida roundtrip, gera debug + TCF."""

import csv
from collections import OrderedDict
from pathlib import Path

from decode_repair import decode_repair
from encode_repair import encode_repair
from repair import reconstroi, repair

BASE = Path(__file__).parent
DATASETS = ["D2-mini", "D2-completo", "D4"]


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


def decompor_str_em_camadas(tcf_text: str) -> tuple[int, int, int]:
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


def processar(nome: str) -> dict:
    header, linhas = ler_csv(BASE / "data" / f"{nome}.csv")
    seen = OrderedDict()
    for s in linhas:
        seen[s] = True
    strings_unicas = list(seen.keys())

    simbolos, strings_tok, log_repair = repair(strings_unicas,
                                                min_len=3, min_count=2)

    # Sanidade: reconstroi cada string
    for s, tokens in zip(strings_unicas, strings_tok):
        rec = reconstroi(tokens, simbolos)
        assert rec == s, f"reconstroi falhou: {s!r} -> {rec!r}"

    tcf = encode_repair(linhas, strings_unicas, strings_tok, simbolos, header)
    (BASE / "encoded").mkdir(exist_ok=True)
    (BASE / "encoded" / f"{nome}.tcf").write_text(tcf, encoding="utf-8")

    decoded = decode_repair(tcf)
    salvar_csv(BASE / "decoded" / f"{nome}.csv", header, decoded)
    rt_ok = decoded == linhas

    macro, ref, dados = decompor_str_em_camadas(tcf)

    # Relatorio textual
    rep: list[str] = []
    rep.append("=" * 80)
    rep.append(f"DATASET: {nome}")
    rep.append("=" * 80)
    rep.append(f"linhas: {len(linhas)}  unicas: {len(strings_unicas)}")
    rep.append("")
    rep.append("LOG REPAIR:")
    for ln in log_repair.splitlines():
        rep.append(f"  {ln}")
    rep.append("")
    rep.append("SIMBOLOS FINAIS:")
    for sid, txt in simbolos.items():
        rep.append(f"  S{sid} = {txt!r}")
    rep.append("")
    rep.append("STRINGS UNICAS APOS REPAIR:")
    for s, tokens in zip(strings_unicas, strings_tok):
        tok_str = " + ".join(repr(t) for t in tokens)
        rep.append(f"  {s!r:<40} -> [{tok_str}]")
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
        "total": len(tcf.encode("utf-8")),
        "macro": macro,
        "ref": ref,
        "dados": dados,
        "ref_dados": ref + dados,
        "n_simbolos": len(simbolos),
        "relatorio": "\n".join(rep),
    }


# Numeros do exp 10 para referencia
EXP10_REF_DADOS = {
    "D2-completo": 655,
    "D4": 505,
}


def main():
    resultados = []
    debug_dir = BASE / "debug-output"
    debug_dir.mkdir(exist_ok=True)
    for ds in DATASETS:
        r = processar(ds)
        (debug_dir / f"{ds}.txt").write_text(r["relatorio"], encoding="utf-8")
        resultados.append(r)

    print("=" * 84)
    print("Tabela consolidada — Re-Pair (exp 13)")
    print("-" * 84)
    print(f"{'dataset':<16} {'rt':>4} {'simbolos':>9} {'macro':>5} "
          f"{'ref':>5} {'dados':>5} {'ref+dados':>9} {'exp10':>6}")
    for r in resultados:
        exp10 = EXP10_REF_DADOS.get(r['nome'], '—')
        print(f"{r['nome']:<16} "
              f"{'OK' if r['rt_ok'] else 'FAIL':>4} "
              f"{r['n_simbolos']:>9} {r['macro']:>5} {r['ref']:>5} "
              f"{r['dados']:>5} {r['ref_dados']:>9} {exp10:>6}")
    print()
    print("Detalhes em debug-output/")


if __name__ == "__main__":
    main()
