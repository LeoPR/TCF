"""Trace + rede de debug do detector HCC (M8.A) — concern separado do core.

Strings de diagnostico (iteracoes do detector + rede de atomos/composicoes),
populadas por `encode()` em `SideOutputs.hcc_trace` / `.hcc_rede`. **NAO afetam
os bytes** do output — sao puramente observabilidade (debug). Isoladas aqui
(P2 foco-2, 2026-06-24) pra deixar o CORE portavel (tokenize/detect/emit/decode)
limpo: um port C/Rust NAO porta este modulo.

Funcoes puras: recebem `name` + os dados do encode (+ o callable `emit_refs_range`
do emit) e retornam a lista de linhas. O caller (`M8AVirtualRefsSyntax.encode`)
guarda em `self._trace` / `self._rede`.
"""
from __future__ import annotations

from collections import Counter, defaultdict


def fmt_sub(sub) -> str:
    """Formata uma sub-tupla de refs (id>0 = atom; id<0 = alias `a{n}`)."""
    return ",".join(str(s) if s > 0 else f"a{-s}" for s in sub)


def build_trace(name, iter_traces, prov_to_final, alias_to_final, ref_seqs,
                emit_refs_range) -> list[str]:
    """Trace das iteracoes do detector + oportunidades perdidas (post-hoc)."""
    t = [f"# Optimization trace — syntax={name}", ""]
    t.append("=== DETECTOR ITERATIONS (unified — atoms + virtuals) ===")
    t.append("")
    for info in iter_traces:
        t.append(f"--- Iter {info['iter_num']} ---")
        t.append(f"Sub-tuplas K>=2 com R>=2: {info['n_pairs']}  "
                 f"net>0: {info['n_candidates']}")
        if info['picked'] is None:
            t.append("Nenhum candidato com net > 0. STOP.")
            t.append("")
            continue
        picked_sub = info['picked'][0]
        for net, sub, R, baseline, n_tam in info['candidates_sorted'][:10]:
            pick = " <- PICK" if sub == picked_sub else ""
            sub_str = fmt_sub(sub)
            t.append(f"  {sub_str:24s} | R={R} Lr={baseline} "
                     f"len(N)~{n_tam} net=({R-1})*({baseline}-{n_tam})"
                     f"={net}{pick}")
        top_net = info['candidates_sorted'][0][0]
        tied = [c for c in info['candidates_sorted'] if c[0] == top_net]
        if len(tied) > 1:
            t.append(f"  AMBIGUIDADE: {len(tied)} candidates "
                     f"empatam em net={top_net}")
        t.append(f"Substituido em {info['n_substituicoes']} "
                 f"ocorrencias (linhas {info['lines_affected']})")
        t.append("")
    # Missed (post-hoc on emitted ref_seqs)
    t.append("=== MISSED OPPORTUNITIES (post-hoc) ===")
    pair_count = Counter()
    pair_lines = defaultdict(list)
    for li, seq in enumerate(ref_seqs):
        for i in range(len(seq) - 1):
            pair = (seq[i], seq[i + 1])
            pair_count[pair] += 1
            if (li + 1) not in pair_lines[pair]:
                pair_lines[pair].append(li + 1)
    next_id = max(list(prov_to_final.values()) +
                   list(alias_to_final.values()) + [0]) + 1
    len_n = len(str(next_id))
    missed = []
    for pair, R in pair_count.items():
        if R < 2:
            continue
        baseline = len(emit_refs_range(list(pair)))
        if baseline <= len_n:
            continue
        net = (R - 1) * (baseline - len_n)
        if net > 0:
            missed.append((net, pair, R, baseline))
    missed.sort(reverse=True)
    if not missed:
        t.append("  (nenhum)")
    else:
        for net, pair, R, baseline in missed[:30]:
            lines_str = ",".join(str(l) for l in pair_lines[pair])
            t.append(f"  pair=({pair[0]},{pair[1]}) R={R} "
                     f"lines=[{lines_str}] "
                     f"baseline={baseline} est_savings={net}")
    t.append("")
    t.append(f"Total estimated missed: {sum(m[0] for m in missed)}")
    return t


def build_rede(name, pieces_per_line, prov_to_final, alias_to_final,
               alias_to_sub, ref_seqs) -> list[str]:
    """Rede de atomos (literais) + composicoes (aliases) + uso por ref."""
    r = [f"# Rede de atomos + composicoes — {name}", ""]
    r.append("=== ATOMS (final IDs) ===")
    prov_to_lit = {}
    for pieces in pieces_per_line:
        if pieces is None:
            continue
        for p in pieces:
            if p[0] == 'lit':
                prov_to_lit[p[2]] = p[1]
    for prov in sorted(prov_to_final):
        r.append(f"  final {prov_to_final[prov]:3d}: "
                 f"{prov_to_lit.get(prov, '?')!r}")
    r.append("")
    r.append("=== COMPOSITIONS (final IDs) ===")
    for atemp, fid in sorted(alias_to_final.items(),
                               key=lambda x: x[1]):
        sub = alias_to_sub[atemp]
        sub_fmt = fmt_sub(sub)
        r.append(f"  final {fid:3d} = a{atemp} composicao({sub_fmt})")
    r.append("")
    r.append("=== USO POR REF ===")
    usage = Counter()
    for seq in ref_seqs:
        usage.update(seq)
    for ref_id, n in sorted(usage.items(), key=lambda x: (-x[1], x[0])):
        r.append(f"  ref {ref_id:3d}: {n}x")
    return r
