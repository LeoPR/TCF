"""Mede Modelo A (tabelão, RLE por coluna-pai) vs Modelo B (nível-aware, counts 1x),
variando a LARGURA do registro (nº de campos-pai) — onde a redundância do A cresce.

Rodar: python run.py
"""
from __future__ import annotations

import json
from pathlib import Path

from models import (
    _spine,
    decode_B,
    encode_A,
    encode_B,
    total,
)
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "src"))
from tcf import decode as D  # noqa: E402

HERE = Path(__file__).resolve().parent
INP, INTER, OUT = HERE / "inputs", HERE / "intermediates", HERE / "outputs"
for d in (INTER, OUT):
    d.mkdir(exist_ok=True)


def w(p: Path, t: str):
    p.write_bytes(t.encode("utf-8"))


def rt_B(records):
    parents, (aname, akind, afields) = _spine(records)
    bodies = encode_B(records)
    back = decode_B(bodies, parents, aname, akind, afields, len(records))
    return back == records, bodies


def main():
    log = ["DUAL DO RLE — multiplicidade repetida (tabelão A) vs deduzida/1x (nível-aware B)", ""]

    for src in sorted(INP.glob("*.json")):
        records = json.loads(src.read_text(encoding="utf-8"))
        parents, (aname, akind, afields) = _spine(records)

        bodies_A = encode_A(records)
        ok_B, bodies_B = rt_B(records)
        A, B = total(bodies_A), total(bodies_B)

        log.append(f"== {src.name} ==")
        log.append(f"  {len(records)} registros, {len(parents)} campos-pai, array '{aname}' ({akind})")
        log.append(f"  Modelo A (tabelão, RLE por coluna-pai): {A} B")
        log.append(f"  Modelo B (nível-aware, counts 1x):      {B} B   (RT: {ok_B})")
        log.append(f"  => B {'economiza' if B < A else 'gasta'} {abs(A-B)} B "
                   f"(a multiplicidade sai de {len(parents)} colunas-pai e vira 1 counts)")
        # artefatos
        w(OUT / f"{src.stem}.modelo-A.tabelao.tcf",
          f"{'#TCF.8H(A) ' + ','.join('.'.join(p) for p in parents)}\n" +
          "".join(f"--- {k} ---\n{v}" for k, v in bodies_A.items()))
        w(OUT / f"{src.stem}.modelo-B.nivel-aware.tcf",
          f"{'#TCF.8H(B) counts + colunas por nivel'}\n" +
          "".join(f"--- {k} ---\n{v}" for k, v in bodies_B.items()))
        log.append("")

    log += [
        "CONCLUSÃO (recupera peça 9 / 2328 + H-CARD-06 + teoria §1-4):",
        "- A multiplicidade [n_i] é INFORMAÇÃO e mora em UM lugar; RLE-por-coluna (A),",
        "  counts (B) e fk são DUAIS, conservam ×N (~log N). O schema/header compra",
        "  RECONSTRUÇÃO, não bytes de multiplicidade (teoria §3-4).",
        "- No TABELÃO (A) a mesma multiplicidade [n_i] repete no RLE de CADA coluna-pai —",
        "  redundante entre irmãs. Quanto mais campos-pai (registro largo), pior.",
        "- NÍVEL-AWARE (B) carrega [n_i] UMA vez (counts) e mantém as colunas-pai na",
        "  granularidade da pessoa (1x). É a forma MÍNIMA da peça 9 ('custo ZERO' p/ doc",
        "  único, deduzido do filho; multi-registro paga o counts UMA vez).",
        "- O 'sincronismo' que o owner citou = o canal counts/rep-level que liga as",
        "  colunas de níveis diferentes. É H-CARD-06 (Order Dependency = rep/def do Dremel).",
        "- Reconciliação do protótipo: 2301/2325 = Modelo A (dual explícito, mais simples,",
        "  RT-exato). Para FIRMAR o mínimo, migrar p/ B (counts uma vez) — decisão do owner.",
    ]
    w(OUT / "10-conclusao.txt", "\n".join(log) + "\n")
    print("\n".join(log))


if __name__ == "__main__":
    main()
