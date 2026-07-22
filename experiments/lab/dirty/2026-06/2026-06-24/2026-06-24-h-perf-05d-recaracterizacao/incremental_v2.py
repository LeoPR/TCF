"""H-PERF-05d v2 — incremental _detect_compositions fiel ao codigo ATUAL (com prune).

READ-ONLY: monkey-patch em runtime (NAO edita src/tcf). Mede speedup + divergencia
byte (M11) vs canonical atual, em lineitem (Z:) + D1-D9.

Melhoria sobre o prototipo antigo (old/refuted/...): aquele rebuildava
sub_first_line/alias_first_line por enumeracao FULL a cada iter (mesmo custo que
o rebuild). Aqui:
- Counter: full-build 1x, depois DELTA so' nas linhas afetadas + remove keys <=0.
- alias_first_line: incremental (alias_temp -> primeira linha afetada na criacao).
- sub_first_line: LAZY (scan so' quando um candidato dispara o body-order check —
  raro: virtual_count==1 e virt_pos>0). Evita a enumeracao full por iter.
"""
from __future__ import annotations

import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

from tcf import encode, decode                      # noqa: E402
from tcf.composicional.syntax import M8AVirtualRefsSyntax  # noqa: E402

_INF = float("inf")


def _scan_first_line_with_sub(pieces_per_line, sub):
    K = len(sub)
    for li, pieces in enumerate(pieces_per_line):
        if pieces is None:
            continue
        for p in pieces:
            if p[0] == "refs":
                refs = p[1]
                for a in range(len(refs)):
                    if a + K <= len(refs) and tuple(refs[a:a + K]) == sub:
                        return li
    return None


def incremental_detect(self, pieces_per_line, atom_count):
    next_alias = 1
    comp_acc_k = 0
    alias_to_sub = {}
    iter_traces = []
    contagem = Counter()
    alias_first_line = {}

    # full build 1x
    for pieces in pieces_per_line:
        if pieces is None:
            continue
        for p in pieces:
            if p[0] == "refs":
                refs = p[1]
                for a in range(len(refs)):
                    for b in range(a + 2, len(refs) + 1):
                        contagem[tuple(refs[a:b])] += 1

    while True:
        n_est_ub = max(2, len(str(atom_count + comp_acc_k + len(contagem) + 9)))
        n_tam_min = len(str(atom_count + comp_acc_k + 1))
        best = None
        best_net = 0
        n_pairs = 0
        candidates = []
        for sub, R in contagem.items():
            if R < 2:
                continue
            n_pairs += 1
            K = len(sub)
            ub_net = (R - 1) * (K * n_est_ub + (K - 1) - n_tam_min)
            if ub_net <= best_net:
                continue
            vc = 0
            for x in sub:
                if x < 0:
                    vc += 1
            if vc > 1:
                continue
            if vc == 1:
                virt_pos = next(i for i, x in enumerate(sub) if x < 0)
                if virt_pos > 0:
                    virt_alias = -sub[virt_pos]
                    sfl = _scan_first_line_with_sub(pieces_per_line, sub)
                    if sfl is None or alias_first_line.get(virt_alias, _INF) >= sfl:
                        continue
            baseline = self._estimate_baseline_chars(sub, atom_count, comp_acc_k)
            n_tam = len(str(atom_count + comp_acc_k + K - 1))
            if baseline <= n_tam:
                continue
            net = (R - 1) * (baseline - n_tam)
            candidates.append((net, sub, R, baseline, n_tam))
            if net > best_net:
                best_net = net
                best = (sub, R)

        iter_info = {
            "iter_num": len(iter_traces) + 1,
            "n_pairs": n_pairs,
            "n_candidates": len(candidates),
            "candidates_sorted": sorted(candidates, reverse=True, key=lambda c: c[0]),
            "picked": best,
        }
        if best is None:
            iter_info["stopped"] = True
            iter_traces.append(iter_info)
            break

        sub, R = best
        alias_temp = next_alias
        next_alias += 1
        comp_acc_k += len(sub) - 1
        alias_to_sub[alias_temp] = list(sub)
        virtual_id = -alias_temp
        K = len(sub)
        first_aff = None
        changes = []  # (refs_old, refs_new)
        n_subs = 0
        lines_affected = []
        for li in range(len(pieces_per_line)):
            pieces = pieces_per_line[li]
            if pieces is None:
                continue
            novos = []
            line_had = False
            for p in pieces:
                if p[0] != "refs":
                    novos.append(p)
                    continue
                refs = p[1]
                new_refs = []
                i = 0
                piece_had = False
                while i < len(refs):
                    if i + K <= len(refs) and tuple(refs[i:i + K]) == sub:
                        new_refs.append(virtual_id)
                        i += K
                        line_had = True
                        piece_had = True
                        n_subs += 1
                    else:
                        new_refs.append(refs[i])
                        i += 1
                if new_refs:
                    if piece_had:
                        changes.append((list(refs), new_refs))
                    novos.append(("refs", new_refs))
            if line_had:
                lines_affected.append(li + 1)
                if first_aff is None:
                    first_aff = li
            pieces_per_line[li] = novos

        iter_info["alias_temp"] = alias_temp
        iter_info["n_substituicoes"] = n_subs
        iter_info["lines_affected"] = lines_affected
        iter_traces.append(iter_info)
        if first_aff is not None:
            alias_first_line[alias_temp] = first_aff

        # delta Counter
        for refs_old, refs_new in changes:
            for a in range(len(refs_old)):
                for b in range(a + 2, len(refs_old) + 1):
                    contagem[tuple(refs_old[a:b])] -= 1
            for a in range(len(refs_new)):
                for b in range(a + 2, len(refs_new) + 1):
                    contagem[tuple(refs_new[a:b])] += 1
        # remove keys <=0 (mantem cardinalidade ~ fresh; ajuda o prune)
        zero = [k for k, v in contagem.items() if v <= 0]
        for k in zero:
            del contagem[k]

        if len(iter_traces) >= 99:
            break

    return alias_to_sub, iter_traces


# ---- harness ----
def _measure(label, col, reps=3):
    # canonical
    tc = []
    for _ in range(reps):
        t0 = time.perf_counter(); cano = encode(col); tc.append(time.perf_counter() - t0)
    orig = M8AVirtualRefsSyntax._detect_compositions
    M8AVirtualRefsSyntax._detect_compositions = incremental_detect
    try:
        ti = []
        for _ in range(reps):
            t0 = time.perf_counter(); incr = encode(col); ti.append(time.perf_counter() - t0)
    finally:
        M8AVirtualRefsSyntax._detect_compositions = orig
    bc, bi = len(cano.encode()), len(incr.encode())
    rt = decode(incr) == col
    speedup = min(tc) / min(ti) if min(ti) else 0
    print(f"{label:28s} N={len(col):>5} | cano {min(tc):.3f}s/{bc}B | "
          f"incr {min(ti):.3f}s/{bi}B | speedup {speedup:.2f}x | "
          f"dbytes {bi-bc:+d} ({100*(bi-bc)/bc:+.2f}%) | RT {'OK' if rt else 'FAIL'}")
    return bi - bc, rt


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT / "scripts"))
    from dataset_reader import DatasetReader
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    r = DatasetReader("tpch-sf001")
    for colname in ("l_comment", "l_shipdate", "l_commitdate"):
        col = [str(row[colname]) for row in r.rows("lineitem", limit=n)]
        _measure(f"lineitem/{colname}", col)
    r.close()
