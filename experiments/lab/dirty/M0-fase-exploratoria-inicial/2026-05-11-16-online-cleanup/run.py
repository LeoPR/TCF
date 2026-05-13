"""Roda exp 16 (cleanup do exp 15) nos 3 datasets.

Objetivo: comportamento byte-identico ao exp 15. Bytes, unidades e
TCFs gerados devem coincidir.
"""

import csv
from collections import OrderedDict
from pathlib import Path

from decode_online import decode_online
from encode_online import encode_online
from online import processar, reconstroi, TokLit, Token

BASE = Path(__file__).parent
DATASETS = ["D2-mini", "D2-completo", "D4"]

# Numeros do exp 15 — exp 16 deve reproduzir exatamente.
EXP15_BYTES = {"D2-mini": 193, "D2-completo": 441, "D4": 399}
EXP15_UNIDADES = {"D2-mini": 47, "D2-completo": 78, "D4": 75}


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
    macro = ref = dados = 0
    for raw in tcf_text.splitlines(keepends=True):
        if raw.strip() in ("<body>", "</body>"):
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


def unidades_de_tokens(tokens_por_string: list[list[Token]]) -> int:
    total = 0
    for tokens in tokens_por_string:
        for tok in tokens:
            if isinstance(tok, TokLit):
                total += len(tok.text)
            else:
                total += 1
    return total


def processar_ds(nome: str) -> dict:
    header, linhas = ler_csv(BASE / "data" / f"{nome}.csv")
    seen = OrderedDict()
    for s in linhas:
        seen[s] = True
    strings_unicas = list(seen.keys())

    tokens_por_str, log_online = processar(strings_unicas, min_len=3)

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
    unidades = unidades_de_tokens(tokens_por_str)

    return {
        "nome": nome,
        "rt_ok": rt_ok,
        "macro": macro, "ref": ref, "dados": dados,
        "ref_dados_bytes": ref + dados,
        "unidades": unidades,
        "tokens_por_str": tokens_por_str,
        "log_online": log_online,
        "tcf": tcf,
    }


def main():
    resultados = [processar_ds(ds) for ds in DATASETS]

    debug_dir = BASE / "debug-output"
    debug_dir.mkdir(exist_ok=True)
    for r in resultados:
        rep = []
        rep.append("=" * 80)
        rep.append(f"DATASET: {r['nome']}")
        rep.append("=" * 80)
        rep.append(r['log_online'])
        rep.append("")
        rep.append(f"TCF ({len(r['tcf'].encode('utf-8'))} bytes):")
        for ln in r['tcf'].splitlines():
            rep.append(f"  {ln}")
        rep.append("")
        rep.append(f"Camadas: macro={r['macro']} ref={r['ref']} dados={r['dados']} "
                   f"(ref+dados={r['ref_dados_bytes']})")
        rep.append(f"Unidades de informacao: {r['unidades']}")
        rep.append(f"Roundtrip: {'OK' if r['rt_ok'] else 'FALHOU'}")
        (debug_dir / f"{r['nome']}.txt").write_text("\n".join(rep), encoding="utf-8")

    print("=" * 96)
    print("exp 16 (cleanup) vs exp 15 — deve coincidir em bytes E unidades")
    print("-" * 96)
    print(f"{'dataset':<16} {'rt':>4} {'bytes_16':>9} {'bytes_15':>9} {'diff':>6}  "
          f"{'unid_16':>8} {'unid_15':>8} {'diff':>6}")
    todos_iguais = True
    for r in resultados:
        b16 = r['ref_dados_bytes']
        b15 = EXP15_BYTES[r['nome']]
        db = b16 - b15
        u16 = r['unidades']
        u15 = EXP15_UNIDADES[r['nome']]
        du = u16 - u15
        if db != 0 or du != 0:
            todos_iguais = False
        print(f"{r['nome']:<16} {'OK' if r['rt_ok'] else 'FAIL':>4} "
              f"{b16:>9} {b15:>9} {db:>+6}  "
              f"{u16:>8} {u15:>8} {du:>+6}")

    print()
    if todos_iguais and all(r['rt_ok'] for r in resultados):
        print("OK: exp 16 reproduz exp 15 byte a byte. Refatoracao sem regressao.")
    else:
        print("ATENCAO: exp 16 divergiu de exp 15. Inspecionar debug-output/.")


if __name__ == "__main__":
    main()
