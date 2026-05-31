"""M6.A — M2.A inline (sem preambulo).

Detector identico ao M2.A original (sufixos K>=3 com net positivo).
Serializacao INLINE: 1a aparicao do alias e' `$N=tupla` em linha;
demais sao `$N`. SEM bloco de preambulo.

Decoder: ve `$N=tupla` → registra alias; ve `$N` (sem `=`) → expande.

Net per alias R-uso de Lr chars:
  inline_savings = R*(Lr-1-len(N)) - (Lr+1)
  preambulo_savings = R*(Lr-1-len(N)) - (Lr+3+len(N))
  inline e' 2+len(N) bytes melhor.
"""

import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from online import Token, TokLit, TokRefPref, TokRefSuf
from syntax_base import Syntax


class M6AM2AInlineSyntax(Syntax):

    name = "M6-A-m2a-inline"

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

    @staticmethod
    def _escape_e_termina_em_digito(text):
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
            elif c in ('*', '\\', '$'):
                out.append('\\')
                out.append(c)
                termina_seq_digito = False
                i += 1
            else:
                out.append(c)
                termina_seq_digito = False
                i += 1
        return ''.join(out), termina_seq_digito

    @staticmethod
    def _emit_refs_range(refs):
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

    def _detectar_aliases(self, runs_por_linha):
        """Detector de sufixos K>=3 com greedy iterativo + net positivo."""
        runs_flat = []
        for runs in runs_por_linha:
            for r in runs:
                if len(r) >= 3:
                    runs_flat.append(tuple(r))

        alias_para_tupla = {}
        proximo_id = 1

        while proximo_id <= 99:
            sufixos = Counter()
            for tupla in runs_flat:
                for k in range(3, len(tupla) + 1):
                    sufixos[tupla[-k:]] += 1

            melhor_net = 0
            melhor_tupla = None
            n_tam = len(str(proximo_id))
            for tupla, R in sufixos.items():
                if R < 2:
                    continue
                Lt_serial = len(self._emit_refs_range(list(tupla)))
                economia_uso = Lt_serial - 1 - n_tam
                # Inline: 1a aparicao $N=tupla = 1+n_tam+1+Lt = Lt+2+n_tam (vs Lt raw → +2+n_tam)
                # (R-1) usos: $N = 1+n_tam (vs Lt raw → -economia_uso)
                # net = (R-1)*economia_uso - (2+n_tam)
                if economia_uso <= 0:
                    continue
                net = (R - 1) * economia_uso - (2 + n_tam)
                if net > melhor_net:
                    melhor_net = net
                    melhor_tupla = tupla

            if melhor_tupla is None:
                break

            alias_para_tupla[melhor_tupla] = proximo_id
            proximo_id += 1

            nova_runs_flat = []
            k_sufixo = len(melhor_tupla)
            for tupla in runs_flat:
                if (len(tupla) >= k_sufixo
                        and tupla[-k_sufixo:] == melhor_tupla):
                    prefixo = tupla[:-k_sufixo]
                    if len(prefixo) >= 3:
                        nova_runs_flat.append(prefixo)
                else:
                    nova_runs_flat.append(tupla)
            runs_flat = nova_runs_flat

        return alias_para_tupla

    def _aplicar_alias_uso(self, refs, alias_para_tupla, aliases_definidos):
        """Serializa refs aplicando o maior sufixo aliasable. Detector
        ja' garantiu net positivo; aplicar sempre que matchar."""
        n = len(refs)
        for k in range(n, 1, -1):
            sufixo = tuple(refs[-k:])
            if sufixo in alias_para_tupla:
                alias_id = alias_para_tupla[sufixo]
                prefixo_refs = refs[:n - k]
                tupla_serial = self._emit_refs_range(list(sufixo))
                if alias_id in aliases_definidos:
                    alias_str = f"${alias_id}"
                    acao = (alias_id, 'use')
                else:
                    alias_str = f"${alias_id}={tupla_serial}"
                    acao = (alias_id, 'def')
                if prefixo_refs:
                    pre = self._emit_refs_range(prefixo_refs)
                    candidato = f"{pre},{alias_str}"
                else:
                    candidato = alias_str
                return candidato, acao
        return self._emit_refs_range(refs), None

    def encode(self, linhas_originais, strings_unicas,
                tokens_por_string, header):
        quebras = self._coletar_quebras(strings_unicas, tokens_por_string)
        unica_to_eid = {s: i + 1 for i, s in enumerate(strings_unicas)}

        frags_por_no = {}
        proximo_idx = 1
        eid_emitido = set()
        linhas_dados = []

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
                eid_emitido.add(eid)
                linhas_dados.append((s_run, count, elementos, eid, False))
            else:
                linhas_dados.append((s_run, count, None, eid, True))

        # Coletar runs por linha para detector
        runs_por_linha = []
        for s_run, count, elementos, eid, is_rep in linhas_dados:
            if is_rep or elementos is None:
                continue
            runs = []
            cur = []
            for elem in elementos:
                if elem[0] == 'ref':
                    cur.append(elem[1])
                else:
                    if cur:
                        runs.append(cur)
                        cur = []
            if cur:
                runs.append(cur)
            runs_por_linha.append(runs)

        alias_para_tupla = self._detectar_aliases(runs_por_linha)

        # Serializar — INLINE: 1a aparicao define, demais usam
        aliases_definidos = set()
        body_linhas = []
        for s_run, count, elementos, eid, is_rep in linhas_dados:
            if is_rep:
                linha_resto = f"^{eid}"
            else:
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
                        serializado, acao = self._aplicar_alias_uso(
                            refs, alias_para_tupla, aliases_definidos)
                        partes.append(serializado)
                        if acao is not None and acao[1] == 'def':
                            aliases_definidos.add(acao[0])
                        prev_tipo = 'ref'
                linha_resto = ''.join(partes)

            if count > 1:
                body_linhas.append(f"*{count}|{linha_resto}")
            else:
                body_linhas.append(linha_resto)

        return "\n".join(["[", *body_linhas, "]"]) + "\n"

    # ---- decode ----

    def _parse_decl(self, resto, frags, proximo_idx_ref, aliases):
        partes = []
        i = 0
        n = len(resto)
        while i < n:
            ch = resto[i]
            if ch == '*':
                i += 1
            elif ch == '$':
                # alias use OR def: $N or $N=tupla
                j = i + 1
                while j < n and resto[j].isdigit():
                    j += 1
                alias_id = int(resto[i + 1:j])
                if j < n and resto[j] == '=':
                    # def inline: $N=tupla
                    j += 1
                    k = j
                    while k < n:
                        c = resto[k]
                        if c.isdigit() or c == ',':
                            k += 1
                        elif c == '.' and k + 1 < n and resto[k + 1] == '.':
                            k += 2
                        else:
                            break
                    refs_str = resto[j:k]
                    refs_lista = []
                    for r in refs_str.split(','):
                        if not r:
                            continue
                        if '..' in r:
                            a, b = r.split('..')
                            for v in range(int(a), int(b) + 1):
                                refs_lista.append(v)
                        else:
                            refs_lista.append(int(r))
                    aliases[alias_id] = refs_lista
                    for f_id in refs_lista:
                        partes.append(frags[f_id])
                    i = k
                else:
                    # uso: $N
                    for f_id in aliases[alias_id]:
                        partes.append(frags[f_id])
                    i = j
            elif ch.isdigit():
                # refs normais
                j = i
                while j < n:
                    c = resto[j]
                    if c.isdigit() or c == ',':
                        j += 1
                    elif c == '.' and j + 1 < n and resto[j + 1] == '.':
                        j += 2
                    elif c == '$':
                        break
                    else:
                        break
                refs_str = resto[i:j]
                for r in refs_str.split(','):
                    if not r:
                        continue
                    if '..' in r:
                        a, b = r.split('..')
                        for v in range(int(a), int(b) + 1):
                            partes.append(frags[v])
                    else:
                        partes.append(frags[int(r)])
                i = j
            else:
                # literal com escape escopo
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
                    elif c.isdigit() or c in ('*', '$'):
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
        aliases = {}

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
                s_no = self._parse_decl(resto, frags, proximo_idx_ref, aliases)
                nos_decl.append(s_no)

            saida.extend([s_no] * count)
        return saida
