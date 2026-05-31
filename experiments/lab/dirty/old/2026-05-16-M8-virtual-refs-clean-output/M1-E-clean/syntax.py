"""M1.E — Range de refs sequenciais.

Tecnica ortogonal ao escape/quote: quando refs consecutivas formam
sequencia aritmetica `n, n+1, n+2, ...`, agrupar como `a..b`.

Sintaxe: `a..b` (dois pontos consecutivos). Escolha de `..` em vez
de `[a-b]` por:
- `[` colide com literal `[` em datasets caos (D4) e com delimitador
  de body. Reservar `[` so' para o body simplifica.
- `a..b` tem 2 chars de overhead vs `[a-b]` com 5 — limiar K menor.

Custos (refs de 1 digito):
- K=2: `1,2` = 3 chars, `1..2` = 4. M1.E perde.
- K=3: `1,2,3` = 5 chars, `1..3` = 4. Ganho 1.
- K=4: `1,2,3,4` = 7 chars, `1..4` = 4. Ganho 3.
- K=N (1 digito): ganho = 2N - 5 (para N>=3).

Para refs com mais digitos (idx 10+), ganho cresce ainda mais.

Mistura: `1,2,3,4,8,9` -> runs greedy [1..4],[8,9] -> `1..4,8,9`.

Esta sintaxe herda escape com escopo de M1.A' para a parte literal
(M1.A' venceu em bytes literais nos 4 datasets, ortogonal a range).

Decoder: estende parser de refs com lookahead `..` (so' consome
ponto se for `..` consecutivo). Literais com `.` unico (`.com`,
`.json`) seguem intocados.

Implementado do zero (sem importar M1.A' nem reaproveitar codigo).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from online import Token, TokLit, TokRefPref, TokRefSuf
from syntax_base import Syntax


class M1ERangeSyntax(Syntax):

    name = "M1-E-clean"

    # ---- analise de quebras (mesma logica que M1.A/B/A') ----

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

    # ---- escape com escopo (igual M1.A') ----

    @staticmethod
    def _escape_e_termina_em_digito(text: str) -> tuple[str, bool]:
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

    # ---- agrupamento range em refs consecutivas ----

    @staticmethod
    def _emit_refs(refs: list[int]) -> str:
        """Emite refs consecutivas. Detecta runs aritmeticos +1 com
        K>=3 e serializa como `a..b`. Mistura com refs isoladas
        preservando virgulas.

        Exemplos:
          [5]                  -> "5"
          [5, 7]               -> "5,7"
          [1, 2]               -> "1,2"        (K=2 nao agrupa)
          [1, 2, 3]            -> "1..3"
          [1, 2, 3, 4]         -> "1..4"
          [1, 2, 3, 4, 8, 9]   -> "1..4,8,9"
          [1, 5, 6, 7, 8]      -> "1,5..8"
        """
        if not refs:
            return ""
        runs = []
        cur = [refs[0]]
        for r in refs[1:]:
            if r == cur[-1] + 1:
                cur.append(r)
            else:
                runs.append(cur)
                cur = [r]
        runs.append(cur)
        partes = []
        for run in runs:
            if len(run) >= 3:
                partes.append(f"{run[0]}..{run[-1]}")
            else:
                partes.extend(str(r) for r in run)
        return ",".join(partes)

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

                # Montar linha: acumular runs de refs consecutivas e
                # emiti-las via _emit_refs (com ranges quando K>=3).
                partes = []
                prev_tipo = None
                prev_lit_termina_seq_digito = False
                i = 0
                n_elem = len(elementos)
                while i < n_elem:
                    tipo, val = elementos[i]
                    if tipo == 'lit':
                        if prev_tipo == 'lit':
                            partes.append('*')
                        emitido, term_seq = self._escape_e_termina_em_digito(val)
                        partes.append(emitido)
                        prev_lit_termina_seq_digito = term_seq
                        prev_tipo = 'lit'
                        i += 1
                    else:
                        refs = []
                        while i < n_elem and elementos[i][0] == 'ref':
                            refs.append(elementos[i][1])
                            i += 1
                        if prev_lit_termina_seq_digito:
                            partes.append('*')
                            prev_lit_termina_seq_digito = False
                        partes.append(self._emit_refs(refs))
                        prev_tipo = 'ref'
                linha_resto = ''.join(partes)
                eid_emitido.add(eid)
            else:
                linha_resto = f"^{eid}"

            if count > 1:
                body_linhas.append(f"*{count}|{linha_resto}")
            else:
                body_linhas.append(linha_resto)

        return "\n".join(body_linhas) + "\n"

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
                # refs (com possivel range n..m). Consome digitos,
                # virgulas, e `..` (so' se for `..` consecutivo).
                j = i
                while j < n:
                    c = resto[j]
                    if c.isdigit() or c == ',':
                        j += 1
                    elif c == '.' and j + 1 < n and resto[j + 1] == '.':
                        j += 2
                    else:
                        break
                refs_str = resto[i:j]
                for r in refs_str.split(','):
                    if not r:
                        continue
                    if '..' in r:
                        a_str, b_str = r.split('..')
                        a, b = int(a_str), int(b_str)
                        for k in range(a, b + 1):
                            partes.append(frags[k])
                    else:
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
                            j = i
                            while j < n and resto[j].isdigit():
                                j += 1
                            buf.append(resto[i:j])
                            i = j
                        else:
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
