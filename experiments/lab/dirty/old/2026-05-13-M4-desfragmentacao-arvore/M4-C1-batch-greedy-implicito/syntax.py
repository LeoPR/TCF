"""M4.C1 — Batch greedy com idx implicito.

Tecnica: depois de gerar serializacao M1.E, identifica RUNS de refs
(sequencias consecutivas) que se repetem entre linhas. Primeira
aparicao da run vai marcada com `~` (define alias); subsequentes
viram `&N`.

Diferenca vs M3-style (com preambulo):
- Sem `&N=texto` no preambulo
- Definicao acontece INLINE (1a aparicao + `~`)
- Custo de definicao: 1 char (`~`) em vez de `4 + len(texto)`
- Idx alocado por ordem de 1a aparicao das runs aliasadas

Custos:
- 1a aparicao: `~RUN` = len(RUN) + 1 char
- 2a+ aparicoes: `&N` = 1 + len(str(N)) chars
- Net = R · (Lr - 1 - len(str(N))) - 1

Para Lr=6 (run media), N=1 (1 char): Net = R · 4 - 1 → R=2: +7,
R=3: +11.

Comparado com M3 explicito: ganho de 4+Lt-1 chars na declaracao
por alias.

Decoder mantem tabela aliases. Ao ver `~`, aloca proximo N, expande
RUN, registra. Ao ver `&N`, expande RUN_N.

Combina com M1.E base (range + escape escopo). Reserva mais 1 char
(`~`) em literais (escape `\~`).
"""

import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from online import Token, TokLit, TokRefPref, TokRefSuf
from syntax_base import Syntax


