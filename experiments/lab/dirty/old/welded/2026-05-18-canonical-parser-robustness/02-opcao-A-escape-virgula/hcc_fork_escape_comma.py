"""HCC fork — Opcao A: escapar `,` em `_escape_lit`.

Subclass de M8AVirtualRefsSyntax (src/tcf intocado). Override apenas
de `_escape_lit` adicionando `,` aos chars escapados.

Decoder: inalterado. `\,` ja' cai no else branch (append nc) em
`_parse_decl`.
"""

from __future__ import annotations

from tcf.composicional.syntax import M8AVirtualRefsSyntax


class HCCEscapeCommaSyntax(M8AVirtualRefsSyntax):
    """Fork de M8-A com `,` escapado em literais."""

    name = "M8-A-escape-comma"

    @staticmethod
    def _escape_lit(text):
        out, i, n = [], 0, len(text)
        term_seq = False
        while i < n:
            c = text[i]
            if c.isdigit():
                j = i
                while j < n and text[j].isdigit():
                    j += 1
                out.append('\\' + text[i:j])
                term_seq = (j == n)
                i = j
            elif c in ('*', '\\', '~', ','):
                out.append('\\' + c)
                term_seq = False
                i += 1
            else:
                out.append(c)
                term_seq = False
                i += 1
        return ''.join(out), term_seq
