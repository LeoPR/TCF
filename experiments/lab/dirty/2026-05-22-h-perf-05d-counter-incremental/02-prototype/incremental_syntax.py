"""IncrementalSyntax — _detect_compositions com counter incremental.

Mantem state (contagem, sub_first_line, alias_first_line) entre iters
do outer loop. Em vez de rebuild Counter from scratch a cada iter,
aplica DELTA so' nas linhas afetadas pela substituicao anterior.

Algoritmo:
1. Iter 0 (full build): popula contagem + sub_first_line + alias_first_line
   percorrendo TODAS as linhas
2. Iters 1..N (delta apply):
   - Apply substituicao em linhas onde sub aparece
   - Pra cada linha afetada, pra cada piece 'refs' alterada:
     - Remove counts de refs_old (decrementa contagem; remove key se 0)
     - Add counts de refs_new (incrementa contagem)
   - Atualiza alias_first_line[alias_temp] com primeira linha afetada
   - sub_first_line: se sub_old apagada de li onde sub_first_line[sub_old] == li,
     marcar stale (lazy: scan quando candidato precisar)

Edge case: sub_first_line stale
- Se sub ainda existe em contagem (count > 0) mas sub_first_line apagado:
  re-scan ON DEMAND quando candidato precisar (filtro virtual_count==1+virt_pos>0)
- Quando virtual_count == 0, sub_first_line nao e' usada — skip

Validacao byte-canonical: bytes IDENTICOS ao canonical em D1-D9 +
lineitem (lineitem 5k ja' testado em sub-exp 02 H-DA-01 dirty).
"""

from __future__ import annotations

from collections import Counter

from tcf.composicional.syntax import M8AVirtualRefsSyntax


def _enumerate_subs(refs):
    """Gera todas as sub-tuplas (a..b) de refs com b-a >= 2.

    Yields (a, b, sub).
    """
    n = len(refs)
    for a in range(n):
        for b in range(a + 2, n + 1):
            yield (a, b, tuple(refs[a:b]))


def _scan_first_line_with_sub(pieces_per_line, sub):
    """Scan linear pra achar primeira linha contendo sub-tupla `sub`.

    Retorna li (>= 0) ou None se nao encontrar.
    """
    for li, pieces in enumerate(pieces_per_line):
        if pieces is None:
            continue
        for p in pieces:
            if p[0] == 'refs':
                refs = p[1]
                for a in range(len(refs)):
                    if (a + len(sub) <= len(refs)
                            and tuple(refs[a:a + len(sub)]) == sub):
                        return li
    return None


class IncrementalSyntax(M8AVirtualRefsSyntax):
    """Subclass com _detect_compositions usando counter incremental."""

    name = "M8-A-incremental"

    def _detect_compositions(self, pieces_per_line, atom_count):
        next_alias = 1
        comp_acc_k = 0
        alias_to_sub = {}
        iter_traces = []

        # State persistente entre iters
        # SIMPLIFICACAO: so' Counter incremental.
        # sub_first_line + alias_first_line rebuild full a cada iter (cheap).
        contagem = Counter()

        # Iter 0: full build do Counter (uma vez)
        for li, pieces in enumerate(pieces_per_line):
            if pieces is None:
                continue
            for p in pieces:
                if p[0] == 'refs':
                    refs = p[1]
                    for a, b, sub in _enumerate_subs(refs):
                        contagem[sub] += 1

        while True:
            # Rebuild sub_first_line + alias_first_line full
            # (mais simples que manter incremental + previne stale)
            sub_first_line: dict = {}
            alias_first_line: dict = {}
            for li, pieces in enumerate(pieces_per_line):
                if pieces is None:
                    continue
                for p in pieces:
                    if p[0] == 'refs':
                        refs = p[1]
                        for a, b, sub in _enumerate_subs(refs):
                            if sub not in sub_first_line:
                                sub_first_line[sub] = li
                        for ref in refs:
                            if ref < 0:
                                aid = -ref
                                if aid not in alias_first_line:
                                    alias_first_line[aid] = li

            # Build candidates (Counter mantido — sem rebuild)
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

            # Pick best
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

            # Apply substituicao + capturar changes pra delta apply
            K = len(sub)
            affected_pieces_changes: list = []  # [(li, [(refs_old, refs_new), ...])]

            for li in range(len(pieces_per_line)):
                pieces = pieces_per_line[li]
                if pieces is None:
                    continue
                novos = []
                line_had_sub = False
                line_changes: list = []  # [(refs_old, refs_new), ...]

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
                            iter_info['n_substituicoes'] += 1
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
                    iter_info['lines_affected'].append(li + 1)
                    affected_pieces_changes.append((li, line_changes))
                pieces_per_line[li] = novos

            # ---- DELTA APPLY (so' Counter incremental) ----
            # Pra cada linha afetada, atualizar contagem.
            # IMPORTANTE: preservar ordem do Counter — NAO deletar keys.
            # sub_first_line + alias_first_line sao rebuilt no inicio do
            # proximo iter (mais simples e robusto).
            for li, line_changes in affected_pieces_changes:
                for refs_old, refs_new in line_changes:
                    # Remove counts de refs_old (sem deletar key — preserva ordem)
                    for a, b, sub_old in _enumerate_subs(refs_old):
                        contagem[sub_old] -= 1
                    # Add counts de refs_new
                    for a, b, sub_new in _enumerate_subs(refs_new):
                        contagem[sub_new] += 1

            iter_traces.append(iter_info)
            if len(iter_traces) >= 99:
                break

        return alias_to_sub, iter_traces
