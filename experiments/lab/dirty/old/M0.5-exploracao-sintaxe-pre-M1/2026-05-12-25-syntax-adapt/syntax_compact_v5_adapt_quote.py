"""Sintaxe compacta v5-adapt-quote — substituicao de marcadores
secundarios + aspas para literais com digitos.

Identico a v5-adapt-escape em relacao a substituicao de `*` e
`,`. Diferenca: para digitos no literal, em vez de escape `\\X`,
usa aspas externas `'X'`.

Trade-off (vs v5-adapt-escape):
  - escape: +1 byte por digito (custo proporcional a K)
  - quote:  +2 bytes por literal com digito (custo fixo)
  - escape vence se K <= 1
  - quote  vence se K >= 3
  - K=2: empate

Regra de aspas em v5-adapt-quote:
  - Sem digito: literal sem aspas (qualquer outro char e' OK,
    inclusive `'` no proprio literal)
  - Com digito: literal envolto em `'...'` com escape interno
    de `'` para `\\'` e `\\` para `\\\\`
"""

from online import Token, TokLit, TokRefPref, TokRefSuf
from syntax_base import Syntax


CANDIDATOS_SEP_LIT = "+#~;:!$%&"
CANDIDATOS_SEP_REFS = ";:"
CHARS_FIXOS = set("^|[]\\")


