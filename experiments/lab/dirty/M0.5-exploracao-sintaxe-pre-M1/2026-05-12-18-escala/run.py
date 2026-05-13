"""Roda exp 18 (escala) com o algoritmo do exp 16 em 4 familias x 3 tamanhos.

Mede:
- tempo de processar (LCP/LCS sobre todas as anteriores)
- tempo de encode
- tempo de decode
- bytes finais
- unidades de informacao
- cobertura ref%
- categorias de cobertura

Objetivo: verificar se O(N^2 * L) e tractable nos tamanhos testados
e se a cobertura ref% se mantem em N maior.
"""

import csv
import time
from collections import OrderedDict
from pathlib import Path

from decode_online import decode_online
from encode_online import encode_online
from online import processar, reconstroi, TokLit, TokRefPref, TokRefSuf, Token

BASE = Path(__file__).parent
FAMILIAS = ["urls", "iso", "ips", "codigos"]
TAMANHOS = [50, 200, 1000]


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


def analisar_cobertura(tokens_por_string: list[list[Token]],
                        strings_unicas: list[str]) -> dict:
    cats = {"literal_puro": 0, "puro_ref": 0,
            "ref_lit_curto": 0, "ref_lit_longo": 0, "so_literal": 0}
    chars_lit = 0
    chars_tot = 0
    for idx, tokens in enumerate(tokens_por_string):
        s = strings_unicas[idx]
        chars_tot += len(s)
        tem_ref = any(isinstance(t, (TokRefPref, TokRefSuf)) for t in tokens)
        chars_lit_aqui = sum(len(t.text) for t in tokens if isinstance(t, TokLit))
        chars_lit += chars_lit_aqui
        if idx == 0:
            cats["literal_puro"] += 1
        elif not tem_ref:
            cats["so_literal"] += 1
        elif chars_lit_aqui == 0:
            cats["puro_ref"] += 1
        elif chars_lit_aqui <= 4:
            cats["ref_lit_curto"] += 1
        else:
            cats["ref_lit_longo"] += 1
    return {
        "cats": cats,
        "chars_lit": chars_lit,
        "chars_tot": chars_tot,
        "cobertura_pct": (1 - chars_lit / chars_tot) * 100 if chars_tot else 0,
    }


def processar_caso(nome: str, n: int) -> dict:
    path = BASE / "data" / f"{nome}-N{n:04d}.csv"
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
        assert rec == s, f"reconstroi falhou {nome}-N{n}: {s!r} -> {rec!r}"

    t0 = time.perf_counter()
    tcf = encode_online(linhas, strings_unicas, tokens_por_str, header)
    t_enc = time.perf_counter() - t0

    (BASE / "encoded").mkdir(exist_ok=True)
    (BASE / "encoded" / f"{nome}-N{n:04d}.tcf").write_text(tcf, encoding="utf-8")

    t0 = time.perf_counter()
    decoded = decode_online(tcf)
    t_dec = time.perf_counter() - t0

    salvar_csv(BASE / "decoded" / f"{nome}-N{n:04d}.csv", header, decoded)
    rt_ok = decoded == linhas

    macro, ref, dados = decompor_camadas(tcf)
    unidades = unidades_de_tokens(tokens_por_str)
    analise = analisar_cobertura(tokens_por_str, strings_unicas)

    return {
        "nome": nome,
        "n": n,
        "n_unicas": len(strings_unicas),
        "rt_ok": rt_ok,
        "bytes": ref + dados,
        "unidades": unidades,
        "macro": macro,
        "ref": ref,
        "dados": dados,
        "t_proc": t_proc,
        "t_enc": t_enc,
        "t_dec": t_dec,
        "cobertura_pct": analise["cobertura_pct"],
        "cats": analise["cats"],
        "chars_tot": analise["chars_tot"],
        "chars_lit": analise["chars_lit"],
    }


