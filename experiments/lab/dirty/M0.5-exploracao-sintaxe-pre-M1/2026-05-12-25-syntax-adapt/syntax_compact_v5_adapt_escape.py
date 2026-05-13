"""Sintaxe compacta v5-adapt-escape — substituicao de marcadores
secundarios + escape para digitos.

Estrategia:
1. Analisa todos os literais que serao emitidos
2. Para cada marcador secundario que aparece em algum literal,
   substitui por um char nao-usado
3. Anuncia substituicoes em linha de header (`~<orig><novo>...`)
4. Para digitos no literal (sempre conflitam com refs): usa
   escape `\\X`

Marcadores secundarios candidatos a substituicao:
  - `*` (separador de literais consecutivos) → `+`, `#`, `~`, `;`, `!`
  - `,` (separador de refs) → `;`, `:`

Marcadores que nao precisam substituicao (resolvidos por posicao):
  - `[`, `]` (so' em linhas dedicadas como macros)
  - `^` (so' no inicio de linha como uso de no)
  - `|` (so' apos `*K` no inicio como RLE bar)

Digitos NAO podem ser substituidos — refs precisam de numeros.

Custo do header: 3 chars por substituicao. Ganho: zero escape
para chars substituidos no literal.
"""

from online import Token, TokLit, TokRefPref, TokRefSuf
from syntax_base import Syntax


# Chars candidatos para sep_lit (em ordem de preferencia)
CANDIDATOS_SEP_LIT = "+#~;:!$%&"
# Chars candidatos para sep_refs
CANDIDATOS_SEP_REFS = ";:"
# Chars que nao podem ser substitutos (ja sao marcadores fixos)
CHARS_FIXOS = set("^|[]\\")


class CompactV5AdaptEscapeSyntax(Syntax):

    name = "compact_v5_adapt_escape"

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
        """Analisa literais e decide se substituir marcadores
        secundarios.

        Retorna (sep_lit, sep_refs, subs) onde subs e' dict
        {char_original: char_novo} apenas para os que mudaram.
        """
        chars_em_lit = set()
        for lit in todos_literais:
            chars_em_lit.update(lit)

        subs = {}
        chars_ocupados = set(CHARS_FIXOS)

        # sep_lit
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
                raise ValueError("v5-adapt-escape: sem char livre para sep_lit")

        # sep_refs
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
                raise ValueError("v5-adapt-escape: sem char livre para sep_refs")

        return sep_lit, sep_refs, subs

    def _escape_literal(self, text, sep_lit, sep_refs):
        """Escapa chars que mudariam modo do parser.
        - digito (vira ref)
        - sep_lit (separa literais)
        - sep_refs (separa refs — se digitos vizinhos, pode ambiguar)
        - `\\` (proprio escape)
        """
        out = []
        for c in text:
            if c.isdigit() or c == sep_lit or c == sep_refs or c == '\\':
                out.append('\\')
            out.append(c)
        return ''.join(out)

    def encode(self, linhas_originais, strings_unicas,
                tokens_por_string, header):
        # Coleta todos os literais que serao emitidos
        # (fragmentos resultantes apos quebras)
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

        # Encode tokens
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
                        if prev_tipo == 'lit':
                            partes.append(sep_lit)
                        partes.append(self._escape_literal(val, sep_lit, sep_refs))
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

        # Monta TCF com header de substituicoes se houver
        out = ["["]
        if subs:
            header_str = "~" + "".join(f"{o}{n}" for o, n in subs.items())
            out.append(header_str)
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
            else:
                # literal sem aspas com escape `\`
                buf = []
                while i < n:
                    c = resto[i]
                    if c == '\\':
                        i += 1
                        if i >= n:
                            raise ValueError("escape no fim de linha")
                        buf.append(resto[i])
                        i += 1
                    elif c.isdigit() or c == sep_lit:
                        break
                    else:
                        buf.append(c)
                        i += 1
                texto = ''.join(buf)
                frags[proximo_idx_ref[0]] = texto
                partes.append(texto)
                proximo_idx_ref[0] += 1
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

            # Header de substituicao (se houver) — 1a linha apos `[`
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

            # Prefixo de count: `*K|` ou (se substituido) `<sep_lit>K|`
            # Mas count usa SEMPRE `*` original — sub e' so' para sep_lit
            # no meio do body. RLE prefix mantém *.
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