class CompactV5AdaptQuoteSyntax(Syntax):

    name = "compact_v5_adapt_quote"

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
                    re_eid = tok.string_id
                    cov = tok.length
                    for q in list(quebras[eid]):
                        if pos < q < pos + cov:
                            quebras[re_eid].add(q - pos)
                    pos += cov
                else:
                    re_eid = tok.string_id
                    cov = tok.length
                    rs = len(unicas[re_eid - 1]) - cov
                    for q in list(quebras[eid]):
                        if pos < q < pos + cov:
                            quebras[re_eid].add((q - pos) + rs)
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

    def _escolher_marcadores(self, todos_literais):
        chars_em_lit = set()
        for lit in todos_literais:
            chars_em_lit.update(lit)

        subs = {}
        chars_ocupados = set(CHARS_FIXOS)

        if '*' not in chars_em_lit:
            sep_lit = '*'
            chars_ocupados.add('*')
        else:
            for c in CANDIDATOS_SEP_LIT:
                if c not in chars_em_lit and c not in chars_ocupados:
                    sep_lit = c
                    subs['*'] = c
                    chars_ocupados.add(c)
                    break
            else:
                raise ValueError("v5-adapt-quote: sem char livre para sep_lit")

        if ',' not in chars_em_lit:
            sep_refs = ','
            chars_ocupados.add(',')
        else:
            for c in CANDIDATOS_SEP_REFS:
                if c not in chars_em_lit and c not in chars_ocupados:
                    sep_refs = c
                    subs[','] = c
                    chars_ocupados.add(c)
                    break
            else:
                raise ValueError("v5-adapt-quote: sem char livre para sep_refs")

        return sep_lit, sep_refs, subs

    def _emit_literal(self, text):
        if not any(c.isdigit() for c in text):
            return text
        esc = text.replace("\\", "\\\\").replace("'", "\\'")
        return f"'{esc}'"

    def encode(self, linhas_originais, strings_unicas,
                tokens_por_string, header):
        quebras = self._coletar_quebras(strings_unicas, tokens_por_string)

        todos_literais = []
        for eid, tokens in enumerate(tokens_por_string, start=1):
            s = strings_unicas[eid - 1]
            quebras_aqui = quebras[eid]
            pos = 0
            for tok in tokens:
                if isinstance(tok, TokLit):
                    sl, el = pos, pos + len(tok.text)
                    qs = sorted(q for q in quebras_aqui if sl < q < el)
                    pts = [sl] + qs + [el]
                    for i in range(len(pts) - 1):
                        a, b = pts[i], pts[i + 1]
                        todos_literais.append(s[a:b])
                    pos = el
                elif isinstance(tok, TokRefPref):
                    pos += tok.length
                else:
                    pos += tok.length

        sep_lit, sep_refs, subs = self._escolher_marcadores(todos_literais)

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
                quebras_aqui = quebras[eid]
                frags_por_no[eid] = []
                elementos = []
                pos = 0

                for tok in tokens:
                    if isinstance(tok, TokLit):
                        sl, el = pos, pos + len(tok.text)
                        qs = sorted(q for q in quebras_aqui if sl < q < el)
                        pts = [sl] + qs + [el]
                        for i in range(len(pts) - 1):
                            a, b = pts[i], pts[i + 1]
                            idx = proximo_idx
                            proximo_idx += 1
                            frags_por_no[eid].append((a, b, idx))
                            elementos.append(('lit', s[a:b]))
                        pos = el
                    elif isinstance(tok, TokRefPref):
                        re_eid = tok.string_id
                        herdados = [(a, b, idx)
                                     for (a, b, idx) in frags_por_no[re_eid]
                                     if a < tok.length and b <= tok.length]
                        for (a, b, idx) in herdados:
                            frags_por_no[eid].append((pos + a, pos + b, idx))
                            elementos.append(('ref', idx))
                        pos += tok.length
                    else:
                        re_eid = tok.string_id
                        s_ref = strings_unicas[re_eid - 1]
                        rs = len(s_ref) - tok.length
                        herdados = [(a, b, idx)
                                     for (a, b, idx) in frags_por_no[re_eid]
                                     if a >= rs and b > rs]
                        for (a, b, idx) in herdados:
                            frags_por_no[eid].append(
                                (pos + (a - rs), pos + (b - rs), idx))
                            elementos.append(('ref', idx))
                        pos += tok.length

                partes = []
                prev_tipo = None
                for tipo, val in elementos:
                    if tipo == 'lit':
                        emitido = self._emit_literal(val)
                        # Separador entre 2 literais consecutivos se o
                        # anterior nao tem aspas (parser nao sabe onde
                        # termina sem o sep_lit).
                        if prev_tipo == 'lit':
                            ultimo = partes[-1]
                            if not ultimo.endswith("'"):
                                partes.append(sep_lit)
                        partes.append(emitido)
                    else:
                        if prev_tipo == 'ref':
                            partes.append(sep_refs)
                        partes.append(str(val))
                    prev_tipo = tipo
                linha_resto = "".join(partes)
                eid_emitido.add(eid)
            else:
                linha_resto = f"^{eid}"

            if count > 1:
                body_linhas.append(f"*{count}|{linha_resto}")
            else:
                body_linhas.append(linha_resto)

        out = ["["]
        if subs:
            out.append("~" + "".join(f"{o}{n}" for o, n in subs.items()))
        out.extend(body_linhas)
        out.append("]")
        return "\n".join(out) + "\n"

    def _parse_decl(self, resto, frags, proximo_idx_ref, sep_lit, sep_refs):
        partes = []
        i = 0
        n = len(resto)
        while i < n:
            ch = resto[i]
            if ch == sep_lit:
                i += 1
            elif ch.isdigit():
                j = i
                while j < n and (resto[j].isdigit() or resto[j] == sep_refs):
                    j += 1
                for r in resto[i:j].split(sep_refs):
                    if r:
                        partes.append(frags[int(r)])
                i = j
            elif ch == "'":
                # literal com aspas, escape interno
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
                # literal sem aspas — `'` no meio e' char comum
                j = i
                while j < n and not resto[j].isdigit() and resto[j] != sep_lit:
                    j += 1
                texto = resto[i:j]
                frags[proximo_idx_ref[0]] = texto
                partes.append(texto)
                proximo_idx_ref[0] += 1
                i = j
        return "".join(partes)

    def decode(self, tcf_text):
        frags = {}
        proximo_idx_ref = [1]
        nos_decl = []
        saida = []
        sep_lit = '*'
        sep_refs = ','
        header_consumido = False

        for raw in tcf_text.splitlines():
            linha = raw.strip()
            if not linha or linha in ("[", "]"):
                continue

            if not header_consumido and linha.startswith("~"):
                pairs = linha[1:]
                for i in range(0, len(pairs), 2):
                    orig = pairs[i]
                    novo = pairs[i + 1]
                    if orig == '*':
                        sep_lit = novo
                    elif orig == ',':
                        sep_refs = novo
                header_consumido = True
                continue
            header_consumido = True

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
                s_no = self._parse_decl(
                    resto, frags, proximo_idx_ref, sep_lit, sep_refs)
                nos_decl.append(s_no)

            saida.extend([s_no] * count)
        return saida
