"""Sintaxe compacta v3 — v2 sem aspas em literais.

Vs compact_v2:
- Literais NAO sao envolvidos por aspas. Sao detectados como
  "sequencia de chars nao-digitos-nao-virgula-nao-separador".
- Separador entre fragmentos da decl: `*` (substituiu o papel do
  `'...'` quando ha literais consecutivos).
- Refs continuam sendo digitos separados por `,`.
- Prefixo de count: `*K|` no inicio da linha (igual v2).
- Uso de no: `^N`.

Regra de transicao no parser:
  - digito ou `,` apos algo nao-digito → comeco de refs
  - nao-digito apos algo digito ou `,` → comeco de literal
  - `*` → separador entre fragmentos da decl (entre 2 literais)

Limitacao critica:
  - Literais nao podem conter digitos. Se um literal precisar ter
    digito (URL com id, IP, codigo com serial), v3 quebra.
  - Em D2-mini e D2-completo isso nao ocorre (literais sao
    emails sem digitos).
  - Literais nao podem conter `*`, `^`, `|` ou `,`. Tampouco
    `[` ou `]`.
"""

from online import Token, TokLit, TokRefPref, TokRefSuf
from syntax_base import Syntax


class CompactV3Syntax(Syntax):

    name = "compact_v3"

    def _coletar_quebras(self, unicas, tokens_por_string):
        quebras = {eid: set() for eid in range(1, len(unicas) + 1)}
        for tokens in tokens_por_string:
            for tok in tokens:
                if isinstance(tok, TokRefPref):
                    quebras[tok.string_id].add(tok.length)
                elif isinstance(tok, TokRefSuf):
                    s_ref = unicas[tok.string_id - 1]
                    quebras[tok.string_id].add(len(s_ref) - tok.length)
        # propagacao inversa
        for eid in range(len(unicas), 0, -1):
            tokens = tokens_por_string[eid - 1]
            pos = 0
            for tok in tokens:
                if isinstance(tok, TokLit):
                    pos += len(tok.text)
                elif isinstance(tok, TokRefPref):
                    ref_eid = tok.string_id
                    cov = tok.length
                    for q in list(quebras[eid]):
                        if pos < q < pos + cov:
                            quebras[ref_eid].add(q - pos)
                    pos += cov
                else:
                    ref_eid = tok.string_id
                    cov = tok.length
                    ref_start = len(unicas[ref_eid - 1]) - cov
                    for q in list(quebras[eid]):
                        if pos < q < pos + cov:
                            quebras[ref_eid].add((q - pos) + ref_start)
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

    def _validar_literal(self, texto: str, contexto: str) -> None:
        if any(c.isdigit() for c in texto):
            raise ValueError(
                f"v3: literal contem digito (proibido sem escape): "
                f"{texto!r} (contexto: {contexto})")
        if any(c in "*^|,[]" for c in texto):
            raise ValueError(
                f"v3: literal contem char reservado: {texto!r}")

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
                            self._validar_literal(
                                s[a:b], f"eid={eid} pos={a}..{b}")
                            elementos.append(('lit', s[a:b]))
                        pos = el
                    elif isinstance(tok, TokRefPref):
                        ref_eid = tok.string_id
                        herdados = [(a, b, idx)
                                     for (a, b, idx) in frags_por_no[ref_eid]
                                     if a < tok.length and b <= tok.length]
                        for (a, b, idx) in herdados:
                            frags_por_no[eid].append((pos + a, pos + b, idx))
                            elementos.append(('ref', idx))
                        pos += tok.length
                    else:
                        ref_eid = tok.string_id
                        s_ref = strings_unicas[ref_eid - 1]
                        rs = len(s_ref) - tok.length
                        herdados = [(a, b, idx)
                                     for (a, b, idx) in frags_por_no[ref_eid]
                                     if a >= rs and b > rs]
                        for (a, b, idx) in herdados:
                            frags_por_no[eid].append(
                                (pos + (a - rs), pos + (b - rs), idx))
                            elementos.append(('ref', idx))
                        pos += tok.length

                # Emitir: literais consecutivos separados por *,
                # refs adjacentes separadas por ',' (em sequencia)
                partes = []
                prev_tipo = None
                for tipo, val in elementos:
                    if tipo == 'lit':
                        if prev_tipo == 'lit':
                            partes.append('*')
                        partes.append(val)
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

    def _parse_decl(self, resto: str,
                     frags: dict[int, str],
                     proximo_idx_ref: list[int]) -> str:
        """Parse uma linha de decl (sem prefixo de count nem ^N)."""
        partes = []
        i = 0
        n = len(resto)
        while i < n:
            ch = resto[i]
            if ch == '*':
                i += 1  # separador, pula
            elif ch.isdigit():
                j = i
                while j < n and (resto[j].isdigit() or resto[j] == ','):
                    j += 1
                for r in resto[i:j].split(','):
                    if r:
                        partes.append(frags[int(r)])
                i = j
            else:
                # literal: vai ate proximo digito, '*', ou fim
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
