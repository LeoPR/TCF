"""Roda exp 03 e mostra diferenca de tamanho/contagem vs exp 02.

Reaplica a mesma arvore Patricia do exp 02 (usa patricia.py copiado).
Encoda em 2 formatos: separado (estilo exp 02) e inline (este experimento).
"""

import csv
from pathlib import Path

from decode_inline import decode_inline
from encode_inline import encode_inline
from patricia import (
    aplicar_patricia,
    construir_inicial,
    desenhar_arvore,
    rle_adjacente,
)

BASE = Path(__file__).parent


def ler_csv(path: Path) -> tuple[str, list[str]]:
    with path.open(encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)[0]
        linhas = [r[0] for r in reader if r]
    return header, linhas


def salvar_csv(path: Path, header: str, linhas: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([header])
        for v in linhas:
            writer.writerow([v])


def encodar_separado(nos, body_rle, header) -> str:
    """Replica do encode do exp 02 — secao patricia separada do body.
    Usado aqui apenas para fins de comparacao de tamanho.
    """
    out: list[str] = []
    out.append("#TCF demonstrativo v0.6.exp02 (separado)")
    out.append(f"# coluna: {header}")
    out.append("<patricia>")
    visitados: set[int] = set()

    def emite(nid: int):
        if nid in visitados:
            return
        n = nos[nid]
        if n.pai_id is not None:
            emite(n.pai_id)
        if n.pai_id is None:
            out.append(f'  no{n.id} = folha "{n.fragmento}"')
        else:
            out.append(
                f'  no{n.id} = filho_de(no{n.pai_id}) + "{n.fragmento}"'
            )
        visitados.add(nid)

    for nid in sorted(nos):
        emite(nid)
    out.append("</patricia>")
    out.append("<body>")
    for no_id, count in body_rle:
        if count == 1:
            out.append(f"  ref:no{no_id}")
        else:
            out.append(f"  {count}x ref:no{no_id}")
    out.append("</body>")
    return "\n".join(out) + "\n"


def processar(cenario: str) -> dict:
    input_path = BASE / "data" / f"input-{cenario}.csv"
    encoded_path = BASE / "encoded" / f"input-{cenario}.tcf"
    decoded_path = BASE / "decoded" / f"input-{cenario}.csv"

    header, linhas = ler_csv(input_path)

    nos, body = construir_inicial(linhas)
    nos = aplicar_patricia(nos)
    body_rle = rle_adjacente(body)

    # Inline (este experimento)
    tcf_inline = encode_inline(nos, body_rle, header)
    encoded_path.parent.mkdir(parents=True, exist_ok=True)
    encoded_path.write_text(tcf_inline, encoding="utf-8")

    # Separado (estilo exp 02) — apenas para comparacao
    tcf_separado = encodar_separado(nos, body_rle, header)

    decoded_header, decoded_linhas = decode_inline(tcf_inline)
    salvar_csv(decoded_path, decoded_header, decoded_linhas)

    rt_ok = decoded_linhas == linhas

    # Conta linhas do TCF inline por categoria
    decls_inline = sum(1 for ln in tcf_inline.splitlines()
                       if ln.lstrip().startswith("no")
                       and ": " in ln
                       and "decl " not in ln
                       and "ref:" not in ln)
    decls_tardias = sum(1 for ln in tcf_inline.splitlines()
                        if ln.lstrip().startswith("no") and ": decl " in ln)
    refs = sum(1 for ln in tcf_inline.splitlines()
               if "ref:no" in ln and not ln.lstrip().startswith("#"))

    return {
        "cenario": cenario,
        "linhas_input": len(linhas),
        "nos_total": len(nos),
        "nos_top_level": sum(1 for n in nos.values() if n.pai_id is None),
        "nos_filhos_patricia": sum(1 for n in nos.values()
                                    if n.pai_id is not None),
        "body_entradas_brutas": len(body),
        "body_entradas_rle": len(body_rle),
        "rle_runs_acima_de_1": sum(1 for _, r in body_rle if r > 1),
        "roundtrip_ok": rt_ok,
        "arvore": desenhar_arvore(nos),
        "tcf_separado_bytes": len(tcf_separado.encode("utf-8")),
        "tcf_inline_bytes": len(tcf_inline.encode("utf-8")),
        "tcf_inline_decls_inline": decls_inline,
        "tcf_inline_decls_tardias": decls_tardias,
        "tcf_inline_refs": refs,
    }


def main():
    print("=" * 70)
    for cenario in ("A", "B"):
        r = processar(cenario)
        print(f"Cenario {cenario}")
        print("-" * 70)
        print(f"  linhas input:                 {r['linhas_input']}")
        print(f"  nos total:                    {r['nos_total']}")
        print(f"  body entradas RLE:            {r['body_entradas_rle']}")
        print(f"  RLE runs (rep > 1):           {r['rle_runs_acima_de_1']}")
        print()
        print(f"  TCF separado (estilo exp02):  {r['tcf_separado_bytes']} bytes")
        print(f"  TCF inline (exp03):           {r['tcf_inline_bytes']} bytes")
        diff = r['tcf_inline_bytes'] - r['tcf_separado_bytes']
        sinal = "+" if diff >= 0 else ""
        pct = 100 * diff / r['tcf_separado_bytes']
        print(f"  diferenca:                    {sinal}{diff} bytes ({sinal}{pct:.1f}%)")
        print()
        print(f"  decls inline (1a ocorrencia): {r['tcf_inline_decls_inline']}")
        print(f"  decls tardias (sem ocorr.):   {r['tcf_inline_decls_tardias']}")
        print(f"  refs:                         {r['tcf_inline_refs']}")
        print()
        print(f"  roundtrip:                    "
              f"{'OK' if r['roundtrip_ok'] else 'FALHOU'}")
        print("=" * 70)


if __name__ == "__main__":
    main()