def main():
    resultados: list[dict] = []
    print("Rodando 4 familias x 3 tamanhos = 12 casos...")
    for fam in FAMILIAS:
        for n in TAMANHOS:
            r = processar_caso(fam, n)
            resultados.append(r)
            print(f"  {fam}-N{n:04d}: {'OK' if r['rt_ok'] else 'FAIL'} "
                  f"t_proc={r['t_proc']*1000:.1f}ms")

    print()
    print("=" * 110)
    print("Tabela 1 - Tempo por familia x N (ms)")
    print("-" * 110)
    print(f"{'familia':<10} | "
          + " | ".join(f"{'N=' + str(n):>30}" for n in TAMANHOS))
    print(f"{'':<10} | "
          + " | ".join(f"{'proc':>8} {'enc':>6} {'dec':>6} {'tot':>6} "
                       for _ in TAMANHOS))
    print("-" * 110)
    for fam in FAMILIAS:
        row = [f"{fam:<10}"]
        for n in TAMANHOS:
            r = next(x for x in resultados if x['nome'] == fam and x['n'] == n)
            tp = r['t_proc'] * 1000
            te = r['t_enc'] * 1000
            td = r['t_dec'] * 1000
            tt = tp + te + td
            row.append(f"{tp:>8.1f} {te:>6.1f} {td:>6.1f} {tt:>6.1f} ")
        print(" | ".join(row))

    print()
    print("=" * 110)
    print("Tabela 2 - Bytes, unidades, cobertura por familia x N")
    print("-" * 110)
    print(f"{'familia':<10} | "
          + " | ".join(f"{'N=' + str(n):>28}" for n in TAMANHOS))
    print(f"{'':<10} | "
          + " | ".join(f"{'bytes':>7} {'unid':>6} {'cob%':>6} {'unid/N':>6} "
                       for _ in TAMANHOS))
    print("-" * 110)
    for fam in FAMILIAS:
        row = [f"{fam:<10}"]
        for n in TAMANHOS:
            r = next(x for x in resultados if x['nome'] == fam and x['n'] == n)
            row.append(f"{r['bytes']:>7} {r['unidades']:>6} "
                       f"{r['cobertura_pct']:>5.1f}% {r['unidades']/n:>6.2f} ")
        print(" | ".join(row))

    print()
    print("=" * 110)
    print("Tabela 3 - Distribuicao de strings por categoria de cobertura (N=1000)")
    print("-" * 110)
    print(f"{'familia':<10} {'lit_puro':>10} {'puro_ref':>10} "
          f"{'r+lit<=4':>10} {'r+lit>4':>10} {'so_lit':>10}")
    for fam in FAMILIAS:
        r = next(x for x in resultados if x['nome'] == fam and x['n'] == 1000)
        c = r['cats']
        print(f"{fam:<10} {c['literal_puro']:>10} {c['puro_ref']:>10} "
              f"{c['ref_lit_curto']:>10} {c['ref_lit_longo']:>10} {c['so_literal']:>10}")

    print()
    print("=" * 110)
    print("Crescimento - razao de tempo (N=200 vs N=50; N=1000 vs N=200)")
    print("Se O(N^2): razao N=200/50 esperada ~16; N=1000/200 esperada ~25")
    print("-" * 110)
    print(f"{'familia':<10} {'t_proc 50':>12} {'t_proc 200':>12} {'r 200/50':>10} "
          f"{'t_proc 1000':>13} {'r 1000/200':>12}")
    for fam in FAMILIAS:
        r50 = next(x for x in resultados if x['nome'] == fam and x['n'] == 50)
        r200 = next(x for x in resultados if x['nome'] == fam and x['n'] == 200)
        r1000 = next(x for x in resultados if x['nome'] == fam and x['n'] == 1000)
        ra = r200['t_proc'] / r50['t_proc'] if r50['t_proc'] else 0
        rb = r1000['t_proc'] / r200['t_proc'] if r200['t_proc'] else 0
        print(f"{fam:<10} {r50['t_proc']*1000:>11.1f}ms {r200['t_proc']*1000:>11.1f}ms "
              f"{ra:>10.1f}x {r1000['t_proc']*1000:>12.1f}ms {rb:>11.1f}x")

    falhas = [r for r in resultados if not r['rt_ok']]
    if falhas:
        print()
        print(f"ATENCAO: {len(falhas)} casos com roundtrip FALHANDO:")
        for r in falhas:
            print(f"  {r['nome']}-N{r['n']:04d}")
    else:
        print()
        print(f"Roundtrip {len(resultados)}/{len(resultados)} OK.")


if __name__ == "__main__":
    main()
