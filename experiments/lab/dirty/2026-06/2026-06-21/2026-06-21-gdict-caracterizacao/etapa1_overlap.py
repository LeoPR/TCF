"""B1 Etapa 1 — overlap intra-blob (Jaccard) entre colunas categoricas reais.

READ-ONLY. Le os hubs SQLite em Z: via DatasetReader (dados ficam em Z:, aqui so'
apontamentos). NAO toca src/tcf.

Pergunta decisiva: dentro de UMA tabela (o que encode() ve), quais colunas de fato
COMPARTILHAM value-set? Sem overlap intra-blob, o cross-dict (H-GDICT) nao tem o que
dedupar -> tende a 0.9. (O risco sondado: sharing forte como UF tende a ser CROSS-tabela.)

Foco: colunas text com cardinalidade <= CAP (acima disso V2-B nem e' dict-elegivel,
_V2B_MAX_CARD=1024). Jaccard(A,B) = |VA & VB| / |VA | VB|.
"""
from __future__ import annotations

import sys
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "scripts"))
from dataset_reader import DatasetReader  # noqa: E402

CAP = 1024  # dict-elegivel (V2-B gating)
DATASETS = ["adult-census", "tpch-sf001", "receita-cnpj", "br-identidades", "ibge-municipios"]


def width94(k: int) -> int:
    w, cap = 1, 94
    while k > cap:
        w += 1
        cap *= 94
    return w


def text_cols_with_sets(r: DatasetReader, table: str):
    """{col: set(valores distintos)} para colunas text dict-elegiveis (card<=CAP)."""
    out = {}
    schema = r.schema(table)
    for col, meta in schema.items():
        if meta.get("type") not in ("string", "date", "datetime"):
            continue
        try:
            d = r.con.execute(f'SELECT COUNT(DISTINCT "{col}") FROM "{table}"').fetchone()[0]
        except Exception:
            continue
        if d == 0 or d > CAP:
            continue
        vals = {row[0] for row in r.con.execute(
            f'SELECT DISTINCT "{col}" FROM "{table}" WHERE "{col}" IS NOT NULL')}
        out[col] = vals
    return out


def analyze_table(r: DatasetReader, table: str):
    sets = text_cols_with_sets(r, table)
    if len(sets) < 2:
        print(f"  [{table}] {len(sets)} col(s) text dict-elegivel — sem par pra comparar")
        return []
    cards = {c: len(s) for c, s in sets.items()}
    print(f"  [{table}] colunas dict-elegiveis (card<= {CAP}): "
          + ", ".join(f"{c}({cards[c]})" for c in sorted(sets, key=lambda x: cards[x])))
    pairs = []
    for a, b in combinations(sets, 2):
        inter = len(sets[a] & sets[b])
        if inter == 0:
            continue
        union = len(sets[a] | sets[b])
        jac = inter / union
        pairs.append((jac, a, b, inter, union, cards[a], cards[b]))
    pairs.sort(reverse=True)
    if not pairs:
        print("     (nenhum par com interseccao > 0 — value-sets disjuntos)")
    for jac, a, b, inter, union, ka, kb in pairs:
        wloc = max(width94(ka), width94(kb))
        wun = width94(union)
        flag = "" if wun == wloc else f"  <!> width {wloc}->{wun} (cruza bucket)"
        print(f"     Jaccard={jac:.3f}  {a}({ka}) ~ {b}({kb})  "
              f"inter={inter} union={union}{flag}")
    return pairs


def main():
    grand = []
    for ds in DATASETS:
        print(f"\n{'='*72}\n{ds}\n{'='*72}")
        try:
            r = DatasetReader(ds)
        except Exception as e:
            print(f"  ERRO ao abrir: {e}")
            continue
        try:
            for t in r.tables:
                ps = analyze_table(r, t)
                grand.extend((ds, t, *p) for p in ps)
        finally:
            r.close()

    print(f"\n{'='*72}\nRESUMO — pares com Jaccard >= 0.30 (candidatos a dict compartilhado)\n{'='*72}")
    strong = sorted((g for g in grand if g[2] >= 0.30), key=lambda g: -g[2])
    if not strong:
        print("  NENHUM par intra-blob com Jaccard >= 0.30.")
    for ds, t, jac, a, b, inter, union, ka, kb in strong:
        print(f"  {ds}/{t}: {a} ~ {b}  Jaccard={jac:.3f} (inter={inter}, union={union})")
    print(f"\n  total de pares com interseccao>0: {len(grand)}; fortes(>=0.30): {len(strong)}")


if __name__ == "__main__":
    main()
