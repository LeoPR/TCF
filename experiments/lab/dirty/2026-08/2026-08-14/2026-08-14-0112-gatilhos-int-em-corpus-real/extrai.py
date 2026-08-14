"""Extrai colunas NUMÉRICAS reais dos hubs em `Z:/tcf-data`. `python extrai.py`

Roda uma vez (ou para reamostrar). Grava fatias congeladas em `inputs/fontes/`, para que
`run.py` seja reproduzível **sem Z:** — mesma política do `extrai.py` do EXP-017.

Regra do projeto: dados grandes vivem em `Z:/tcf-data/`, **nunca se baixa nada** quando o
hub já tem. Aqui só se lê.

DESCOBERTA AUTOMÁTICA, de propósito: em vez de eu escolher a dedo as colunas que confirmam
minha hipótese, o extrator varre os bancos, pega TODA coluna com tipo numérico declarado e
amostra as que tiverem valores suficientes. Escolher a dedo seria montar o corpus para a
resposta — o erro que o projeto já registrou como "benchmark que embute a própria resposta".

Cada coluna sai em duas formas (a ordem é a maior alavanca conhecida do projeto):

    <rotulo>.natural.json    a ordem em que está armazenada
    <rotulo>.ordenado.json   a mesma multiset, ordenada
"""
from __future__ import annotations

import json
import pathlib
import sqlite3
import sys

RAIZ = pathlib.Path(__file__).parent
FONTES = RAIZ / "inputs" / "fontes"
FONTES.mkdir(parents=True, exist_ok=True)
HUB = pathlib.Path("Z:/tcf-data")
N_MAX = 3000
MIN_LINHAS = 200

TIPOS_NUM = ("INT", "INTEGER", "BIGINT", "SMALLINT", "REAL", "FLOAT", "DOUBLE",
             "NUMERIC", "DECIMAL")


def numerica(decl: str) -> bool:
    d = (decl or "").upper()
    return any(t in d for t in TIPOS_NUM)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if not HUB.exists():
        print(f"Z: nao montado ({HUB}) — nada a extrair")
        return 0
    manifesto, vistos = [], set()
    for db in sorted((HUB / "interim").glob("*.db")):
        try:
            con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
            tabs = [r[0] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")]
            for tab in tabs:
                cols = list(con.execute(f'PRAGMA table_info("{tab}")'))
                n = con.execute(f'SELECT COUNT(*) FROM "{tab}"').fetchone()[0]
                if n < MIN_LINHAS:
                    continue
                for _cid, nome, decl, *_ in cols:
                    if not numerica(decl):
                        continue
                    rot = f"{db.stem}-{tab}-{nome}".replace("_", "-").lower()
                    if rot in vistos:
                        continue
                    linhas = [r[0] for r in con.execute(
                        f'SELECT "{nome}" FROM "{tab}" LIMIT {N_MAX}')]
                    vals = [v for v in linhas if v is not None]
                    if len(vals) < MIN_LINHAS:
                        continue
                    # so' INT puro nesta rodada (float e' caso proprio, ja' registrado)
                    if not all(isinstance(v, int) and not isinstance(v, bool) for v in vals):
                        continue
                    if len(set(vals)) < 2:
                        continue                     # constante: nao ensina nada aqui
                    vistos.add(rot)
                    (FONTES / f"{rot}.natural.json").write_text(
                        json.dumps(linhas, ensure_ascii=False), encoding="utf-8")
                    (FONTES / f"{rot}.ordenado.json").write_text(
                        json.dumps(sorted(linhas, key=lambda x: (x is None, x)),
                                   ensure_ascii=False), encoding="utf-8")
                    manifesto.append({
                        "rotulo": rot, "db": db.name, "tabela": tab, "coluna": nome,
                        "decl": decl, "n": len(linhas), "k": len(set(vals)),
                        "min": min(vals), "max": max(vals),
                        "nulos": sum(1 for v in linhas if v is None),
                        "exemplo": vals[:3],
                    })
                    print(f"  {rot:52s} n={len(linhas):5d} k={len(set(vals)):5d} "
                          f"[{min(vals)}..{max(vals)}]")
            con.close()
        except Exception as e:
            print(f"  !! {db.name}: {type(e).__name__}: {str(e)[:60]}")
    (FONTES / "_manifesto.json").write_text(
        json.dumps(manifesto, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n{len(manifesto)} colunas numericas extraidas -> {FONTES}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
