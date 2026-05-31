"""M1.B — Quote em grupo.

Tecnica: literal com qualquer char ambiguo (digito ou `*`)
e' envolto em aspas simples `'X'`. Custo fixo: +2 bytes por
literal ambiguo, independente de quantos chars.

Dentro de `'X'`:
  - `'` interno e' escapado para `\\'`
  - `\\` interno e' escapado para `\\\\`

Literais SEM ambiguidade ficam raw (sem aspas) — `'` no literal
**nao** dispara aspas (so' digito e `*` disparam — o conflito
real e' com refs e separador).

Decoder: stateful — quando ve `'` no inicio de elemento, entra
modo aspas; le ate proxima `'` nao escapada.

Implementado do zero (sem importar v4-q-fix antigo).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from online import Token, TokLit, TokRefPref, TokRefSuf
from syntax_base import Syntax


class M1BQuoteSyntax(Syntax):

    name = "M1-B-quote"

    # ---- analise de quebras (mesma logica que M1.A) ----

    def _coletar_quebras(self, unicas, tokens_por_string):
        quebras = {eid: set() for eid in range(1, len(unicas) + 1)}
        for tokens in tokens_por_string:
            for tok in tokens:
                if isinstance(tok, TokRefPref):
                    quebras[tok.string_id].add(tok.length)
                elif isinstance(tok, TokRefSuf):
                    s_ref = unicas[tok.string_id - 1]
                    quebras[tok.string_id].add(len(s_ref) - tok.length)
        for eid in range(len(unicas), 0, -1):
            tokens = tokens_por_string[eid - 1]
            pos = 0
            for tok in tokens:
                if isinstance(tok, TokLit):
                    pos += len(tok.text)
                elif isinstance(tok, TokRefPref):
                    cov = tok.length
                    for q in list(quebras[eid]):
                        if pos < q < pos + cov:
                            quebras[tok.string_id].add(q - pos)
                    pos += cov
                else:
                    cov = tok.length
                    rs = len(unicas[tok.string_id - 1]) - cov
                    for q in list(quebras[eid]):
                        if pos < q < pos + cov:
                            quebras[tok.string_id].add((q - pos) + rs)
                    pos += cov
        return quebras

    def _rle_adjacente(self, linhas):
        out = []
        for s in linhas:
            if out and out[-1][0] == s:
                out[-1] = (s, out[-1][1] + 1)
            else:
                out.append((s, 1))
        return out

    # ---- quote (especifico de M1.B) ----

    @staticmethod
    def _precisa_quote(text: str) -> bool:
        """Quote so' se contem char que mudaria modo do parser."""
        return any(c.isdigit() or c == '*' for c in text)

    @staticmethod
    def _emit_literal(text: str) -> str:
        if not M1BQuoteSyntax._precisa_quote(text):
            return text
        # com aspas — escapa `\\` e `'` internos
        esc = text.replace("\\", "\\\\").replace("'", "\\'")
        return f"'{esc}'"

    # ---- encode ----

    def encode(self, linhas_originais, strings_unicas,
                tokens_por_string, header):
        quebras = self._coletar_quebras(strings_unicas, tokens_por_string)
        unica_to_eid = {s: i + 1 for i, s in enumerate(strings_unicas)}

        frags_por_no = {}
        proximo_idx = 1
        eid_emitido = set()
        body_linhas = []

        for s_run, count in self._rle_adjacente(linhas_originais):
            eid = unica_to_eid[s_run]

            if eid not in eid_emitido:
                s = strings_unicas[eid - 1]
                tokens = tokens_por_string[eid - 1]
                qa = quebras[eid]
                frags_por_no[eid] = []
                elementos = []
                pos = 0

                for tok in tokens:
                    if isinstance(tok, TokLit):
                        sl, el = pos, pos + len(tok.text)
                        qs = sorted(q for q in qa if sl < q < el)
                        pts = [sl] + qs + [el]
                        for i in range(len(pts) - 1):
                            a, b = pts[i], pts[i + 1]
                            idx = proximo_idx
                            proximo_idx += 1
                            frags_por_no[eid].append((a, b, idx))
                            elementos.append(('lit', s[a:b]))
                        pos = el
                    elif isinstance(tok, TokRefPref):
                        herdados = [(a, b, idx)
                                     for (a, b, idx) in frags_por_no[tok.string_id]
                                     if a < tok.length and b <= tok.length]
                        for (a, b, idx) in herdados:
                            frags_por_no[eid].append((pos + a, pos + b, idx))
                            elementos.append(('ref', idx))
                        pos += tok.length
                    else:
                        s_ref = strings_unicas[tok.string_id - 1]
                        rs = len(s_ref) - tok.length
                        herdados = [(a, b, idx)
                                     for (a, b, idx) in frags_por_no[tok.string_id]
                                     if a >= rs and b > rs]
                        for (a, b, idx) in herdados:
                            frags_por_no[eid].append(
                                (pos + (a - rs), pos + (b - rs), idx))
                            elementos.append(('ref', idx))
                        pos += tok.length

                # Emitir linha. Separador `*` entre 2 literais
                # consecutivos quando anterior NAO termina com `'`
                # (parser nao sabe onde literal sem aspas termina).
                partes = []
                prev_tipo = None
                for tipo, val in elementos:
                    if tipo == 'lit':
                        emitido = self._emit_literal(val)
                        if prev_tipo == 'lit':
                            ultimo = partes[-1]
                            if not ultimo.endswith("'"):
                                partes.append('*')
                        partes.append(emitido)
                    else:
                        if prev_tipo == 'ref':
                            partes.append(',')
                        partes.append(str(val))
                    prev_tipo = tipo
                linha_resto = ''.join(partes)
                eid_emitido.add(eid)
            else:
                linha_resto = f"^{eid}"

            if count > 1:
                body_linhas.append(f"*{count}|{linha_resto}")
            else:
                body_linhas.append(linha_resto)

        return "\n".join(["[", *body_linhas, "]"]) + "\n"

    # ---- decode ----

    def _parse_decl(self, resto, frags, proximo_idx_ref):
        partes = []
        i = 0
        n = len(resto)
        while i < n:
            ch = resto[i]
            if ch == '*':
                i += 1
            elif ch.isdigit():
                j = i
                while j < n and (resto[j].isdigit() or resto[j] == ','):
                    j += 1
                for r in resto[i:j].split(','):
                    if r:
                        partes.append(frags[int(r)])
                i = j
            elif ch == "'":
                # literal com aspas, com escape interno
                buf = []
                j = i + 1
                while j < n and resto[j] != "'":
                    if resto[j] == '\\':
                        j += 1
                        if j >= n:
                            raise ValueError("escape no fim de linha")
                        buf.append(resto[j])
                        j += 1
                    else:
                        buf.append(resto[j])
                        j += 1
                if j >= n:
                    raise ValueError(f"aspa nao fechada em {resto!r}")
                texto = ''.join(buf)
                frags[proximo_idx_ref[0]] = texto
                partes.append(texto)
                proximo_idx_ref[0] += 1
                i = j + 1
            else:
                # literal sem aspas — `'` no meio e' char comum,
                # so' inicia modo aspas no comeco de elemento (top do while)
                j = i
                while j < n and not resto[j].isdigit() and resto[j] != '*':
                    j += 1
                texto = resto[i:j]
                frags[proximo_idx_ref[0]] = texto
                partes.append(texto)
                proximo_idx_ref[0] += 1
                i = j
        return ''.join(partes)

    def decode(self, tcf_text):
        frags = {}
        proximo_idx_ref = [1]
        nos_decl = []
        saida = []

        for raw in tcf_text.splitlines():
            linha = raw.strip()
            if not linha or linha in ("[", "]"):
                continue

            if linha.startswith("*") and "|" in linha:
                bar = linha.find("|")
                count = int(linha[1:bar])
                resto = linha[bar + 1:]
            else:
                count = 1
                resto = linha

            if resto.startswith("^"):
                no_id = int(resto[1:])
                s_no = nos_decl[no_id - 1]
            else:
                s_no = self._parse_decl(resto, frags, proximo_idx_ref)
                nos_decl.append(s_no)

            saida.extend([s_no] * count)
        return saida
