"""M1.A' — Escape com escopo (variante de M1.A).

Tecnica: `\\` antes de uma sequencia de digitos sinaliza
"todos os digitos contiguos seguintes sao literal". Em vez de
escapar char a char (M1.A original), agrupa a sequencia.

Para `*` e `\\` no literal: continua escape individual (esses
chars nao formam "sequencias" no sentido tipico).

Custo (vs M1.A):
- K digitos contiguos no literal:
  - M1.A: +K bytes (K escapes individuais)
  - M1.A': +1 byte (1 escape antes da sequencia) + 0 chars
    extras + dependendo de contexto, +1 separador
- Para K=1: M1.A' = M1.A (escape unico)
- Para K=2: M1.A' = M1.A (mesma economia)
- Para K=3+: M1.A' ganha (K-1 bytes economizados, possivelmente
  -1 por separador necessario antes de refs adjacentes)

Decoder: stateful pequeno — em modo literal, ao ver `\\`
seguido de digito, le sequencia de digitos como literal.

Implementado do zero (sem importar M1.A nem v4-escape antigo).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from online import Token, TokLit, TokRefPref, TokRefSuf
from syntax_base import Syntax


class M1AEscapeEscopoSyntax(Syntax):

    name = "M1-A-escape-escopo"

    # ---- analise de quebras (mesma logica que M1.A e M1.B) ----

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

    # ---- escape com escopo ----

    @staticmethod
    def _escape_e_termina_em_digito(text: str) -> tuple[str, bool]:
        """Escapa chars ambiguos. Dígitos contíguos viram `\\<seq>`.
        `*` e `\\` ficam com escape individual `\\X`.

        Retorna (texto_escapado, terminou_com_seq_digitos).
        O segundo flag indica se a saida termina com sequencia
        de digitos escapada — usado para decidir separador antes
        de refs adjacentes.
        """
        out = []
        i = 0
        n = len(text)
        termina_seq_digito = False
        while i < n:
            c = text[i]
            if c.isdigit():
                j = i
                while j < n and text[j].isdigit():
                    j += 1
                out.append('\\')
                out.append(text[i:j])
                termina_seq_digito = (j == n)
                i = j
            elif c == '*' or c == '\\':
                out.append('\\')
                out.append(c)
                termina_seq_digito = False
                i += 1
            else:
                out.append(c)
                termina_seq_digito = False
                i += 1
        return ''.join(out), termina_seq_digito

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

                # Montar linha. Cada literal e escape-escopo.
                # Se literal termina em sequencia de digitos e proximo
                # elemento e' ref, precisa separador `*` (parser nao
                # absorve digitos das refs como parte do literal).
                partes = []
                prev_tipo = None
                prev_lit_termina_seq_digito = False
                for tipo, val in elementos:
                    if tipo == 'lit':
                        if prev_tipo == 'lit':
                            partes.append('*')
                        emitido, term_seq = self._escape_e_termina_em_digito(val)
                        partes.append(emitido)
                        prev_lit_termina_seq_digito = term_seq
                    else:
                        # ref
                        if prev_lit_termina_seq_digito:
                            # separador necessario para parser nao
                            # absorver digitos da ref como parte do literal
                            partes.append('*')
                            prev_lit_termina_seq_digito = False
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
                # refs (sem escape `\` antes)
                j = i
                while j < n and (resto[j].isdigit() or resto[j] == ','):
                    j += 1
                for r in resto[i:j].split(','):
                    if r:
                        partes.append(frags[int(r)])
                i = j
            else:
                # literal sem aspas, com escape `\X` ou escape escopo `\<digits>`
                buf = []
                while i < n:
                    c = resto[i]
                    if c == '\\':
                        i += 1
                        if i >= n:
                            raise ValueError("escape no fim de linha")
                        next_c = resto[i]
                        if next_c.isdigit():
                            # escape escopo: le sequencia de digitos
                            j = i
                            while j < n and resto[j].isdigit():
                                j += 1
                            buf.append(resto[i:j])
                            i = j
                        else:
                            # escape individual
                            buf.append(next_c)
                            i += 1
                    elif c.isdigit() or c == '*':
                        break
                    else:
                        buf.append(c)
                        i += 1
                texto = ''.join(buf)
                frags[proximo_idx_ref[0]] = texto
                partes.append(texto)
                proximo_idx_ref[0] += 1
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