class M4C1BatchGreedyImplicitoSyntax(Syntax):

    name = "M4-C1-batch-greedy-implicito"

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

        # FASE 1: gerar elementos por eid (igual M1.E mas separa runs)
        frags_por_no = {}
        proximo_idx = 1
        eid_emitido = set()
        # elementos_por_eid[eid] = lista de (tipo, val)
        # tipo: 'lit' (val=text), 'refs' (val=list[int])
        elementos_por_eid = {}
        linhas_dados = []

        for s_run, count in self._rle_adjacente(linhas_originais):
            eid = unica_to_eid[s_run]
            if eid not in eid_emitido:
                s = strings_unicas[eid - 1]
                tokens = tokens_por_string[eid - 1]
                qa = quebras[eid]
                frags_por_no[eid] = []
                # primeiro pass: coleta TUDO como ('lit', text) ou
                # ('ref', idx); depois agrupa refs consecutivas
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

                # agrupa refs consecutivas em uma run
                elementos = []
                i = 0
                while i < len(base):
                    tipo, val = base[i]
                    if tipo == 'ref':
                        run = [val]
                        i += 1
                        while i < len(base) and base[i][0] == 'ref':
                            run.append(base[i][1])
                            i += 1
                        elementos.append(('refs', tuple(run)))
                    else:
                        elementos.append(('lit', val))
                        i += 1
                elementos_por_eid[eid] = elementos
                eid_emitido.add(eid)
                linhas_dados.append((s_run, count, eid, False))
            else:
                linhas_dados.append((s_run, count, eid, True))

        # FASE 2: coletar runs e contar ocorrencias por linha (em ordem)
        # runs_por_linha[linha_idx] = lista de (pos_no_elementos, run_tuple)
        runs_por_linha = []
        for s_run, count, eid, is_rep in linhas_dados:
            if is_rep:
                runs_por_linha.append([])
                continue
            elementos = elementos_por_eid[eid]
            runs_aqui = []
            for pos, elem in enumerate(elementos):
                if elem[0] == 'refs':
                    runs_aqui.append((pos, elem[1]))
            runs_por_linha.append(runs_aqui)

        # FASE 3: contagem global de runs (tuplas)
        contagem = Counter()
        for runs in runs_por_linha:
            for (_, run) in runs:
                contagem[run] += 1

        # FASE 4: greedy de selecao de aliases
        # Para cada run com R >= 2, calcula net:
        # Lr = len(emit_refs_range(run))
        # Custo na 1a: 1 char (`~`)
        # Custo na 2a+: 1 + len(str(N)) chars (`&N`)
        # Economia/uso a partir da 2a: Lr - (1 + len(str(N)))
        # Net = (R - 1) * (Lr - 1 - len(str(N))) - 1 (marker `~` na 1a)
        # Greedy: maior net primeiro
        candidatos = []
        for run, R in contagem.items():
            if R < 2:
                continue
            Lr = len(self._emit_refs_range(list(run)))
            if Lr <= 1:
                continue
            # vamos supor N de 1 digito (otimista; sera ajustado)
            for n_tam in (1, 2):
                eco_uso = Lr - 1 - n_tam
                if eco_uso <= 0:
                    continue
                net = (R - 1) * eco_uso - 1
                if net > 0:
                    candidatos.append((net, R, Lr, run, n_tam))
                    break

        candidatos.sort(key=lambda c: -c[0])

        # FASE 4.1: SELECIONA quais runs viram alias (greedy por net)
        runs_aliasadas = set()
        for net, R, Lr, run, n_tam in candidatos:
            if len(runs_aliasadas) >= 99:
                break
            runs_aliasadas.add(run)

        # FASE 4.2: ALOCA idx por ORDEM DE 1a APARICAO no body
        # (encoder e decoder concordam nessa ordem; decoder aloca
        # ao ver `~` no TCF, encoder espelha)
        run_primeira_aparicao = {}  # run -> linha_idx
        for linha_idx, runs in enumerate(runs_por_linha):
            for (_, run) in runs:
                if run in runs_aliasadas and run not in run_primeira_aparicao:
                    run_primeira_aparicao[run] = linha_idx

        runs_ordenadas = sorted(run_primeira_aparicao.keys(),
                                  key=lambda r: run_primeira_aparicao[r])
        run_to_alias = {run: i + 1 for i, run in enumerate(runs_ordenadas)}

        # FASE 5: serializar
        # Para cada run aliasada: na 1a aparicao emite `~` + range,
        # nas seguintes emite `&N`
        run_ja_definido = set()  # runs cuja 1a aparicao ja' foi emitida
        body_linhas = []
        for (s_run, count, eid, is_rep), runs_aqui in zip(
                linhas_dados, runs_por_linha):
            if is_rep:
                linha_resto = f"^{eid}"
            else:
                elementos = elementos_por_eid[eid]
                partes = []
                prev_tipo = None
                prev_emit_termina_em_digito = False
                for elem in elementos:
                    tipo = elem[0]
                    if tipo == 'lit':
                        val = elem[1]
                        if prev_tipo == 'lit':
                            partes.append('*')
                        emitido, term_seq = self._escape_e_termina_em_digito(val)
                        partes.append(emitido)
                        prev_emit_termina_em_digito = term_seq
                        prev_tipo = 'lit'
                    else:  # refs
                        run = elem[1]
                        run_serial = self._emit_refs_range(list(run))
                        if run in run_to_alias:
                            alias_id = run_to_alias[run]
                            if run not in run_ja_definido:
                                # 1a aparicao: `~` + run completa
                                if prev_emit_termina_em_digito:
                                    partes.append('*')
                                partes.append('~')
                                partes.append(run_serial)
                                run_ja_definido.add(run)
                            else:
                                # 2a+: `&N`
                                # nao precisa separador `*` antes pois
                                # `&` distingue
                                partes.append(f"&{alias_id}")
                            prev_emit_termina_em_digito = True
                        else:
                            if prev_emit_termina_em_digito:
                                partes.append('*')
                            partes.append(run_serial)
                            prev_emit_termina_em_digito = True
                        prev_tipo = 'refs'
                linha_resto = ''.join(partes)

            if count > 1:
                body_linhas.append(f"*{count}|{linha_resto}")
            else:
                body_linhas.append(linha_resto)

        return "\n".join(["[", *body_linhas, "]"]) + "\n"

    # ---- decode ----

    def _parse_decl(self, resto, frags, proximo_idx_ref, aliases,
                      aliases_pendentes):
        """aliases: dict alias_id → expanded text
        aliases_pendentes: list de runs que aguardam alocacao (FIFO
            por ordem de 1a aparicao com `~`)
        """
        partes = []
        i = 0
        n = len(resto)
        while i < n:
            ch = resto[i]
            if ch == '*':
                i += 1
            elif ch == '~':
                # marca proximo run como alias (1a aparicao definidora)
                # next char deve ser digit (run comeca com idx-ref)
                i += 1
                # parsear o run completo (refs com range)
                j = i
                while j < n:
                    c = resto[j]
                    if c.isdigit() or c == ',':
                        j += 1
                    elif c == '.' and j + 1 < n and resto[j + 1] == '.':
                        j += 2
                    else:
                        break
                run_str = resto[i:j]
                # expandir refs e gravar texto da run
                expandido = []
                for r in run_str.split(','):
                    if not r:
                        continue
                    if '..' in r:
                        a, b = r.split('..')
                        for v in range(int(a), int(b) + 1):
                            expandido.append(frags[v])
                    else:
                        expandido.append(frags[int(r)])
                texto_run = ''.join(expandido)
                partes.append(texto_run)
                # registra como proximo alias disponivel
                next_id = len(aliases) + 1
                aliases[next_id] = texto_run
                i = j
            elif ch == '&':
                # alias use
                j = i + 1
                while j < n and resto[j].isdigit():
                    j += 1
                alias_id = int(resto[i + 1:j])
                partes.append(aliases[alias_id])
                i = j
            elif ch.isdigit():
                # refs normais (run nao-aliasada)
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
        aliases = {}  # id -> texto expandido

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
                    resto, frags, proximo_idx_ref, aliases, [])
                nos_decl.append(s_no)

            saida.extend([s_no] * count)
        return saida
