"""Roda exp 17 (familias variadas) com o algoritmo do exp 16 em 6
familias de string. Mede comportamento por familia para identificar
onde o algoritmo se mantem e onde degrada.
"""

import csv
from collections import OrderedDict
from pathlib import Path

from decode_online import decode_online
from encode_online import encode_online
from online import processar, reconstroi, TokLit, TokRefPref, TokRefSuf, Token

BASE = Path(__file__).parent
FAMILIAS = [
    ("urls", "URLs profundas com base comum"),
    ("uuids", "UUIDs hex random com separadores fixos"),
    ("iso-timestamps", "Timestamps ISO de 2 dias"),
    ("ips", "IPs v4 em 3 sub-redes"),
    ("cpfs", "CPFs com digitos pseudo-random"),
    ("codigos", "Codigos PED/INV com serial"),
]


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
            total += len(tok.text) if isinstance(tok, TokLit) else 1
    return total


def analisar_cobertura(tokens_por_string: list[list[Token]],
                        strings_unicas: list[str]) -> dict:
    """Distribui as strings em categorias por tipo de cobertura."""
    cats = {
        "literal_puro": 0,        # 1a string ou sem refs
        "puro_ref": 0,            # so refs, zero literal
        "ref_lit_curto": 0,       # refs + literal <= 4 chars
        "ref_lit_longo": 0,       # refs + literal > 4 chars
        "so_literal": 0,          # so literal mas nao 1a string (raro)
    }
    chars_literal = 0
    chars_total = 0
    literais_longos: list[tuple[int, str]] = []  # (idx, texto)

    for idx, tokens in enumerate(tokens_por_string):
        s = strings_unicas[idx]
        chars_total += len(s)
        tem_ref = any(isinstance(t, (TokRefPref, TokRefSuf)) for t in tokens)
        chars_lit_aqui = sum(len(t.text) for t in tokens if isinstance(t, TokLit))
        chars_literal += chars_lit_aqui

        if idx == 0:
            cats["literal_puro"] += 1
            if chars_lit_aqui >= 5:
                literais_longos.append((idx + 1, s))
        elif not tem_ref:
            cats["so_literal"] += 1
            if chars_lit_aqui >= 5:
                literais_longos.append((idx + 1, s))
        elif chars_lit_aqui == 0:
            cats["puro_ref"] += 1
        elif chars_lit_aqui <= 4:
            cats["ref_lit_curto"] += 1
        else:
            cats["ref_lit_longo"] += 1
            for t in tokens:
                if isinstance(t, TokLit) and len(t.text) >= 5:
                    literais_longos.append((idx + 1, t.text))

    return {
        "cats": cats,
        "chars_literal": chars_literal,
        "chars_total": chars_total,
        "cobertura_ref_pct": (1 - chars_literal / chars_total) * 100 if chars_total else 0,
        "literais_longos": literais_longos,
    }


def processar_fam(nome: str) -> dict:
    header, linhas = ler_csv(BASE / "data" / f"{nome}.csv")
    seen = OrderedDict()
    for s in linhas:
        seen[s] = True
    strings_unicas = list(seen.keys())

    tokens_por_str, log_online = processar(strings_unicas, min_len=3)

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
    unidades = unidades_de_tokens(tokens_por_str)
    analise = analisar_cobertura(tokens_por_str, strings_unicas)

    return {
        "nome": nome,
        "rt_ok": rt_ok,
        "n_strings": len(strings_unicas),
        "macro": macro, "ref": ref, "dados": dados,
        "ref_dados_bytes": ref + dados,
        "unidades": unidades,
        "tokens_por_str": tokens_por_str,
        "log_online": log_online,
        "tcf": tcf,
        "analise": analise,
    }


def main():
    resultados = [processar_fam(nome) for nome, _ in FAMILIAS]

    debug_dir = BASE / "debug-output"
    debug_dir.mkdir(exist_ok=True)
    for r in resultados:
        rep = []
        rep.append("=" * 80)
        rep.append(f"FAMILIA: {r['nome']}")
        rep.append("=" * 80)
        rep.append(r['log_online'])
        rep.append("")
        rep.append(f"TCF ({len(r['tcf'].encode('utf-8'))} bytes):")
        for ln in r['tcf'].splitlines():
            rep.append(f"  {ln}")
        rep.append("")
        rep.append(f"Camadas: macro={r['macro']} ref={r['ref']} dados={r['dados']} "
                   f"(ref+dados={r['ref_dados_bytes']})")
        rep.append(f"Unidades: {r['unidades']}")
        rep.append(f"Roundtrip: {'OK' if r['rt_ok'] else 'FALHOU'}")
        (debug_dir / f"{r['nome']}.txt").write_text("\n".join(rep), encoding="utf-8")

    print("=" * 100)
    print("Tabela 1 - Compressao por familia (exp 17 = algoritmo do exp 16)")
    print("-" * 100)
    print(f"{'familia':<18} {'rt':>4} {'N':>3} {'bytes':>6} {'unid':>6} "
          f"{'chars_tot':>9} {'chars_lit':>9} {'cob_ref%':>8}")
    for r in resultados:
        a = r['analise']
        print(f"{r['nome']:<18} {'OK' if r['rt_ok'] else 'FAIL':>4} "
              f"{r['n_strings']:>3} {r['ref_dados_bytes']:>6} {r['unidades']:>6} "
              f"{a['chars_total']:>9} {a['chars_literal']:>9} "
              f"{a['cobertura_ref_pct']:>7.1f}%")

    print()
    print("=" * 100)
    print("Tabela 2 - Distribuicao de strings por tipo de cobertura")
    print("-" * 100)
    print(f"{'familia':<18} {'lit_puro':>9} {'puro_ref':>9} "
          f"{'r+lit<=4':>9} {'r+lit>4':>9} {'so_lit':>7}")
    for r in resultados:
        c = r['analise']['cats']
        print(f"{r['nome']:<18} {c['literal_puro']:>9} {c['puro_ref']:>9} "
              f"{c['ref_lit_curto']:>9} {c['ref_lit_longo']:>9} {c['so_literal']:>7}")

    print()
    print("=" * 100)
    print("Literais residuais (texto != ref) >= 5 chars - por familia")
    print("-" * 100)
    for r in resultados:
        longos = r['analise']['literais_longos']
        if not longos:
            print(f"{r['nome']}: (nenhum)")
            continue
        print(f"{r['nome']}: ({len(longos)} ocorrencias)")
        # Mostra ate 5 unicos
        vistos = set()
        for idx, txt in longos:
            if txt not in vistos:
                vistos.add(txt)
                print(f"  string {idx}: {txt!r} (len={len(txt)})")
                if len(vistos) >= 5:
                    break


if __name__ == "__main__":
    main()
