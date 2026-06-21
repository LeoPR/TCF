"""H-HCC-01 — caracterizacao da composicao perdida no detector HCC.

Mede o UPPER-BOUND do ganho de uma "contagem estendida": o detector atual
(`_detect_compositions`) conta sub-tuplas recorrentes so' dentro de pecas
'refs'. Aqui contamos adjacencias de ATOMS na sequencia completa (lits + refs),
incluindo a ocorrencia de DEFINICAO (onde o atom e' literal). Pares que
recorrem (R>=2) na contagem estendida mas NAO na refs-only sao composicoes
que o detector perde.

FORK exploratorio — NAO toca src/tcf. So' replica o pipeline ate' pieces e
analisa. Estimativa (upper-bound): nao modela overlap/greedy/custo-dinamico
(H-HCC-02), entao o ganho REAL <= este numero. Serve pra decidir se vale um
prototipo completo.
"""

from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
from tcf.encoder import _encode_column  # noqa: E402
from tcf.column_features import analyze_column  # noqa: E402
from tcf.auto_cadence import detect_cadence_from_features  # noqa: E402
from tcf.auto_min_len import detect_min_len_from_features  # noqa: E402
from tcf.core.online import processar  # noqa: E402
from tcf.obat_shape import processar_with_hint  # noqa: E402
from tcf.composicional.syntax import M8AVirtualRefsSyntax  # noqa: E402

EXT = Path("Z:/tcf-data/external")
ROWS = 5000

# (label, path, [colunas-alvo de texto]); None = todas as colunas
DATASETS = [
    ("adult",        EXT / "adult-census" / "adult.csv", None),
    ("online-retail", EXT / "online-retail" / "online_retail.csv",
        ["Description", "StockCode", "Country"]),
    ("tpch-lineitem", EXT / "tpch-sf001" / "lineitem.csv",
        ["l_comment", "l_shipinstruct", "l_shipmode"]),
    ("br-pessoas",   EXT / "br-identidades" / "pessoas.csv", None),
    ("receita",      EXT / "receita-cnpj" / "estabelecimentos.csv",
        ["nome_fantasia", "cnae_principal", "municipio_cod"]),
    ("ibge",         EXT / "ibge-municipios" / "municipios.csv", None),
]


def load(path, cols, limit):
    for enc in ("utf-8", "latin-1"):
        try:
            with path.open(encoding=enc, newline="") as f:
                r = csv.reader(f)
                header = next(r)
                idx = {h: i for i, h in enumerate(header)}
                want = cols or header
                data = {c: [] for c in want if c in idx}
                for n, row in enumerate(r):
                    if n >= limit:
                        break
                    if len(row) != len(header):
                        continue
                    for c in data:
                        data[c].append(row[idx[c]])
            return data
        except UnicodeDecodeError:
            continue
    return {}


def pieces_of(values):
    """Replica o pipeline ate' pieces_per_line (sem detect/emit)."""
    seen = {}
    for s in values:
        seen.setdefault(s, True)
    unicas = list(seen.keys())
    feats = analyze_column(values)
    cad, _ = detect_cadence_from_features(feats, unicas)
    mlen = detect_min_len_from_features(feats)
    if cad:
        tokens, _ = processar_with_hint(unicas, min_len=mlen, prefer_shape_consistency=True)
    else:
        tokens, _ = processar(unicas, min_len=mlen)
    syn = M8AVirtualRefsSyntax()
    return syn._tokenize_pieces(unicas, unicas, tokens)


def analyze_col(values):
    pieces_per_line, _line_meta, atom_count = pieces_of(values)

    refs_only = Counter()   # pares dentro de pecas 'refs' (= detector atual)
    extended = Counter()    # pares na sequencia completa de atoms (lit+ref)
    atom_use = Counter()    # quantas vezes cada atom aparece (proxy de sharing)

    for pieces in pieces_per_line:
        if pieces is None:
            continue
        seq = []
        for p in pieces:
            if p[0] == 'lit':
                seq.append(p[2])
            else:  # 'refs'
                refs = p[1]
                for a in range(len(refs) - 1):
                    refs_only[(refs[a], refs[a + 1])] += 1
                seq.extend(refs)
        for a in seq:
            atom_use[a] += 1
        for a in range(len(seq) - 1):
            extended[(seq[a], seq[a + 1])] += 1

    # Pares que o detector PERDE: recorrem (R>=2) no estendido, mas nao no refs-only
    missed = [(pair, R) for pair, R in extended.items()
              if R >= 2 and refs_only.get(pair, 0) < 2]

    # Estimativa de chars salvos (greedy por ganho, id composto crescendo)
    missed.sort(key=lambda x: -(x[1] - 1) * (len(str(x[0][0])) + 1 + len(str(x[0][1]))))
    saved = 0
    comp = 0
    shared_risk = 0
    for (x, y), R in missed:
        n_tam = len(str(atom_count + comp + 1))
        baseline = len(str(x)) + 1 + len(str(y))  # "x,y"
        per = baseline - n_tam
        if per <= 0:
            continue
        saved += (R - 1) * per
        comp += 1
        # risco de sharing: y muito compartilhado (composicao pode reduzir flat)
        if atom_use[y] >= 4:
            shared_risk += 1

    return {
        "n_missed": len(missed),
        "saved_chars": saved,
        "shared_risk": shared_risk,
    }


def main():
    print(f"{'dataset.col':34s} {'body B':>8s} {'missed':>7s} {'~saved':>7s} {'%body':>6s} {'shareRisk':>9s}")
    print("-" * 80)
    tot_body = tot_saved = 0
    for label, path, cols in DATASETS:
        if not path.exists():
            print(f"{label}: SKIP ({path} nao existe)")
            continue
        data = load(path, cols, ROWS)
        for col, values in data.items():
            if not values or len(set(values)) < 3:
                continue
            try:
                body = _encode_column(values, header=col)
                body_b = len(body.encode("utf-8"))
                a = analyze_col(values)
            except Exception as e:
                print(f"{label}.{col}: ERRO {type(e).__name__}: {e}")
                continue
            pct = 100 * a["saved_chars"] / body_b if body_b else 0
            tot_body += body_b
            tot_saved += a["saved_chars"]
            mark = " <<" if pct >= 1.0 else ""
            print(f"{label+'.'+col:34.34s} {body_b:8d} {a['n_missed']:7d} "
                  f"{a['saved_chars']:7d} {pct:5.2f}% {a['shared_risk']:9d}{mark}")
    print("-" * 80)
    g = 100 * tot_saved / tot_body if tot_body else 0
    print(f"{'TOTAL (upper-bound)':34s} {tot_body:8d} {'':7s} {tot_saved:7d} {g:5.2f}%")
    print("\nNOTA: upper-bound (nao modela overlap/greedy/custo-dinamico H-HCC-02).")
    print("Ganho REAL de um prototipo <= este numero. shareRisk = pares cujo")
    print("atom compartilhado (>=4 usos) pode perder sharing flat se composto.")


if __name__ == "__main__":
    main()
