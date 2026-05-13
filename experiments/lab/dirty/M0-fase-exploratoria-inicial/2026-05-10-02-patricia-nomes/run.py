"""Roda end-to-end os 2 cenarios e verifica roundtrip.

CSV -> construir_inicial -> aplicar_patricia -> rle_adjacente -> encode
TCF -> decode -> compara linha-a-linha com CSV original.
"""

import csv
from pathlib import Path

from decode import decode
from encode import encode
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


def processar(cenario: str) -> dict:
    input_path = BASE / "data" / f"input-{cenario}.csv"
    encoded_path = BASE / "encoded" / f"input-{cenario}.tcf"
    decoded_path = BASE / "decoded" / f"input-{cenario}.csv"

    header, linhas = ler_csv(input_path)

    nos, body = construir_inicial(linhas)
    nos = aplicar_patricia(nos)
    body_rle = rle_adjacente(body)

    tcf_text = encode(nos, body_rle, header)
    encoded_path.parent.mkdir(parents=True, exist_ok=True)
    encoded_path.write_text(tcf_text, encoding="utf-8")

    decoded_header, decoded_linhas = decode(tcf_text)
    salvar_csv(decoded_path, decoded_header, decoded_linhas)

    rt_ok = decoded_linhas == linhas

    return {
        "cenario": cenario,
        "linhas_input": len(linhas),
        "nos_total": len(nos),
        "nos_top_level": sum(1 for n in nos.values() if n.pai_id is None),
        "nos_filhos_patricia": sum(1 for n in nos.values() if n.pai_id is not None),
        "body_entradas_brutas": len(body),
        "body_entradas_rle": len(body_rle),
        "rle_runs_acima_de_1": sum(1 for _, r in body_rle if r > 1),
        "roundtrip_ok": rt_ok,
        "arvore": desenhar_arvore(nos),
        "tcf_bytes": len(tcf_text.encode("utf-8")),
    }


def main():
    print("=" * 60)
    for cenario in ("A", "B"):
        r = processar(cenario)
        print(f"Cenario {cenario}")
        print("-" * 60)
        print(f"  linhas input:           {r['linhas_input']}")
        print(f"  nos total:              {r['nos_total']}")
        print(f"  nos top-level:          {r['nos_top_level']}")
        print(f"  nos filhos (Patricia):  {r['nos_filhos_patricia']}")
        print(f"  body entradas brutas:   {r['body_entradas_brutas']}")
        print(f"  body entradas RLE:      {r['body_entradas_rle']}")
        print(f"  RLE runs (rep > 1):     {r['rle_runs_acima_de_1']}")
        print(f"  TCF tamanho (bytes):    {r['tcf_bytes']}")
        print(f"  roundtrip:              "
              f"{'OK' if r['roundtrip_ok'] else 'FALHOU'}")
        print(f"  arvore:")
        for ln in r["arvore"].splitlines():
            print(f"    {ln}")
        print("=" * 60)


if __name__ == "__main__":
    main()
