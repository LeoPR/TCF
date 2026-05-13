"""Roda exp 20 (modularizacao de marcadores) nos 21 datasets do exp 19.

Verifica:
1. TCFs gerados pela `VerboseSyntax` sao byte-identicos aos do exp 16
   (e do exp 19, que coincide com exp 16 nos casos compartilhados).
2. Roundtrip 21/21 OK via decode da mesma sintaxe.
3. Codigo do algoritmo (online.py) nao foi tocado.

A modularizacao em si nao muda numeros — muda a estrutura para
permitir trocar sintaxe sem mexer no algoritmo.
"""

import csv
import time
from collections import OrderedDict
from pathlib import Path

from online import processar, reconstroi, TokLit, Token
from syntax_base import Syntax
from syntax_verbose import VerboseSyntax

BASE = Path(__file__).parent

GRUPO1 = ["D2-mini", "D2-completo", "D4"]
GRUPO2 = ["urls", "uuids", "iso-timestamps", "ips", "cpfs", "codigos"]
GRUPO3 = [f"{fam}-N{n:04d}" for fam in ("urls", "iso", "ips", "codigos")
          for n in (50, 200, 1000)]
TODOS = GRUPO1 + GRUPO2 + GRUPO3

# Referencia: bytes do exp 16 (= exp 19 nos casos compartilhados)
REF_BYTES = {
    "D2-mini": 193, "D2-completo": 441, "D4": 399,
    "urls": 433, "uuids": 563, "iso-timestamps": 380,
    "ips": 304, "cpfs": 291, "codigos": 307,
    "urls-N0050": 1621, "urls-N0200": 6186, "urls-N1000": 31284,
    "iso-N0050": 1861, "iso-N0200": 7039, "iso-N1000": 33566,
    "ips-N0050": 1222, "ips-N0200": 5010, "ips-N1000": 28442,
    "codigos-N0050": 1338, "codigos-N0200": 5650, "codigos-N1000": 29281,
}


def ler_csv(path: Path) -> tuple[str, list[str]]:
    with path.open(encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)[0]
        return header, [r[0] for r in reader if r]


def salvar_csv(path: Path, header: str, linhas: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow([header])
        for v in linhas:
            w.writerow([v])


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
            total += len(tok.text) if isinstance(tok, TokLit) else 1
    return total


def rodar_caso(nome: str, sintaxe: Syntax) -> dict:
    """Roda algoritmo + encode/decode via `sintaxe` para um dataset."""
    path = BASE / "data" / f"{nome}.csv"
    header, linhas = ler_csv(path)
    seen = OrderedDict()
    for s in linhas:
        seen[s] = True
    strings_unicas = list(seen.keys())

    t0 = time.perf_counter()
    tokens_por_str, _log = processar(strings_unicas, min_len=3)
    t_proc = time.perf_counter() - t0

    for s, tokens in zip(strings_unicas, tokens_por_str):
        rec = reconstroi(tokens, strings_unicas)
        assert rec == s, f"reconstroi falhou {nome}: {s!r} -> {rec!r}"

    t0 = time.perf_counter()
    tcf = sintaxe.encode(linhas, strings_unicas, tokens_por_str, header)
    t_enc = time.perf_counter() - t0

    out_dir = BASE / "encoded" / sintaxe.name
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{nome}.tcf").write_text(tcf, encoding="utf-8")

    t0 = time.perf_counter()
    decoded = sintaxe.decode(tcf)
    t_dec = time.perf_counter() - t0

    out_csv = BASE / "decoded" / sintaxe.name
    salvar_csv(out_csv / f"{nome}.csv", header, decoded)
    rt_ok = decoded == linhas

    macro, ref, dados = decompor_camadas(tcf)

    return {
        "nome": nome,
        "rt_ok": rt_ok,
        "n_unicas": len(strings_unicas),
        "bytes": ref + dados,
        "unidades": unidades_de_tokens(tokens_por_str),
        "tcf": tcf,
        "t_proc_ms": t_proc * 1000,
        "t_enc_ms": t_enc * 1000,
        "t_dec_ms": t_dec * 1000,
    }


def main():
    sintaxe = VerboseSyntax()
    print(f"Rodando {len(TODOS)} datasets com sintaxe '{sintaxe.name}'...")

    resultados: dict = {}
    for nome in TODOS:
        r = rodar_caso(nome, sintaxe)
        resultados[nome] = r
        marker = "OK" if r['rt_ok'] else "FAIL"
        print(f"  {nome:<22} {marker:>4}  b={r['bytes']:>6} u={r['unidades']:>5} "
              f"t={r['t_proc_ms']:>7.1f}ms")

    print()
    print("=" * 90)
    print("Paridade vs exp 16 (referencia)")
    print("-" * 90)
    print(f"{'dataset':<22} {'rt':>4} {'bytes':>7} {'ref16':>7} {'diff':>6}")
    todos_iguais = True
    for nome in TODOS:
        r = resultados[nome]
        ref = REF_BYTES[nome]
        diff = r['bytes'] - ref
        if diff != 0:
            todos_iguais = False
        print(f"{nome:<22} {'OK' if r['rt_ok'] else 'FAIL':>4} "
              f"{r['bytes']:>7} {ref:>7} {diff:>+6}")

    falhas = [r for r in resultados.values() if not r['rt_ok']]
    print()
    if todos_iguais and not falhas:
        print(f"OK: VerboseSyntax reproduz exp 16 em {len(TODOS)}/{len(TODOS)} datasets.")
        print("    Algoritmo desacoplado da sintaxe sem regressao.")
    else:
        if falhas:
            print(f"ATENCAO: {len(falhas)} casos com roundtrip FALHANDO:")
            for r in falhas:
                print(f"  {r['nome']}")
        if not todos_iguais:
            print("ATENCAO: bytes divergem do exp 16 em algum dataset.")


if __name__ == "__main__":
    main()
