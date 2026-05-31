"""Roda exp 19 (par A+B independente) e compara com exp 16 em 3 grupos:
  G1: 3 datasets do exp 15 (D2-mini, D2-completo, D4)
  G2: 6 familias do exp 17 (urls, uuids, iso, ips, cpfs, codigos)
  G3: 4 familias x 3 tamanhos do exp 18 (N=50, 200, 1000)

Mede: bytes, unidades, cobertura, tempo. Compara delta vs exp 16
(que ja era equivalente a exp 15 nos casos coincidentes).
"""

import csv
import time
from collections import OrderedDict
from pathlib import Path

from decode_online import decode_online
from encode_online import encode_online
from online import processar, reconstroi, TokLit, TokRefPref, TokRefSuf, Token

BASE = Path(__file__).parent

# Numeros do exp 16 (= exp 15 nos 3 primeiros, = exp 17 nos 6 seguintes,
# = exp 18 nos 12 ultimos)
EXP16 = {
    "D2-mini":         {"bytes": 193, "unid": 47},
    "D2-completo":     {"bytes": 441, "unid": 78},
    "D4":              {"bytes": 399, "unid": 75},
    "urls":            {"bytes": 433, "unid": 128, "cob": 80.6},
    "uuids":           {"bytes": 563, "unid": 430, "cob": 0.7},
    "iso-timestamps":  {"bytes": 380, "unid": 49,  "cob": 88.8},
    "ips":             {"bytes": 304, "unid": 52,  "cob": 72.0},
    "cpfs":            {"bytes": 291, "unid": 168, "cob": 0.0},
    "codigos":         {"bytes": 307, "unid": 38,  "cob": 86.9},
    "urls-N0050":      {"bytes": 1621,  "unid": 228,  "cob": 93.9},
    "urls-N0200":      {"bytes": 6186,  "unid": 553,  "cob": 97.7},
    "urls-N1000":      {"bytes": 31284, "unid": 2255, "cob": 98.8},
    "iso-N0050":       {"bytes": 1861,  "unid": 269,  "cob": 82.9},
    "iso-N0200":       {"bytes": 7039,  "unid": 648,  "cob": 93.8},
    "iso-N1000":       {"bytes": 33566, "unid": 2264, "cob": 98.7},
    "ips-N0050":       {"bytes": 1222,  "unid": 184,  "cob": 75.8},
    "ips-N0200":       {"bytes": 5010,  "unid": 553,  "cob": 84.4},
    "ips-N1000":       {"bytes": 28442, "unid": 2092, "cob": 96.3},
    "codigos-N0050":   {"bytes": 1338,  "unid": 119,  "cob": 93.3},
    "codigos-N0200":   {"bytes": 5650,  "unid": 427,  "cob": 95.4},
    "codigos-N1000":   {"bytes": 29281, "unid": 2067, "cob": 95.9},
}

GRUPO1 = ["D2-mini", "D2-completo", "D4"]
GRUPO2 = ["urls", "uuids", "iso-timestamps", "ips", "cpfs", "codigos"]
GRUPO3 = [f"{fam}-N{n:04d}" for fam in ("urls", "iso", "ips", "codigos")
          for n in (50, 200, 1000)]


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


def cobertura_pct(tokens_por_string: list[list[Token]],
                   strings_unicas: list[str]) -> float:
    chars_lit = chars_tot = 0
    for idx, tokens in enumerate(tokens_por_string):
        s = strings_unicas[idx]
        chars_tot += len(s)
        chars_lit += sum(len(t.text) for t in tokens if isinstance(t, TokLit))
    return (1 - chars_lit / chars_tot) * 100 if chars_tot else 0


def processar_ds(nome: str) -> dict:
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
        assert rec == s, f"reconstroi falhou em {nome}: {s!r} -> {rec!r}"

    tcf = encode_online(linhas, strings_unicas, tokens_por_str, header)
    (BASE / "encoded").mkdir(exist_ok=True)
    (BASE / "encoded" / f"{nome}.tcf").write_text(tcf, encoding="utf-8")

    decoded = decode_online(tcf)
    salvar_csv(BASE / "decoded" / f"{nome}.csv", header, decoded)
    rt_ok = decoded == linhas

    macro, ref, dados = decompor_camadas(tcf)

    return {
        "nome": nome,
        "rt_ok": rt_ok,
        "n_unicas": len(strings_unicas),
        "bytes": ref + dados,
        "unidades": unidades_de_tokens(tokens_por_str),
        "cobertura": cobertura_pct(tokens_por_str, strings_unicas),
        "t_proc": t_proc,
    }


def imprimir_tabela(titulo: str, ids: list[str], resultados: dict) -> None:
    print()
    print("=" * 110)
    print(titulo)
    print("-" * 110)
    print(f"{'dataset':<18} {'rt':>4} {'b19':>7} {'b16':>7} {'db%':>7}  "
          f"{'u19':>6} {'u16':>6} {'du%':>7}  "
          f"{'cob19':>6} {'cob16':>6}  {'t19':>8}")
    for nome in ids:
        r = resultados[nome]
        ref16 = EXP16[nome]
        db = (r['bytes'] - ref16['bytes']) / ref16['bytes'] * 100 if ref16['bytes'] else 0
        du = (r['unidades'] - ref16['unid']) / ref16['unid'] * 100 if ref16['unid'] else 0
        cob19 = r['cobertura']
        cob16 = ref16.get('cob', None)
        cob16_s = f"{cob16:>5.1f}%" if cob16 is not None else "  n/a"
        print(f"{nome:<18} {'OK' if r['rt_ok'] else 'FAIL':>4} "
              f"{r['bytes']:>7} {ref16['bytes']:>7} {db:>+6.1f}%  "
              f"{r['unidades']:>6} {ref16['unid']:>6} {du:>+6.1f}%  "
              f"{cob19:>5.1f}% {cob16_s}  {r['t_proc']*1000:>7.1f}ms")


def main():
    todos_ids = GRUPO1 + GRUPO2 + GRUPO3
    print(f"Rodando {len(todos_ids)} datasets (par A+B busca exaustiva)...")
    resultados: dict = {}
    for nome in todos_ids:
        r = processar_ds(nome)
        resultados[nome] = r
        print(f"  {nome}: {'OK' if r['rt_ok'] else 'FAIL'} "
              f"t={r['t_proc']*1000:.0f}ms b19={r['bytes']} u19={r['unidades']} "
              f"cob={r['cobertura']:.1f}%")

    imprimir_tabela(
        "G1 - Datasets do exp 15 (D2-mini, D2-completo, D4)",
        GRUPO1, resultados)
    imprimir_tabela(
        "G2 - 6 familias do exp 17",
        GRUPO2, resultados)
    imprimir_tabela(
        "G3 - 4 familias x 3 tamanhos do exp 18",
        GRUPO3, resultados)

    falhas = [r for r in resultados.values() if not r['rt_ok']]
    if falhas:
        print(f"\nATENCAO: {len(falhas)} falhas de roundtrip:")
        for r in falhas:
            print(f"  {r['nome']}")
    else:
        print(f"\nRoundtrip {len(resultados)}/{len(resultados)} OK.")


if __name__ == "__main__":
    main()
