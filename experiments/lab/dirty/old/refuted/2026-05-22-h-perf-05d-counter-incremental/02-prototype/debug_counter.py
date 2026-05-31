"""Debug — verificar se Counter incremental == rebuild apos iter 1.

Se sao IGUAIS (mesmo conteudo, possivelmente ordem diferente): so' ordem.
Se DIFEREM em counts: bug de implementacao.
"""

from __future__ import annotations

import sys
from collections import Counter, OrderedDict
from pathlib import Path

THIS = Path(__file__).parent
ROOT = THIS.parents[4]
SCRIPTS = ROOT / "scripts"
SRC = ROOT / "src"

sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(SRC))

from dataset_reader import DatasetReader  # noqa: E402
from tcf.composicional.syntax import M8AVirtualRefsSyntax  # noqa: E402
from tcf.column_features import analyze_column  # noqa: E402
from tcf.auto_min_len import detect_min_len_from_features  # noqa: E402
from tcf.core.online import processar  # noqa: E402


def _enumerate_subs(refs):
    n = len(refs)
    for a in range(n):
        for b in range(a + 2, n + 1):
            yield tuple(refs[a:b])


def dedup_preserve_order(values):
    seen = OrderedDict()
    for v in values:
        seen[v] = True
    return list(seen.keys())


def build_counter_full(pieces_per_line):
    c = Counter()
    for li, pieces in enumerate(pieces_per_line):
        if pieces is None:
            continue
        for p in pieces:
            if p[0] == 'refs':
                for sub in _enumerate_subs(p[1]):
                    c[sub] += 1
    return c


def apply_substitute(pieces_per_line, sub, virtual_id):
    """Apply substituicao like canonical _detect_compositions."""
    K = len(sub)
    affected_lines = 0
    affected_pieces_changes = []
    for li in range(len(pieces_per_line)):
        pieces = pieces_per_line[li]
        if pieces is None:
            continue
        novos = []
        line_had_sub = False
        line_changes = []
        for p in pieces:
            if p[0] != 'refs':
                novos.append(p)
                continue
            refs = p[1]
            new_refs = []
            i = 0
            piece_had_sub = False
            while i < len(refs):
                if (i + K <= len(refs)
                        and tuple(refs[i:i + K]) == sub):
                    new_refs.append(virtual_id)
                    i += K
                    line_had_sub = True
                    piece_had_sub = True
                else:
                    new_refs.append(refs[i])
                    i += 1
            if new_refs:
                if piece_had_sub:
                    line_changes.append((list(refs), new_refs))
                novos.append(('refs', new_refs))
        if line_had_sub:
            affected_lines += 1
            affected_pieces_changes.append((li, line_changes))
        pieces_per_line[li] = novos
    return affected_pieces_changes


def main():
    # Carrega lineitem 5k l_commitdate
    reader = DatasetReader("tpch-sf001")
    rows = reader.rows("lineitem", limit=5000)
    cols = {c: [str(r[c]) if r[c] is not None else "" for r in rows]
            for c in rows[0].keys()}
    reader.close()

    values = cols["l_commitdate"]
    unicas = dedup_preserve_order(values)
    features = analyze_column(values)
    min_len = detect_min_len_from_features(features)
    tokens, _ = processar(unicas, min_len=min_len)

    # Setup pieces_per_line como o canonical faria
    syn = M8AVirtualRefsSyntax()
    # Call internal: _build_pieces_per_line
    pieces_per_line = syn._build_pieces_per_line(values, unicas, tokens)
    atom_count = len(unicas)

    # ITER 1
    print("=== ITER 1 ===\n")

    # Build counter inicial
    c_inicial = build_counter_full(pieces_per_line)
    print(f"Counter inicial: {len(c_inicial)} keys, total counts: {sum(c_inicial.values())}")

    # Find best sub (simulate logic)
    # Pra simplificar, escolho a sub com maior R (count)
    candidates = []
    for sub, R in c_inicial.items():
        if R < 2:
            continue
        K = len(sub)
        baseline = syn._estimate_baseline_chars(sub, atom_count, 0)
        n_tam = len(str(atom_count + K - 1))
        if baseline <= n_tam:
            continue
        candidates.append(((R - 1) * (baseline - n_tam), sub, R))
    candidates.sort(reverse=True, key=lambda x: x[0])
    if not candidates:
        print("Nenhum candidato")
        return
    best_net, best_sub, best_R = candidates[0]
    print(f"Best: net={best_net}, sub={best_sub}, R={best_R}")

    # Apply substituicao
    virtual_id = -1
    affected = apply_substitute(pieces_per_line, best_sub, virtual_id)
    print(f"Affected lines: {len(affected)}")

    # Build counter REBUILT (canonical)
    c_canonical = build_counter_full(pieces_per_line)
    print(f"\nCounter REBUILT (canonical): {len(c_canonical)} keys, "
          f"total counts: {sum(c_canonical.values())}")

    # Build counter INCREMENTAL (start from c_inicial, apply delta)
    c_incremental = c_inicial.copy()
    for li, line_changes in affected:
        for refs_old, refs_new in line_changes:
            for sub in _enumerate_subs(refs_old):
                c_incremental[sub] -= 1
            for sub in _enumerate_subs(refs_new):
                c_incremental[sub] += 1
    print(f"Counter INCREMENTAL: {len(c_incremental)} keys, "
          f"total counts: {sum(c_incremental.values())}")

    # Compare: subs com count > 0 (apos filtro)
    can_keys = {k: v for k, v in c_canonical.items() if v > 0}
    inc_keys = {k: v for k, v in c_incremental.items() if v > 0}

    print(f"\nCanonical keys (R>0): {len(can_keys)}")
    print(f"Incremental keys (R>0): {len(inc_keys)}")

    # Diffs
    only_can = set(can_keys) - set(inc_keys)
    only_inc = set(inc_keys) - set(can_keys)
    both = set(can_keys) & set(inc_keys)
    diff_count = sum(1 for k in both if can_keys[k] != inc_keys[k])

    print(f"\nOnly in canonical: {len(only_can)}")
    print(f"Only in incremental: {len(only_inc)}")
    print(f"Both (same key, diff count): {diff_count}")

    if only_can:
        print(f"\nFirst 5 only-in-canonical:")
        for k in list(only_can)[:5]:
            print(f"  {k}: can={can_keys[k]}")
    if only_inc:
        print(f"\nFirst 5 only-in-incremental:")
        for k in list(only_inc)[:5]:
            print(f"  {k}: inc={inc_keys[k]}")
    if diff_count:
        print(f"\nFirst 5 diff counts:")
        cnt = 0
        for k in both:
            if can_keys[k] != inc_keys[k]:
                print(f"  {k}: can={can_keys[k]}, inc={inc_keys[k]}")
                cnt += 1
                if cnt >= 5:
                    break

    if can_keys == inc_keys:
        print("\nCounters CONTENT IDENTICAL (so' ordem pode diferir)")
    else:
        print("\nCounters DIFFER em conteudo — BUG!")


if __name__ == "__main__":
    main()
