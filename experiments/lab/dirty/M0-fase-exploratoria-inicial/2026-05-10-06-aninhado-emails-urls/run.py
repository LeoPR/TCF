"""Roda 4 datasets de emails/URLs com o mesmo encoder/decoder aninhado
do exp 05. Valida roundtrip e imprime o TCF inteiro.
"""

import csv
from pathlib import Path

from decode_aninhado import decode_aninhado
from encode_aninhado import encode_aninhado
from patricia import (
    aplicar_patricia,
    construir_inicial,
    desenhar_arvore,
    rle_adjacente,
)

BASE = Path(__file__).parent

DATASETS = [
    "D1-emails-um-dominio",
    "D2-emails-multi-dominio",
    "D3-urls-path-comum",
    "D4-urls-multi-recurso",
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


def processar(nome: str):
    input_path = BASE / "data" / f"{nome}.csv"
    encoded_path = BASE / "encoded" / f"{nome}.tcf"
    decoded_path = BASE / "decoded" / f"{nome}.csv"

    header, linhas = ler_csv(input_path)

    nos, body = construir_inicial(linhas)
    nos = aplicar_patricia(nos)
    body_rle = rle_adjacente(body)

    tcf = encode_aninhado(nos, body_rle, header)
    encoded_path.parent.mkdir(parents=True, exist_ok=True)
    encoded_path.write_text(tcf, encoding="utf-8")

    decoded = decode_aninhado(tcf)
    salvar_csv(decoded_path, header, decoded)
    rt_ok = decoded == linhas

    print("=" * 80)
    print(f"Cenario: {nome}")
    print("-" * 80)
    print(f"  linhas input:           {len(linhas)}")
    print(f"  nos total:              {len(nos)}")
    print(f"  nos top-level:          {sum(1 for n in nos.values() if n.pai_id is None)}")
    print(f"  nos filhos (Patricia):  {sum(1 for n in nos.values() if n.pai_id is not None)}")
    print(f"  body entradas brutas:   {len(body)}")
    print(f"  body entradas RLE:      {len(body_rle)}")
    print(f"  TCF tamanho:            {len(tcf.encode('utf-8'))} bytes")
    print(f"  roundtrip:              {'OK' if rt_ok else 'FALHOU'}")
    print()
    print("  Arvore Patricia:")
    for ln in desenhar_arvore(nos).splitlines():
        print(f"    {ln}")
    print()
    print("  TCF aninhado completo:")
    for ln in tcf.splitlines():
        print(f"    {ln}")
    print()


def main():
    for ds in DATASETS:
        processar(ds)


if __name__ == "__main__":
    main()
