"""M5.A — Detector hibrido M2.A (preambulo) + M4.C1' (inline).

Cada candidato (subseq contigua K >= 2) e' avaliado sob AMBAS
sintaxes; seleciona o de maior net global. Aliases coexistem em
namespaces separados (`$N` preambulo, `&N` inline).

Algebra (esperada):
  M2.A_net  = R*(Lr-1-len(N)) - (Lr+3+len(N))
  M4C1p_net = (R-1)*(Lr-1-len(N)) - 2
  diff      = -2 - 2*len(N)  → M4.C1' sempre vence

Esperado empirico: 0 aliases M2.A selecionados.
"""

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from online import Token, TokLit, TokRefPref, TokRefSuf
from syntax_base import Syntax


class M5APilhaHibridaSyntax(Syntax):

    name = "M5-A-pilha-hibrida"

    # ---- helpers identicos a M4.C1' ----

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
            elif c in ('*', '\\', '&', '~', '$'):
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

    # ---- encode ----

    def encode(self, linhas_originais, strings_unicas,
                tokens_por_string, header):
        quebras = self._coletar_quebras(strings_unicas, tokens_por_string)
        unica_to_eid = {s: i + 1 for i, s in enumerate(strings_unicas)}

        # FASE 1: gerar pedacos base (igual M4.C1')
        frags_por_no = {}
        proximo_idx = 1
        eid_emitido = set()
        linha_pedacos = []
        linha_meta = []

        for s_run, count in self._rle_adjacente(linhas_originais):
            eid = unica_to_eid[s_run]
            if eid not in eid_emitido:
                s = strings_unicas[eid - 1]
                tokens = tokens_por_string[eid - 1]
                qa = quebras[eid]
                frags_por_no[eid] = []
                base = []
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
                            base.append(('lit', s[a:b]))
                        pos = el
                    elif isinstance(tok, TokRefPref):
                        herdados = [(a, b, idx)
                                     for (a, b, idx) in frags_por_no[tok.string_id]
                                     if a < tok.length and b <= tok.length]
                        for (a, b, idx) in herdados:
                            frags_por_no[eid].append((pos + a, pos + b, idx))
                            base.append(('ref', idx))
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
                            base.append(('ref', idx))
                        pos += tok.length
                pedacos = []
                i = 0
                while i < len(base):
                    tipo, val = base[i]
                    if tipo == 'ref':
                        run = [val]
                        i += 1
                        while i < len(base) and base[i][0] == 'ref':
                            run.append(base[i][1])
                            i += 1
                        pedacos.append(('refs', run))
                    else:
                        pedacos.append(('lit', val))
                        i += 1
                linha_pedacos.append(pedacos)
                linha_meta.append((count, eid, False))
                eid_emitido.add(eid)
            else:
                linha_pedacos.append(None)
                linha_meta.append((count, eid, True))

        # FASE 2-4: detector iterativo HIBRIDO
        proximo_alias_m2 = 1
        proximo_alias_m4 = 1
        aliases_selecionados = []  # lista de (tipo, id, sub)
        iter_count = 0
        while iter_count < 99:
            iter_count += 1
            contagem = Counter()
            for pedacos in linha_pedacos:
                if pedacos is None:
                    continue
                for p in pedacos:
                    if p[0] == 'refs':
                        refs = p[1]
                        L = len(refs)
                        for a in range(L):
                            for b in range(a + 2, L + 1):
                                sub = tuple(refs[a:b])
                                contagem[sub] += 1

            # Avalia cada candidato sob AMBAS sintaxes
            melhor = None
            melhor_net = 0
            melhor_tipo = None  # 'm2' ou 'm4'
            n_tam_m2 = len(str(proximo_alias_m2))
            n_tam_m4 = len(str(proximo_alias_m4))
            for sub, R in contagem.items():
                if R < 2:
                    continue
                Lr = len(self._emit_refs_range(list(sub)))

                # M2.A net
                eco_uso_m2 = Lr - 1 - n_tam_m2
                if eco_uso_m2 > 0:
                    net_m2 = R * eco_uso_m2 - (Lr + 3 + n_tam_m2)
                else:
                    net_m2 = -10**9

                # M4.C1' net
                eco_uso_m4 = Lr - 1 - n_tam_m4
                if eco_uso_m4 > 0:
                    net_m4 = (R - 1) * eco_uso_m4 - 2
                else:
                    net_m4 = -10**9

                # escolhe o maior dos dois
                if net_m4 >= net_m2:
                    candidato_net = net_m4
                    candidato_tipo = 'm4'
                else:
                    candidato_net = net_m2
                    candidato_tipo = 'm2'

                if candidato_net > melhor_net:
                    melhor_net = candidato_net
                    melhor = (sub, R, Lr)
                    melhor_tipo = candidato_tipo

            if melhor is None:
                break

            sub, R, Lr = melhor
            if melhor_tipo == 'm4':
                aid = proximo_alias_m4
                proximo_alias_m4 += 1
            else:
                aid = proximo_alias_m2
                proximo_alias_m2 += 1
            aliases_selecionados.append((melhor_tipo, aid, list(sub)))

            for li in range(len(linha_pedacos)):
                pedacos = linha_pedacos[li]
                if pedacos is None:
                    continue
                novos = []
                for p in pedacos:
                    if p[0] != 'refs':
                        novos.append(p)
                        continue
                    refs = p[1]
                    i = 0
                    buf = []
                    while i < len(refs):
                        if (i + len(sub) <= len(refs)
                                and tuple(refs[i:i+len(sub)]) == sub):
                            if buf:
                                novos.append(('refs', buf))
                                buf = []
                            novos.append(('alias_marker',
                                           melhor_tipo, aid, list(sub)))
                            i += len(sub)
                        else:
                            buf.append(refs[i])
                            i += 1
                    if buf:
                        novos.append(('refs', buf))
                linha_pedacos[li] = novos

        # FASE 5: para M4 aliases, marca 1a ocorrencia global como def
        m4_def_feito = set()
        for li in range(len(linha_pedacos)):
            pedacos = linha_pedacos[li]
            if pedacos is None:
                continue
            novos = []
            for p in pedacos:
                if p[0] == 'alias_marker':
                    tipo, aid, sub = p[1], p[2], p[3]
                    if tipo == 'm4':
                        if aid not in m4_def_feito:
                            novos.append(('m4_def_inline', aid, sub))
                            m4_def_feito.add(aid)
                        else:
                            novos.append(('m4_use', aid))
                    else:  # m2
                        novos.append(('m2_use', aid))
                else:
                    novos.append(p)
            linha_pedacos[li] = novos

        # FASE 6: renumera M4 aliases por ordem de 1a definicao
        m4_remap = {}
        contador = 1
        for li in range(len(linha_pedacos)):
            pedacos = linha_pedacos[li]
            if pedacos is None:
                continue
            for p in pedacos:
                if p[0] == 'm4_def_inline' and p[1] not in m4_remap:
                    m4_remap[p[1]] = contador
                    contador += 1
        # M2 aliases: ordem do preambulo segue ordem de selecao
        # (proximo_alias_m2 ja' era sequencial)
        for li in range(len(linha_pedacos)):
            pedacos = linha_pedacos[li]
            if pedacos is None:
                continue
            novos = []
            for p in pedacos:
                if p[0] == 'm4_def_inline':
                    novos.append(('m4_def_inline',
                                   m4_remap[p[1]], p[2]))
                elif p[0] == 'm4_use':
                    novos.append(('m4_use', m4_remap[p[1]]))
                else:
                    novos.append(p)
            linha_pedacos[li] = novos

        # FASE 7: emitir preambulo M2 + body
        preambulo_m2 = []
        m2_aliases = [a for a in aliases_selecionados if a[0] == 'm2']
        for tipo, aid, sub in m2_aliases:
            preambulo_m2.append(f"${aid}={self._emit_refs_range(sub)}")

        body_linhas = []
        for li, (count, eid, is_rep) in enumerate(linha_meta):
            if is_rep:
                linha_resto = f"^{eid}"
            else:
                partes = []
                prev_tipo = None
                prev_emit_termina_em_digito = False
                for p in linha_pedacos[li]:
                    t = p[0]
                    if t == 'lit':
                        if prev_tipo == 'lit':
                            partes.append('*')
                        emitido, term_seq = self._escape_e_termina_em_digito(p[1])
                        partes.append(emitido)
                        prev_emit_termina_em_digito = term_seq
                        prev_tipo = 'lit'
                    elif t == 'refs':
                        if prev_tipo == 'refs':
                            partes.append(',')
                        elif prev_tipo == 'lit' and prev_emit_termina_em_digito:
                            partes.append('*')
                        elif prev_tipo in ('m4_use', 'm2_use'):
                            partes.append(',')
                        # m4_def_inline termina em `~` (nao-digit), sem sep
                        partes.append(self._emit_refs_range(p[1]))
                        prev_emit_termina_em_digito = True
                        prev_tipo = 'refs'
                    elif t == 'm4_def_inline':
                        aid = p[1]
                        sub = p[2]
                        if prev_tipo == 'refs':
                            partes.append(',')
                        partes.append('~')
                        partes.append(self._emit_refs_range(sub))
                        partes.append('~')
                        prev_emit_termina_em_digito = False
                        prev_tipo = 'm4_def_inline'
                    elif t == 'm4_use':
                        if prev_tipo == 'refs':
                            partes.append(',')
                        partes.append(f"&{p[1]}")
                        prev_emit_termina_em_digito = True
                        prev_tipo = 'm4_use'
                    elif t == 'm2_use':
                        if prev_tipo == 'refs':
                            partes.append(',')
                        partes.append(f"${p[1]}")
                        prev_emit_termina_em_digito = True
                        prev_tipo = 'm2_use'
                linha_resto = ''.join(partes)

            if count > 1:
                body_linhas.append(f"*{count}|{linha_resto}")
            else:
                body_linhas.append(linha_resto)

        if preambulo_m2:
            return "\n".join(["[", *preambulo_m2, *body_linhas, "]"]) + "\n"
        else:
            return "\n".join(["[", *body_linhas, "]"]) + "\n"

    # ---- decode ----

    def _parse_alias_decl_m2(self, linha):
        eq = linha.find('=')
        n = int(linha[1:eq])
        resto = linha[eq + 1:]
        refs = []
        for p in resto.split(','):
            if '..' in p:
                a, b = p.split('..')
                for v in range(int(a), int(b) + 1):
                    refs.append(v)
            else:
                refs.append(int(p))
        return n, refs

    def _parse_decl(self, resto, frags, proximo_idx_ref,
                     m4_aliases, m2_aliases):
        partes = []
        i = 0
        n = len(resto)
        while i < n:
            ch = resto[i]
            if ch == '*':
                i += 1
            elif ch == ',':
                i += 1
            elif ch == '~':
                # def alias M4: ~SUBSEQ~
                i += 1
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
                if j >= n or resto[j] != '~':
                    raise ValueError(f"alias M4 def sem ~ final em pos {i}: "
                                     f"{resto!r}")
                expandido = []
                for r in refs_str.split(','):
                    if not r:
                        continue
                    if '..' in r:
                        a, b = r.split('..')
                        for v in range(int(a), int(b) + 1):
                            expandido.append(frags[v])
                    else:
                        expandido.append(frags[int(r)])
                texto_alias = ''.join(expandido)
                next_id = len(m4_aliases) + 1
                m4_aliases[next_id] = texto_alias
                partes.append(texto_alias)
                i = j + 1
            elif ch == '&':
                # uso alias M4: &N
                j = i + 1
                while j < n and resto[j].isdigit():
                    j += 1
                alias_id = int(resto[i + 1:j])
                partes.append(m4_aliases[alias_id])
                i = j
            elif ch == '$':
                # uso alias M2: $N (sempre uso na body — decl ja' processada)
                j = i + 1
                while j < n and resto[j].isdigit():
                    j += 1
                alias_id = int(resto[i + 1:j])
                refs_m2 = m2_aliases[alias_id]
                for r in refs_m2:
                    partes.append(frags[r])
                i = j
            elif ch.isdigit():
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
                    elif c.isdigit() or c in ('*', '&', '~', '$'):
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
        m4_aliases = {}  # id → texto
        m2_aliases = {}  # id → list of frag ids

        for raw in tcf_text.splitlines():
            linha = raw.strip()
            if not linha or linha in ("[", "]"):
                continue

            # detectar declaracao de alias M2 (preambulo)
            if linha.startswith('$') and '=' in linha and '|' not in linha[:linha.find('=')]:
                n, refs = self._parse_alias_decl_m2(linha)
                m2_aliases[n] = refs
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
                s_no = self._parse_decl(
                    resto, frags, proximo_idx_ref, m4_aliases, m2_aliases)
                nos_decl.append(s_no)

            saida.extend([s_no] * count)
        return saida
