# cython: language_level=3, boundscheck=False, wraparound=False
"""Acelerador Cython OPCIONAL de _detect_compositions (HCC, H-PERF-06-v2 Fase B).

ADR-0020. Logica IDENTICA ao metodo pure-Python em
composicional/syntax.py (M8AVirtualRefsSyntax._detect_compositions, pos-weld
#15). Estruturas de dados continuam Python (Counter/dict/tuple/list) -> ordem
de insercao e tie-break first-wins preservados byte-exato. So' adiciona
cdef Py_ssize_t em contadores/comprimentos e cdef list nas listas quentes.
Genexprs usam j/y pra evitar clash de escopo com os cdef.

Se esta extensao nao compilar/importar, syntax.py usa o fallback pure-Python
(output byte-identico). Validado contra os baselines/fixtures dos tests
(test_regression_v1_baseline.py + test_real_world_snapshots.py).
Speedup ~2.1-2.3x no _detect_compositions.
"""
from collections import Counter


def _detect_compositions(self, pieces_per_line, atom_count):
    cdef Py_ssize_t next_alias = 1
    cdef Py_ssize_t comp_acc_k = 0
    alias_to_sub = {}
    iter_traces = []

    cdef Py_ssize_t li, a, b, i, K, R, n_refs
    cdef Py_ssize_t n_est_ub, n_tam_min, n_tam, baseline, net, ub_net
    cdef Py_ssize_t best_net, virtual_count, virt_pos, virt_alias
    cdef Py_ssize_t alias_temp, virtual_id, ai
    cdef list refs, new_refs, novos
    cdef bint line_had_sub

    while True:
        contagem = Counter()
        sub_first_line = {}
        for li, pieces in enumerate(pieces_per_line):
            if pieces is None:
                continue
            for p in pieces:
                if p[0] == 'refs':
                    refs = p[1]
                    n_refs = len(refs)
                    for a in range(n_refs):
                        for b in range(a + 2, n_refs + 1):
                            sub = tuple(refs[a:b])
                            contagem[sub] += 1
                            if sub not in sub_first_line:
                                sub_first_line[sub] = li

        # alias_first_line: primeiro li onde -alias aparece em body
        alias_first_line = {}
        for li, pieces in enumerate(pieces_per_line):
            if pieces is None:
                continue
            for p in pieces:
                if p[0] == 'refs':
                    for ref in p[1]:
                        if ref < 0:
                            ai = -ref
                            if ai not in alias_first_line:
                                alias_first_line[ai] = li

        # cheap upper-bound prune + running-max inline (ADR-0019)
        n_est_ub = max(2, len(str(atom_count + comp_acc_k + len(contagem) + 9)))
        n_tam_min = len(str(atom_count + comp_acc_k + 1))

        candidates = []
        best = None
        best_net = 0
        for sub, R in contagem.items():
            if R < 2:
                continue
            K = len(sub)
            ub_net = (R - 1) * (K * n_est_ub + (K - 1) - n_tam_min)
            if ub_net <= best_net:
                continue
            virtual_count = sum(1 for y in sub if y < 0)
            if virtual_count > 1:
                continue
            if virtual_count == 1:
                virt_pos = next(j for j, y in enumerate(sub) if y < 0)
                if virt_pos > 0:
                    virt_alias = -sub[virt_pos]
                    if alias_first_line.get(virt_alias,
                                            float('inf')) >= sub_first_line[sub]:
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
                n_refs = len(refs)
                while i < n_refs:
                    if (i + K <= n_refs and tuple(refs[i:i + K]) == sub):
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
        if len(iter_traces) >= 99:
            break

    return alias_to_sub, iter_traces
