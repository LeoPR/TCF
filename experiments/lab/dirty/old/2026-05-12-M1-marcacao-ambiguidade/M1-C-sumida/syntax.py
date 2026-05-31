"""M1.C — Sumida (parser stateful elimina escape redundante).

Tecnica: quando o frag literal e' uma seq de digitos PURA (sem
outros chars) e o numero supera `max_idx_visivel` no ponto em que
e' declarado, o parser-decoder sabe que nao pode ser ref → e' literal.
Encoder omite o `\\` escape escopo nesses casos.

Combina com range (M1.E) e escape com escopo (M1.A') para os casos
em que ainda e' necessario escapar.

Custos vs M1.E:
- Cada frag literal puro-digitos com int > max_idx_visivel e sem
  leading-zero: economiza 1 byte (o `\\`).
- Frags com leading-zero (`00`, `042`): NAO suprime (parser ambiguo
  com int-leading-zero).
- Frags mistos (`users/00`, `42abc`): NAO suprime (decoder confundiria
  fronteira lit/ref).

Decoder: em ref-context, ao ler seq de digitos PURA (sem `,` nem
`..`), checa se int > max_idx_visivel atual. Se sim, trata seq inteira
como literal novo (aloca novo idx). Senao, processa como ref.

Implementado do zero (sem importar M1.E nem M1.A' antigos).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from online import Token, TokLit, TokRefPref, TokRefSuf
from syntax_base import Syntax


class M1CSumidaSyntax(Syntax):

    name = "M1-C-sumida"

    # ---- analise de quebras (mesma logica de M1.A/B/A'/E) ----

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

    # ---- escape com escopo + supressao quando seguro ----

    @staticmethod
    def _escape_e_termina_em_digito(text: str, max_visivel_antes: int) -> tuple[str, bool]:
        """Escapa chars ambiguos. Suprime escape se frag inteiro for
        seq de digitos pura, sem leading-zero, e int(text) >
        max_visivel_antes (parser nao pode confundir com ref).

        Retorna (texto_emitido, terminou_com_seq_digitos).
        """
        # Caso especial: frag inteiro e' puro-digit sem leading-zero
        # E int > max_visivel_antes → emite cru (sem `\`).
        if text and text.isdigit() and text[0] != '0' \
                and int(text) > max_visivel_antes:
            return text, True

        # Senao, comportamento M1.A' (escape escopo de sub-seqs)
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

    # ---- agrupamento range (igual M1.E) ----

    @staticmethod
    def _lit_sera_sumido(text: str, max_visivel_antes: int) -> bool:
        """Mesma regra usada por _escape_e_termina_em_digito para
        decidir supressao de escape. Util para encoder decidir se
        precisa separador `*` antes deste literal."""
        return (bool(text) and text.isdigit() and text[0] != '0'
                and int(text) > max_visivel_antes)

    @staticmethod
    def _emit_refs(refs: list[int]) -> str:
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
                # elementos: ('lit', text, max_visivel_antes) ou ('ref', idx)
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
                            max_antes = idx - 1
                            proximo_idx += 1
                            frags_por_no[eid].append((a, b, idx))
                            elementos.append(('lit', s[a:b], max_antes))
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

                # Montar linha
                # prev_emit_termina_em_digito: True se ultimo emit
                # terminou em digit-seq (refs SEMPRE terminam em digit;
                # literais terminam em digit se escape escopo final ou
                # se foi sumido).
                partes = []
                prev_tipo = None
                prev_emit_termina_em_digito = False
                i = 0
                n_elem = len(elementos)
                while i < n_elem:
                    elem = elementos[i]
                    tipo = elem[0]
                    if tipo == 'lit':
                        _, val, max_antes = elem
                        will_be_sumido = self._lit_sera_sumido(val, max_antes)
                        if prev_tipo == 'lit':
                            # lit-lit consecutivos sempre precisam de '*'
                            partes.append('*')
                        elif prev_tipo == 'ref' and will_be_sumido:
                            # ref-emit termina em digit; lit sumido comeca
                            # com digit. Sem '*' o parser une os dois.
                            partes.append('*')
                        emitido, term_seq = self._escape_e_termina_em_digito(
                            val, max_antes)
                        partes.append(emitido)
                        prev_emit_termina_em_digito = term_seq
                        prev_tipo = 'lit'
                        i += 1
                    else:
                        refs = []
                        while i < n_elem and elementos[i][0] == 'ref':
                            refs.append(elementos[i][1])
                            i += 1
                        if prev_emit_termina_em_digito:
                            # lit anterior terminou em digit-seq; sem '*'
                            # parser une com a primeira ref (digit tambem).
                            partes.append('*')
                        partes.append(self._emit_refs(refs))
                        prev_emit_termina_em_digito = True
                        prev_tipo = 'ref'
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
                # refs (com possivel range n..m) ou literal sumido
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

                # Checar se e' literal sumido: seq PURA digitos (sem ',' nem '..')
                # com int > max_idx_visivel e sem leading-zero.
                if ',' not in refs_str and '..' not in refs_str:
                    max_idx = proximo_idx_ref[0] - 1
                    num = int(refs_str)
                    if refs_str[0] != '0' and num > max_idx:
                        # literal sumido — registra como novo frag
                        frags[proximo_idx_ref[0]] = refs_str
                        partes.append(refs_str)
                        proximo_idx_ref[0] += 1
                        i = j
                        continue

                # Caso contrario: processa como refs/ranges (igual M1.E)
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
                # literal com escape `\X` ou escape escopo `\<digits>`
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
