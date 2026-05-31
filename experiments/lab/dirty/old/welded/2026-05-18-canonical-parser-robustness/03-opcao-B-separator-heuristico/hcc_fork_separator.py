"""HCC fork — Opcao B: separator `*` em ref->lit com `,`/`~`.

Subclass de M8AVirtualRefsSyntax. Override apenas de _emit_body
adicionando separator quando refs->lit AND lit comeca com `,` ou `~`.

Decoder + _escape_lit: inalterados.
"""

from __future__ import annotations

from tcf.composicional.syntax import M8AVirtualRefsSyntax


class HCCSeparatorSyntax(M8AVirtualRefsSyntax):
    """Fork de M8-A com separator heuristico em ref->lit ambiguo."""

    name = "M8-A-separator-ambiguous-lit"

    def _emit_body(self, pieces_per_line, line_meta, alias_to_sub):
        """Mesmo de M8-A canonical com adicao: separator `*` quando
        ref->lit AND lit text comeca com `,` ou `~`."""
        body = []
        prov_to_final = {}
        alias_to_final = {}
        state = {
            'current_id': [0],
            'prov_to_final': prov_to_final,
            'alias_to_final': alias_to_final,
            'alias_to_sub': alias_to_sub,
            'ref_seqs': [],
        }

        for li, (count, eid, is_rep) in enumerate(line_meta):
            if is_rep:
                if count > 1:
                    body.append(f"*{count}|^{eid}")
                else:
                    body.append(f"^{eid}")
                state['ref_seqs'].append([])
                continue

            pieces = pieces_per_line[li]
            parts = []
            prev_type = None
            prev_lit_term_digit = False
            ref_seq = []
            state['ref_seq'] = ref_seq

            for p in pieces:
                kind = p[0]

                if kind == 'lit':
                    if prev_type == 'lit':
                        parts.append('*')
                    # **MUDANCA Opcao B**: separator se ref->lit com `,`/`~`
                    elif prev_type == 'refs' and p[1] and p[1][0] in (',', '~'):
                        parts.append('*')
                    state['current_id'][0] += 1
                    prov_to_final[p[2]] = state['current_id'][0]
                    text_emit, prev_lit_term_digit = self._escape_lit(p[1])
                    parts.append(text_emit)
                    prev_type = 'lit'

                else:  # 'refs'
                    if prev_type == 'refs':
                        parts.append(',')
                    elif prev_type == 'lit' and prev_lit_term_digit:
                        parts.append('*')

                    refs = p[1]
                    run_emit = self._emit_ref_run(refs, state)
                    parts.append(run_emit)
                    prev_lit_term_digit = True
                    prev_type = 'refs'

            linha_resto = ''.join(parts)
            if count > 1:
                body.append(f"*{count}|{linha_resto}")
            else:
                body.append(linha_resto)
            state['ref_seqs'].append(ref_seq)

        return body, prov_to_final, alias_to_final, state['ref_seqs']
