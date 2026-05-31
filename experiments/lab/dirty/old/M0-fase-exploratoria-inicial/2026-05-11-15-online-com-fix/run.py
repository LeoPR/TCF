"""Roda online com fix (exp 15) nos 3 datasets, valida roundtrip,
e compara com exp 13 (Re-Pair) e exp 14 (online sem fix) sob 2
metricas: bytes literais e unidades de informacao.
"""

import csv
from collections import OrderedDict
from pathlib import Path

from decode_online import decode_online
from encode_online import encode_online
from online import processar, reconstroi, TokLit, TokRefPref, TokRefSuf, Token

BASE = Path(__file__).parent
DATASETS = ["D2-mini", "D2-completo", "D4"]

EXP13_BYTES = {"D2-mini": 192, "D2-completo": 447, "D4": 424}
EXP14_BYTES = {"D2-mini": 198, "D2-completo": 463, "D4": 399}

# Unidades de exp 13 (Re-Pair) — calculadas a mao com base no debug do exp 13
# Cada simbolo declarado = len(text) + 1 (id)
# Cada string: tokens (refs = 1u cada, lit = len(text)u)
# D2-mini exp 13:
#   simbolos: S1="maria.silva@" (12+1=13), S2="joao.souza@" (11+1=12),
#             S3="mail.com" (8+1=9) = 34
#   s1: R1+L("g")+R3 = 1+1+1 = 3
#   s2: R1+L("hot")+R3 = 1+3+1 = 5
#   s3: R1+L("yahoo.com") = 1+9 = 10
#   s4: R2+L("g")+R3 = 3
#   s5: R2+L("hot")+R3 = 5
#   s6: R2+L("yahoo.com") = 10
#   total: 34 + 36 = 70
EXP13_UNIDADES = {"D2-mini": 70, "D2-completo": 124, "D4": 105}
# Recalculado manualmente do TCF do exp 13:
# D2-completo: 55 (simbolos 9+11+12+12+11) + 69 (strings) = 124
# D4:          49 (simbolos 28+10+11) + 56 (strings)      = 105


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
    """Cada ref = 1 unidade. Cada char literal = 1 unidade.
    A primeira string vira TokLit(s) inteiro — len(s) unidades.
    Strings subsequentes contam refs + literais.
    """
    total = 0
    for tokens in tokens_por_string:
        for tok in tokens:
            if isinstance(tok, TokLit):
                total += len(tok.text)
            else:  # ref
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
        (debug_dir / f"{r['nome']}.txt").write_text("\n".join(rep),
                                                     encoding="utf-8")

    print("=" * 96)
    print("Tabela 1 — Bytes literais (ref+dados): exp 15 vs exp 14 vs exp 13")
    print("-" * 96)
    print(f"{'dataset':<16} {'rt':>4} {'exp13':>6} {'exp14':>6} {'exp15':>6} "
          f"{'d_v14':>6} {'d_v13':>6}")
    for r in resultados:
        v15 = r['ref_dados_bytes']
        v14 = EXP14_BYTES[r['nome']]
        v13 = EXP13_BYTES[r['nome']]
        d14 = v15 - v14
        d13 = v15 - v13
        print(f"{r['nome']:<16} {'OK' if r['rt_ok'] else 'FAIL':>4} "
              f"{v13:>6} {v14:>6} {v15:>6} "
              f"{d14:>+6} {d13:>+6}")

    print()
    print("=" * 96)
    print("Tabela 2 — Unidades de informacao: exp 15 vs exp 13 (Re-Pair)")
    print("-" * 96)
    print(f"{'dataset':<16} {'exp13_u':>8} {'exp15_u':>8} {'delta':>7}")
    for r in resultados:
        u15 = r['unidades']
        u13 = EXP13_UNIDADES.get(r['nome'], 0)
        delta = u15 - u13 if u13 else 0
        sinal = "+" if delta >= 0 else ""
        print(f"{r['nome']:<16} {u13:>8} {u15:>8} {sinal}{delta:>6}")
    print()
    print("Unidade: 1 ref = 1 unidade; 1 char literal = 1 unidade.")
    print("Em exp 13 (Re-Pair) inclui declaracoes de simbolos (len+1 cada).")
    print("Em exp 15 (online) inclui literal completo da 1a string.")


if __name__ == "__main__":
    main()
