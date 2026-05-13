"""Sintaxe compacta v4-quote-fixed — correcao do v4-quote.

Vs v4-quote do exp 24:
- `_precisa_aspas` NAO dispara por `'`. Aspas sao usadas APENAS
  quando o literal contem char que mudaria o modo do parser:
    - digito (vira ref no modo sem-aspas)
    - `*`    (vira separador no modo sem-aspas)
- `'` no literal e tratado como char comum (igual v3 base).
  Apenas se ja ha aspas externas (devido a digito/*), o `'`
  interno e escapado para `\\'`.

Motivacao: o conflito **tem que existir**. `'` nao e marcador
em v3, entao nao deveria forcar aspas. Era erro do exp 24.

Regra de aspas:
  - Sem digito e sem `*`: literal sem aspas (mesmo se contem `'`)
  - Com digito ou `*`: literal com aspas; `'` interno escapado
"""

from online import Token, TokLit, TokRefPref, TokRefSuf
from syntax_base import Syntax


class CompactV4QuoteFixedSyntax(Syntax):

    name = "compact_v4_quote_fixed"

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

    @staticmethod
    def _precisa_aspas(text: str) -> bool:
        # APENAS digito ou `*` disparam aspas — sao os unicos chars
        # que mudam o modo do parser. `'` nao e marcador em v3 base,
        # entao no modo sem-aspas e tratado como char qualquer.
        return any(c.isdigit() or c == '*' for c in text)

    @staticmethod
    def _emit_literal(text: str) -> str:
        if not CompactV4QuoteFixedSyntax._precisa_aspas(text):
            return text
        # com aspas — escapar `\\` e `'` internos
        esc = text.replace("\\", "\\\\").replace("'", "\\'")
        return f"'{esc}'"

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
                        # Separador `*` entre 2 literais consecutivos sempre
                        # que o anterior nao tem aspas (parser nao sabe
                        # onde o literal sem aspas termina sem ele).
                        # Quando o anterior tem aspas, `'` final ja delimita.
                        if prev_tipo == 'lit':
                            ultimo = partes[-1]
                            ultimo_tem_aspas = ultimo.endswith("'")
                            if not ultimo_tem_aspas:
                                partes.append('*')
                        partes.append(emitido)
                    else:
                        if prev_tipo == 'ref':
                            partes.append(',')
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

        return "\n".join(["[", *body_linhas, "]"]) + "\n"

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
                # literal entre aspas com escape interno
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
                # literal sem aspas: ler ate proximo digito ou *.
                # `'` no meio e' char comum (nao para o literal),
                # porque `'` so' inicia modo-aspas no comeco de elemento
                # (top deste while loop).
                j = i
                while j < n and not resto[j].isdigit() and resto[j] != '*':
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
