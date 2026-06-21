"""Caracterizacao de colunas UCI — que estrutura existe pra naturezas?

Passo 4.1 (fechar limbo): naturezas raras #5 (range) e #8 (arredondamento)
+ Pacote 7 H-LR-* (lossy float/monetary) foram REFUTADAS em Adult/TPC-H
(datasets gerais). T-DATA-1 trouxe 3 datasets financeiros/cientificos
projetados pra ter esses padroes. Antes de testar nature specs, MEDIR
se a estrutura realmente existe.

Por coluna numerica, mede:
- rounding: fracao de valores terminando em .99/.95/.50/.00/.X0 (preco)
- range: min/max/spread (range estreito = candidato delta-from-base)
- precision: numero de casas decimais (fixa = candidato a separar int/frac)
- cardinality: unicos/total (baixa = dedup ja resolve)
- M10 ratio atual (baseline a vencer)

Saida: tabela por coluna + flag de candidatura a cada hipotese.
"""

from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
from tcf import encode, decode  # noqa: E402

EXT = Path("Z:/tcf-data/external")

DATASETS = {
    "wine-quality": EXT / "wine-quality" / "wine.csv",
    "beijing-pm25": EXT / "beijing-pm25" / "beijing_pm25.csv",
    "online-retail": EXT / "online-retail" / "online_retail.csv",
}


def load_cols(path: Path, limit: int | None = None) -> dict[str, list[str]]:
    with path.open(encoding="utf-8") as f:
        r = csv.reader(f)
        header = next(r)
        cols = {h: [] for h in header}
        for i, row in enumerate(r):
            if limit and i >= limit:
                break
            for h, v in zip(header, row):
                cols[h].append(v)
    return cols


def is_numeric_col(values: list[str]) -> bool:
    n_ok = 0
    for v in values[:200]:
        if v == "":
            continue
        try:
            float(v)
            n_ok += 1
        except ValueError:
            return False
    return n_ok > 0


def decimal_places(v: str) -> int:
    if "." not in v:
        return 0
    return len(v.split(".", 1)[1].rstrip())


def analyze_numeric(values: list[str]) -> dict:
    nonempty = [v for v in values if v != ""]
    n = len(nonempty)
    if n == 0:
        return {}
    floats = []
    for v in nonempty:
        try:
            floats.append(float(v))
        except ValueError:
            pass
    # rounding: ultimo digito / terminacoes de preco
    cents = Counter()
    for v in nonempty:
        if "." in v:
            frac = v.split(".", 1)[1]
            cents[frac[:2]] += 1
        else:
            cents["int"] += 1
    top_cents = cents.most_common(3)
    # precision distribution
    prec = Counter(decimal_places(v) for v in nonempty)
    # range
    spread = (max(floats) - min(floats)) if floats else 0
    # cardinality
    uniq = len(set(nonempty))
    return {
        "n": n,
        "uniq": uniq,
        "cardinality": round(uniq / n, 3),
        "min": round(min(floats), 4) if floats else None,
        "max": round(max(floats), 4) if floats else None,
        "spread": round(spread, 4),
        "precision_dist": dict(prec.most_common(4)),
        "top_terminations": top_cents,
    }


def m10_ratio(values: list[str]) -> tuple[int, int, float, bool]:
    raw = sum(len(v.encode("utf-8")) for v in values)
    text = encode(values)
    tcf = len(text.encode("utf-8"))
    rt = decode(text) == values
    return raw, tcf, (tcf / raw * 100 if raw else 0), rt


def main():
    for ds_name, path in DATASETS.items():
        if not path.exists():
            print(f"[skip] {ds_name}: {path} nao existe")
            continue
        # limit retail pra rodar rapido na caracterizacao
        limit = 20000 if ds_name == "online-retail" else None
        cols = load_cols(path, limit=limit)
        n_rows = len(next(iter(cols.values())))
        print(f"\n{'='*78}")
        print(f"{ds_name}  ({n_rows} rows{' [limit]' if limit else ''})")
        print(f"{'='*78}")
        for cname, values in cols.items():
            if not is_numeric_col(values):
                continue
            a = analyze_numeric(values)
            if not a:
                continue
            raw, tcf, ratio, rt = m10_ratio(values)
            print(f"\n  COL {cname!r}  (numeric)")
            print(f"    n={a['n']} uniq={a['uniq']} card={a['cardinality']} "
                  f"range=[{a['min']}, {a['max']}] spread={a['spread']}")
            print(f"    precision_dist={a['precision_dist']}")
            print(f"    top_terminations={a['top_terminations']}")
            print(f"    M10: {raw}B -> {tcf}B ({ratio:.1f}%) RT={'OK' if rt else 'FAIL'}")
            # Flags de candidatura
            flags = []
            # #8 arredondamento: terminacoes concentradas
            top_frac = a['top_terminations'][0][1] / a['n'] if a['top_terminations'] else 0
            if top_frac > 0.3 and a['top_terminations'][0][0] not in ('int',):
                flags.append(f"#8-rounding (term {a['top_terminations'][0][0]!r} em {top_frac*100:.0f}%)")
            # #5 range estreito: spread pequeno relativo
            if a['min'] is not None and a['spread'] > 0:
                rel_spread = a['spread'] / (abs(a['max']) + 1e-9)
                if rel_spread < 0.5 and a['cardinality'] > 0.3:
                    flags.append(f"#5-narrow-range (rel_spread {rel_spread:.2f})")
            # precision fixa
            if len(a['precision_dist']) == 1 and 0 not in a['precision_dist']:
                flags.append(f"fixed-precision ({list(a['precision_dist'])[0]} casas)")
            # ratio alto = oportunidade
            if ratio > 70:
                flags.append(f"weak-M10 ({ratio:.0f}% — oportunidade)")
            if flags:
                print(f"    >> CANDIDATO: {', '.join(flags)}")


if __name__ == "__main__":
    main()
