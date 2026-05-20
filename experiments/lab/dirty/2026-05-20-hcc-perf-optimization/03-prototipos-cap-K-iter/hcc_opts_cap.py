"""HCC cap K + cap iter — possivel byte loss.

Patch _detect_compositions com:
- cap_K_max: ignora sub-tuplas de tamanho > cap_K_max
- cap_iter_max: para outer loop apos cap_iter_max iters

Validar byte loss vs baseline.
"""

from __future__ import annotations

from collections import Counter
from tcf.composicional import syntax as _hcc

_originals = {}


def make_detect_capped(cap_K_max=None, cap_iter_max=None):
    """Factory que gera _detect_compositions com caps."""
    if cap_iter_max is None:
        cap_iter_max = 99

    def _detect(self, pieces_per_line, atom_count):
        next_alias = 1
        comp_acc_k = 0
        alias_to_sub = {}
        iter_traces = []

        while True:
            contagem = Counter()
            sub_first_line = {}
            for li, pieces in enumerate(pieces_per_line):
                if pieces is None:
                    continue
                for p in pieces:
                    if p[0] == 'refs':
                        refs = p[1]
                        R = len(refs)
                        for a in range(R):
                            b_max = R + 1
                            if cap_K_max is not None:
                                b_max = min(b_max, a + cap_K_max + 1)
                            for b in range(a + 2, b_max):
                                sub = tuple(refs[a:b])
                                contagem[sub] += 1
                                if sub not in sub_first_line:
                                    sub_first_line[sub] = li

            alias_first_line = {}
            for li, pieces in enumerate(pieces_per_line):
                if pieces is None:
                    continue
                for p in pieces:
                    if p[0] == 'refs':
                        for ref in p[1]:
                            if ref < 0:
                                a = -ref
                                if a not in alias_first_line:
                                    alias_first_line[a] = li

            candidates = []
            for sub, R in contagem.items():
                if R < 2:
                    continue
                virtual_count = sum(1 for x in sub if x < 0)
                if virtual_count > 1:
                    continue
                if virtual_count == 1:
                    virt_pos = next(i for i, x in enumerate(sub) if x < 0)
                    if virt_pos > 0:
                        virt_alias = -sub[virt_pos]
                        if alias_first_line.get(virt_alias,
                                                  float('inf')) >= sub_first_line[sub]:
                            continue
                baseline = self._estimate_baseline_chars(
                    sub, atom_count, comp_acc_k)
                K = len(sub)
                n_tam = len(str(atom_count + comp_acc_k + K - 1))
                if baseline <= n_tam:
                    continue
                candidates.append(((R - 1) * (baseline - n_tam),
                                    sub, R, baseline, n_tam))

            best = None
            best_net = 0
            for net, sub, R, baseline, n_tam in candidates:
                if net > best_net:
                    best_net, best = net, (sub, R)

            iter_info = {
                'n_pairs': sum(1 for v in contagem.values() if v >= 2),
                'n_candidates': len(candidates),
                'candidates_sorted': sorted(candidates, reverse=True,
                                              key=lambda c: c[0]),
                'picked': best,
                'iter_num': len(iter_traces) + 1,
            }

            if best is None:
                iter_info['stopped'] = True
                iter_traces.append(iter_info)
                break

            sub, R = best
            alias_temp = next_alias
            next_alias += 1
            comp_acc_k += len(sub) - 1
            alias_to_sub[alias_temp] = list(sub)
            virtual_id = -alias_temp
            iter_info['alias_temp'] = alias_temp
            iter_info['lines_affected'] = []
            iter_info['n_substituicoes'] = 0

            K = len(sub)
            for li in range(len(pieces_per_line)):
                pieces = pieces_per_line[li]
                if pieces is None:
                    continue
                novos = []
                line_had_sub = False
                for p in pieces:
                    if p[0] != 'refs':
                        novos.append(p)
                        continue
                    refs = p[1]
                    new_refs = []
                    i = 0
                    while i < len(refs):
                        if (i + K <= len(refs)
                                and tuple(refs[i:i + K]) == sub):
                            new_refs.append(virtual_id)
                            i += K
                            iter_info['n_substituicoes'] += 1
                            line_had_sub = True
                        else:
                            new_refs.append(refs[i])
                            i += 1
                    if new_refs:
                        novos.append(('refs', new_refs))
                if line_had_sub:
                    iter_info['lines_affected'].append(li + 1)
                pieces_per_line[li] = novos

            iter_traces.append(iter_info)
            if len(iter_traces) >= cap_iter_max:
                break

        return alias_to_sub, iter_traces

    return _detect


def patch(cap_K_max=None, cap_iter_max=None):
    cls = _hcc.M8AVirtualRefsSyntax
    _originals.clear()
    _originals['_detect_compositions'] = cls._detect_compositions
    cls._detect_compositions = make_detect_capped(cap_K_max, cap_iter_max)


def unpatch():
    cls = _hcc.M8AVirtualRefsSyntax
    for name, orig in _originals.items():
        setattr(cls, name, orig)
    _originals.clear()
