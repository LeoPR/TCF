"""M4.C1' — Batch greedy com idx implicito + subsequencias.

Estende M4.C1 v1 (runs inteiras) para detectar subsequencias
contiguas internas de runs maiores.

Sintaxe:
- 1a aparicao da subseq: `~SUBSEQ~` (par de marcadores)
- 2a+ aparicoes: `&N`
- Idx alocado por ordem de 1a aparicao no body

Custos:
- 1a def: `~SUBSEQ~` = Lr + 2 chars
- Uso: `&N` = 1 + len(str(N)) chars
- Net = (R-1)*(Lr - 1 - len(N)) - 2

Detector iterativo:
1. Coleta todas sub-tuplas contiguas (K >= 2) de cada run
2. Conta global
3. Escolhe maior net positivo
4. Substitui em todas runs (divide em pre + alias + pos)
5. Repete sobre runs modificadas

Custo O(N * L^2 * iter) onde N=linhas, L=run media, iter=#aliases.

Combina com M1.E base (range + escape escopo). Reserva `~` e `&`
em literais (escape `\~`, `\&`).
"""

import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from online import Token, TokLit, TokRefPref, TokRefSuf
from syntax_base import Syntax


class M4C1pBatchSubsequenciasSyntax(Syntax):

    name = "M4-C1p-batch-subsequencias"

    # ---- helpers identicos a M1.E ----

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
            elif c in ('*', '\\', '&', '~'):
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

        # FASE 1: gerar pedacos base por linha
        # Cada linha vira lista de tokens:
        #   ('lit', text)
        #   ('refs', [int, int, ...])    # subsequencia contigua
        # (1 elemento 'refs' por agrupamento natural; subsequencias
        #  internas serao identificadas e separadas na FASE 4)
        frags_por_no = {}
        proximo_idx = 1
        eid_emitido = set()
        # linha_pedacos[i] = lista de tokens OU None (se is_rep)
        linha_pedacos = []
        # linha_meta[i] = (count, eid_resp, is_rep)
        linha_meta = []

        for s_run, count in self._rle_adjacente(linhas_originais):
            eid = unica_to_eid[s_run]
            if eid not in eid_emitido:
                s = strings_unicas[eid - 1]
                tokens = tokens_por_string[eid - 1]
                qa = quebras[eid]
                frags_por_no[eid] = []
                base = []  # sequencia bruta (alternating lit/ref)
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
                # agrupa refs contiguas em uma run
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

        # FASE 2-4: detector iterativo de subsequencias
        proximo_alias_temp = 1  # id temporario (sera remapeado)
        while proximo_alias_temp <= 99:
            # 4a. Conta sub-tuplas contiguas K >= 2 sobre todos pedacos
            # 'refs' atuais
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

            # 4b. encontra melhor candidato com net > 0
            melhor = None
            melhor_net = 0
            n_tam = len(str(proximo_alias_temp))
            for sub, R in contagem.items():
                if R < 2:
                    continue
                Lr = len(self._emit_refs_range(list(sub)))
                eco_uso = Lr - 1 - n_tam  # `&N` custo
                if eco_uso <= 0:
                    continue
                # 1a def: `~SUBSEQ~` = Lr + 2; vs original (Lr) →
                # custo extra na 1a = 2
                # uso (R-1) vezes: cada uso economiza eco_uso
                net = (R - 1) * eco_uso - 2
                if net > melhor_net:
                    melhor_net = net
                    melhor = (sub, R, Lr)

            if melhor is None:
                break

            sub, R, Lr = melhor
            alias_id_temp = proximo_alias_temp
            proximo_alias_temp += 1

            # 4c. substituir em todas linhas
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
                                           alias_id_temp, list(sub)))
                            i += len(sub)
                        else:
                            buf.append(refs[i])
                            i += 1
                    if buf:
                        novos.append(('refs', buf))
                linha_pedacos[li] = novos

        # FASE 5: converte 1a ocorrencia global de cada alias em def,
        # demais em use
        aliases_ja_def = set()
        for li in range(len(linha_pedacos)):
            pedacos = linha_pedacos[li]
            if pedacos is None:
                continue
            novos = []
            for p in pedacos:
                if p[0] == 'alias_marker':
                    aid = p[1]
                    sub = p[2]
                    if aid not in aliases_ja_def:
                        novos.append(('alias_def_inline', aid, sub))
                        aliases_ja_def.add(aid)
                    else:
                        novos.append(('alias_use', aid))
                else:
                    novos.append(p)
            linha_pedacos[li] = novos

        # FASE 6: renumera aliases por ordem de 1a definicao
        alias_remap = {}
        contador = 1
        for li in range(len(linha_pedacos)):
            pedacos = linha_pedacos[li]
            if pedacos is None:
                continue
            for p in pedacos:
                if p[0] == 'alias_def_inline' and p[1] not in alias_remap:
                    alias_remap[p[1]] = contador
                    contador += 1
        for li in range(len(linha_pedacos)):
            pedacos = linha_pedacos[li]
            if pedacos is None:
                continue
            novos = []
            for p in pedacos:
                if p[0] == 'alias_def_inline':
                    novos.append(('alias_def_inline',
                                   alias_remap[p[1]], p[2]))
                elif p[0] == 'alias_use':
                    novos.append(('alias_use', alias_remap[p[1]]))
                else:
                    novos.append(p)
            linha_pedacos[li] = novos

        # FASE 7: serializar
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
                        # separador antes de refs:
                        # - apos refs (sem separador): `,` para juntar
                        # - apos lit que terminou em digit-seq: `*` (M1.E)
                        # - apos alias_use (`&N` termina em digit): `,`
                        # - apos alias_def_inline (termina em `~`): nada
                        if prev_tipo == 'refs':
                            partes.append(',')
                        elif prev_tipo == 'lit' and prev_emit_termina_em_digito:
                            partes.append('*')
                        elif prev_tipo == 'alias_use':
                            partes.append(',')
                        # alias_def_inline termina em `~` (nao-digit), sem sep
                        partes.append(self._emit_refs_range(p[1]))
                        prev_emit_termina_em_digito = True
                        prev_tipo = 'refs'
                    elif t == 'alias_def_inline':
                        # `~SUBSEQ~` — `~` inicial distingue, sem sep
                        # explicito, EXCETO apos lit-digit-seq onde
                        # `~` distingue OK (nao-digit)
                        aid = p[1]
                        sub = p[2]
                        if prev_tipo == 'refs':
                            partes.append(',')
                        # apos lit-digit-seq: `~` nao confunde com digit, OK
                        # apos alias_use: `~` nao confunde, OK
                        partes.append('~')
                        partes.append(self._emit_refs_range(sub))
                        partes.append('~')
                        prev_emit_termina_em_digito = False
                        prev_tipo = 'alias_def_inline'
                    elif t == 'alias_use':
                        # `&N` — `&` distingue, sem separador
                        if prev_tipo == 'refs':
                            partes.append(',')
                        partes.append(f"&{p[1]}")
                        prev_emit_termina_em_digito = True
                        prev_tipo = 'alias_use'
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
            elif ch == ',':
                i += 1  # separador entre tokens de refs/aliases
            elif ch == '~':
                # def alias: ~SUBSEQ~
                i += 1
                # parsear SUBSEQ (refs com range)
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
                # j deve estar em '~'
                if j >= n or resto[j] != '~':
                    raise ValueError(f"alias def sem ~ final em pos {i}: "
                                     f"{resto!r}")
                # expande refs e grava texto
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
                next_id = len(aliases) + 1
                aliases[next_id] = texto_alias
                partes.append(texto_alias)
                i = j + 1  # pula `~` final
            elif ch == '&':
                # alias use: &N
                j = i + 1
                while j < n and resto[j].isdigit():
                    j += 1
                alias_id = int(resto[i + 1:j])
                partes.append(aliases[alias_id])
                i = j
            elif ch.isdigit():
                # refs normais (run nao-aliasada). Le digits/virgulas/..
                # ate' encontrar nao-digit-nao-virgula-nao-..-nao-~-nao-&
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
                # remove virgulas vazias do final
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
                    elif c.isdigit() or c in ('*', '&', '~'):
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
                s_no = self._parse_decl(
                    resto, frags, proximo_idx_ref, aliases)
                nos_decl.append(s_no)

            saida.extend([s_no] * count)
        return saida
