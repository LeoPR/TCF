"""M3.B — Encadeamento de declaracoes (`&N=&P+ext`).

Estende M3.A. Detector identifica substrings compartilhadas e
verifica se existe substring ja' declarada cujo texto e' prefixo
desta. Se sim, declara encadeada (`&N=&P+ext`); senao, absoluta
(`&N=texto`).

Custos:
- Decl absoluta: `&N=texto\\n` = 4 + Lt
- Decl encadeada: `&N=&P+ext\\n` = 5 + len(str(P)) + len(ext)

Encadeada compensa absoluta quando:
    5 + len(P) + len(ext) < 4 + Lt
    → len(ext) < Lt - 1 - len(P)
    Para P de 1 digito: len(ext) < Lt - 2

Em hierarquia profunda (cadeias de 3+ niveis), encadeamento
acumula reducao no preambulo. Em hierarquia rasa (1-2 niveis),
diferenca para M3.A absoluta e' minima.

Decoder resolve recursivamente: ao ver `&P+ext`, expande &P e
concatena ext.
"""

import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from online import Token, TokLit, TokRefPref, TokRefSuf
from syntax_base import Syntax


class M3BEncadeamentoSyntax(Syntax):

    name = "M3-B-encadeamento"

    # ---- helpers identicos a M3.A ----

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
            elif c == '*' or c == '\\' or c == '&':
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
    def _emit_refs_range(refs: list[int]) -> str:
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
        elementos_por_eid = {}
        candidatos_subs = defaultdict(list)
        texto_sub = {}
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
                        refs_idx = [idx for (a, b, idx) in herdados]
                        for (a, b, idx) in herdados:
                            frags_por_no[eid].append((pos + a, pos + b, idx))
                        elementos.append(('sub', tok.string_id, 'P',
                                            tok.length, refs_idx))
                        key = (tok.string_id, 'P', tok.length)
                        candidatos_subs[key].append(eid)
                        s_orig = strings_unicas[tok.string_id - 1]
                        texto_sub[key] = s_orig[:tok.length]
                        pos += tok.length
                    else:
                        s_ref = strings_unicas[tok.string_id - 1]
                        rs = len(s_ref) - tok.length
                        herdados = [(a, b, idx)
                                     for (a, b, idx) in frags_por_no[tok.string_id]
                                     if a >= rs and b > rs]
                        refs_idx = [idx for (a, b, idx) in herdados]
                        for (a, b, idx) in herdados:
                            frags_por_no[eid].append(
                                (pos + (a - rs), pos + (b - rs), idx))
                        elementos.append(('sub', tok.string_id, 'S',
                                            tok.length, refs_idx))
                        key = (tok.string_id, 'S', tok.length)
                        candidatos_subs[key].append(eid)
                        texto_sub[key] = s_ref[-tok.length:]
                        pos += tok.length
                eid_emitido.add(eid)
                elementos_por_eid[eid] = elementos
                linhas_dados.append((s_run, count, eid, False))
            else:
                linhas_dados.append((s_run, count, eid, True))

        # FASE 2: detector com cadeia
        # Avaliar todas substrings com R >= 2 e net (absoluto) > 0
        candidatos_avaliados = []
        for key, eid_users in candidatos_subs.items():
            R = len(eid_users)
            if R < 2:
                continue
            eid_origem, tipo, length = key
            texto = texto_sub[key]
            Lt = len(texto)
            primeiro_eid = eid_users[0]
            elem_lista = elementos_por_eid[primeiro_eid]
            Lr = None
            for elem in elem_lista:
                if (elem[0] == 'sub' and elem[1] == eid_origem
                        and elem[2] == tipo and elem[3] == length):
                    refs_idx = elem[4]
                    Lr = len(self._emit_refs_range(refs_idx))
                    break
            if Lr is None or Lr <= 2:
                continue
            economia_uso = Lr - 2
            custo_decl_abs = 4 + Lt  # `&N=texto\n` para N=1 digit
            net_abs = R * economia_uso - custo_decl_abs
            if net_abs > 0:
                candidatos_avaliados.append(
                    (R, key, Lr, Lt, texto, net_abs))

        # Ordena por R decrescente (substrings com mais usos primeiro)
        candidatos_avaliados.sort(key=lambda c: -c[0])

        # Seleciona e tenta encadear
        # selecionados_lista: lista ordenada de (key, alias_id, texto, modo, parent_id, ext)
        #   modo = 'abs' ou 'chain'
        #   parent_id = id de outro alias (para chain) ou None
        #   ext = string extensao (para chain) ou None
        selecionados_lista = []
        texto_para_id = {}  # texto → alias_id (para detectar pais)

        for R, key, Lr, Lt, texto, net_abs in candidatos_avaliados:
            if len(selecionados_lista) >= 9:
                break
            alias_id = len(selecionados_lista) + 1

            # Tentar encontrar pai: maior alias ja' selecionado cujo
            # texto e' prefixo PROPRIO de `texto` (e diferente)
            melhor_pai = None
            melhor_pai_texto = None
            for ptexto, pid in texto_para_id.items():
                if (texto.startswith(ptexto) and len(ptexto) < len(texto)
                        and (melhor_pai_texto is None
                              or len(ptexto) > len(melhor_pai_texto))):
                    melhor_pai = pid
                    melhor_pai_texto = ptexto

            if melhor_pai is not None:
                ext = texto[len(melhor_pai_texto):]
                # custo encadeado: `&N=&P+ext\n` = 5 + len(str(P)) + len(ext)
                custo_chain = 5 + len(str(melhor_pai)) + len(ext)
                if custo_chain < 4 + Lt:
                    selecionados_lista.append(
                        (key, alias_id, texto, 'chain', melhor_pai, ext))
                    texto_para_id[texto] = alias_id
                    continue
            # fallback: absoluto
            selecionados_lista.append(
                (key, alias_id, texto, 'abs', None, None))
            texto_para_id[texto] = alias_id

        key_to_alias = {tup[0]: tup[1] for tup in selecionados_lista}

        # FASE 3: serializar body
        body_linhas = []
        for s_run, count, eid, is_rep in linhas_dados:
            if is_rep:
                linha_resto = f"^{eid}"
            else:
                partes = []
                prev_tipo = None
                prev_emit_termina_em_digito = False
                elementos = elementos_por_eid[eid]
                i = 0
                n_elem = len(elementos)
                while i < n_elem:
                    elem = elementos[i]
                    tipo_e = elem[0]
                    if tipo_e == 'lit':
                        _, val = elem
                        if prev_tipo == 'lit':
                            partes.append('*')
                        emitido, term_seq = self._escape_e_termina_em_digito(val)
                        partes.append(emitido)
                        prev_emit_termina_em_digito = term_seq
                        prev_tipo = 'lit'
                        i += 1
                    elif tipo_e == 'sub':
                        _, eid_orig, sub_tipo, length, refs_idx = elem
                        key = (eid_orig, sub_tipo, length)
                        if key in key_to_alias:
                            alias_id = key_to_alias[key]
                            partes.append(f"&{alias_id}")
                            prev_emit_termina_em_digito = True
                            prev_tipo = 'sub'
                            i += 1
                        else:
                            refs_coletar = list(refs_idx)
                            i += 1
                            while i < n_elem:
                                e2 = elementos[i]
                                if e2[0] == 'sub' and (e2[1], e2[2], e2[3]) not in key_to_alias:
                                    refs_coletar.extend(e2[4])
                                    i += 1
                                else:
                                    break
                            if prev_emit_termina_em_digito:
                                partes.append('*')
                            partes.append(self._emit_refs_range(refs_coletar))
                            prev_emit_termina_em_digito = True
                            prev_tipo = 'ref'
                    else:
                        i += 1
                linha_resto = ''.join(partes)

            if count > 1:
                body_linhas.append(f"*{count}|{linha_resto}")
            else:
                body_linhas.append(linha_resto)

        # FASE 4: emitir preambulo + body
        preambulo = []
        for key, alias_id, texto, modo, parent_id, ext in selecionados_lista:
            if modo == 'abs':
                texto_emit = texto.replace('&', '\\&').replace('+', '\\+')
                preambulo.append(f"&{alias_id}={texto_emit}")
            else:  # chain
                ext_emit = ext.replace('&', '\\&').replace('+', '\\+')
                preambulo.append(f"&{alias_id}=&{parent_id}+{ext_emit}")

        if preambulo:
            return "\n".join(["[", *preambulo, *body_linhas, "]"]) + "\n"
        else:
            return "\n".join(["[", *body_linhas, "]"]) + "\n"

    # ---- decode ----

    def _parse_alias_decl(self, linha, aliases):
        """Parse `&N=texto` ou `&N=&P+ext`. Resolve encadeamento
        usando aliases ja' parseados."""
        eq = linha.find('=')
        n = int(linha[1:eq])
        rhs = linha[eq + 1:]
        if rhs.startswith('&'):
            # chain: &P+ext
            i = 1
            while i < len(rhs) and rhs[i].isdigit():
                i += 1
            parent_id = int(rhs[1:i])
            # esperar '+'
            if i >= len(rhs) or rhs[i] != '+':
                raise ValueError(f"chain malformado: {linha!r}")
            ext = rhs[i + 1:].replace('\\&', '&').replace('\\+', '+')
            texto = aliases[parent_id] + ext
        else:
            texto = rhs.replace('\\&', '&').replace('\\+', '+')
        return n, texto

    def _parse_decl(self, resto, frags, proximo_idx_ref, aliases):
        partes = []
        i = 0
        n = len(resto)
        while i < n:
            ch = resto[i]
            if ch == '*':
                i += 1
            elif ch == '&':
                j = i + 1
                while j < n and resto[j].isdigit():
                    j += 1
                alias_id = int(resto[i + 1:j])
                partes.append(aliases[alias_id])
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
                    elif c.isdigit() or c == '*' or c == '&':
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

            if linha.startswith('&') and '=' in linha:
                eq = linha.find('=')
                if linha[1:eq].isdigit():
                    n, texto = self._parse_alias_decl(linha, aliases)
                    aliases[n] = texto
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
