"""H-HCC-02 — simulador de custo DINAMICO (a "matemagica" do owner).

O upper-bound estatico (analyze.py, 1.2% weighted) SUPERCONTA: soma nets de
pares independentes, ignorando (a) overlap entre pares, (b) que compor um par
muda a largura dos ids seguintes. Aqui simulo o greedy de verdade — Re-Pair
sobre a sequencia COMPLETA de atoms (lit-def + refs), recontando a cada pick
(trata overlap) e com id composto crescendo (width dinamico).

Isola o ganho REALISTA do H-HCC-01 comparando, sob o MESMO modelo de custo:
  - refs-only greedy   = so' adjacencias ref-ref (~ o que o detector atual faz)
  - extended greedy    = todas as adjacencias (inclui a def-as-lit) <- a proposta
  realized_extra = extended - refs-only  (o ganho novo, controlado pelo modelo)

NAO enforca feasibility de body-order (decoder) -> ainda e' um teto, mas MUITO
mais apertado que o estatico (overlap + width modelados). RT: expandir as regras
reproduz a sequencia original (verificado).

FORK exploratorio — NAO toca src/tcf.
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
ROWS = 2000  # free-text e' pesado; greedy recount e' O(iters*len)

DATASETS = [
    ("adult",         EXT / "adult-census" / "adult.csv", None),
    ("online-retail", EXT / "online-retail" / "online_retail.csv",
        ["Description", "StockCode"]),
    ("tpch-lineitem", EXT / "tpch-sf001" / "lineitem.csv",
        ["l_comment", "l_shipinstruct"]),
    ("br-pessoas",    EXT / "br-identidades" / "pessoas.csv", None),
    ("receita",       EXT / "receita-cnpj" / "estabelecimentos.csv",
        ["nome_fantasia", "cnae_principal"]),
    ("ibge",          EXT / "ibge-municipios" / "municipios.csv", None),
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


def seqs_flagged(values):
    """Sequencia por linha de (atom_id, is_ref). lit-def -> is_ref=False."""
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
    pieces_per_line, _meta, atom_count = syn._tokenize_pieces(unicas, unicas, tokens)
    out = []
    for pieces in pieces_per_line:
        if pieces is None:
            out.append([])
            continue
        s = []
        for p in pieces:
            if p[0] == 'lit':
                s.append((p[2], False))
            else:
                for r in p[1]:
                    s.append((r, True))
        out.append(s)
    return out, atom_count


def greedy_repair(seqs0, atom_count, extended, max_iter=4000):
    """Re-Pair greedy sob modelo de custo dinamico. Retorna (saved, rules, seqs).

    net por pick = (n_repl - 1) * (idlen(x) + 1 + idlen(y) - idlen(V))
    com idlen(V) recalculado a cada iteracao (width dinamico). Recount a cada
    pick = trata overlap. Composto vira ref-like (is_ref=True)."""
    seqs = [list(s) for s in seqs0]
    next_id = atom_count + 1
    saved = 0
    rules = {}
    picks = []  # net de cada pick (ordem greedy = decrescente)
    for _ in range(max_iter):
        cnt = Counter()
        for s in seqs:
            for i in range(len(s) - 1):
                aid, aref = s[i]
                bid, bref = s[i + 1]
                if extended or (aref and bref):
                    cnt[(aid, bid)] += 1
        n_tam = len(str(next_id))
        best = None
        best_net = 0
        for (x, y), R in cnt.items():
            if R < 2:
                continue
            per = len(str(x)) + 1 + len(str(y)) - n_tam
            if per <= 0:
                continue
            net = (R - 1) * per
            if net > best_net:
                best_net = net
                best = (x, y, per)
        if best is None:
            break
        x, y, per = best
        V = next_id
        next_id += 1
        rules[V] = (x, y)
        # replace non-overlapping left-to-right (Re-Pair); conta repl reais
        repl = 0
        for s in seqs:
            i = 0
            out = []
            while i < len(s):
                if i + 1 < len(s) and s[i][0] == x and s[i + 1][0] == y:
                    out.append((V, True))
                    i += 2
                    repl += 1
                else:
                    out.append(s[i])
                    i += 1
            s[:] = out
        pick_net = (repl - 1) * per
        saved += pick_net
        picks.append(pick_net)
    return saved, rules, seqs, picks


def rules_for_frac(picks, frac):
    """Quantas regras (greedy, maior net primeiro) p/ atingir `frac` do saved."""
    total = sum(picks)
    if total <= 0:
        return 0
    acc = 0
    for i, net in enumerate(sorted(picks, reverse=True), 1):
        acc += net
        if acc >= frac * total:
            return i
    return len(picks)


def expand(seqs, rules):
    """Expande todas as regras -> sequencia de atom ids original (RT check)."""
    out = []
    for s in seqs:
        flat = []
        stack = [sid for sid, _ in reversed(s)]
        while stack:
            x = stack.pop()
            if x in rules:
                a, b = rules[x]
                stack.append(b)
                stack.append(a)
            else:
                flat.append(x)
        out.append(flat)
    return out


def main():
    print(f"ROWS={ROWS}\n")
    print(f"{'dataset.col':30s} {'body B':>8s} {'extra':>6s} {'%body':>6s} "
          f"{'rules':>6s} {'r@80%':>6s} {'net/rule':>8s} {'RT':>3s}")
    print("-" * 82)
    tot_body = tot_extra = tot_body_all = 0
    all_rt = True
    for label, path, cols in DATASETS:
        if not path.exists():
            print(f"{label}: SKIP")
            continue
        data = load(path, cols, ROWS)
        for col, values in data.items():
            if not values or len(set(values)) < 3:
                continue
            try:
                body_b = len(_encode_column(values, header=col).encode("utf-8"))
                seqs0, atom_count = seqs_flagged(values)
                orig = [[sid for sid, _ in s] for s in seqs0]
                s_refs, _, _, _ = greedy_repair(seqs0, atom_count, extended=False)
                s_ext, rules_e, seqs_e, picks_e = greedy_repair(
                    seqs0, atom_count, extended=True)
                rt = expand(seqs_e, rules_e) == orig
                all_rt = all_rt and rt
            except Exception as e:
                print(f"{label}.{col}: ERRO {type(e).__name__}: {e}")
                continue
            tot_body_all += body_b   # denominador weighted = TODAS as colunas
            extra = s_ext - s_refs
            if extra <= 0:
                continue  # so' lista colunas onde extended adiciona algo
            pct = 100 * extra / body_b if body_b else 0
            tot_body += body_b
            tot_extra += extra
            nrules = len(rules_e)
            r80 = rules_for_frac(picks_e, 0.80)
            net_per = extra / nrules if nrules else 0
            mark = " <<" if pct >= 1.0 else ""
            print(f"{label+'.'+col:30.30s} {body_b:8d} {extra:6d} {pct:5.2f}% "
                  f"{nrules:6d} {r80:6d} {net_per:8.2f} "
                  f"{'OK' if rt else 'X':>3s}{mark}")
    print("-" * 82)
    g_aff = 100 * tot_extra / tot_body if tot_body else 0
    g_all = 100 * tot_extra / tot_body_all if tot_body_all else 0
    print(f"realized_extra={tot_extra}  body(afetadas)={tot_body} ({g_aff:.2f}%)  "
          f"body(TODAS)={tot_body_all} ({g_all:.2f}% weighted)")
    print(f"\nRT (todas as colunas): {'OK' if all_rt else 'FALHOU'}")
    print("realized_extra = extended_greedy - refs_only_greedy (mesmo modelo).")
    print("Dinamico: overlap (recount) + width (idlen(V) cresce) modelados.")
    print("NAO enforca feasibility body-order -> ainda teto, mas << upper-bound estatico.")


if __name__ == "__main__":
    main()
