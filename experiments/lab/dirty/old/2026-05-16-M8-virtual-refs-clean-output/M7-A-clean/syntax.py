"""M7.A — Composicional (refactor limpo de M6.C).

Mesma semantica que M6.C:
- `,` entre refs: concat sem criar ref
- `~` entre refs: concat + cria novo ref auto-nomeado (pairwise)
- `a..b`: range = caso particular de composicao
- reuso: bare ref id (sem prefixo)

Diferenca: codigo estruturado em 3 fases (tokenize / detect / emit),
sem remendos. Trace gerado inline.
"""

import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from online import TokLit, TokRefPref, TokRefSuf
from syntax_base import Syntax


class M7AComposicionalSyntax(Syntax):

    name = "M7-A-clean"

    def __init__(self):
        self._trace = None
        self._rede = None

    def get_trace(self):
        return "\n".join(self._trace) if self._trace else ""

    def get_rede(self):
        return "\n".join(self._rede) if self._rede else ""

    # ---- helpers ----

    @staticmethod
    def _rle_adjacente(linhas):
        out = []
        for s in linhas:
            if out and out[-1][0] == s:
                out[-1] = (s, out[-1][1] + 1)
            else:
                out.append((s, 1))
        return out

    @staticmethod
    def _escape_lit(text):
        out, i, n = [], 0, len(text)
        term_seq = False
        while i < n:
            c = text[i]
            if c.isdigit():
                j = i
                while j < n and text[j].isdigit():
                    j += 1
                out.append('\\' + text[i:j])
                term_seq = (j == n)
                i = j
            elif c in ('*', '\\', '~'):
                out.append('\\' + c)
                term_seq = False
                i += 1
            else:
                out.append(c)
                term_seq = False
                i += 1
        return ''.join(out), term_seq

    @staticmethod
    def _runs(refs):
        """Quebra refs em runs de consecutivos."""
        if not refs:
            return []
        out, cur = [], [refs[0]]
        for r in refs[1:]:
            if r == cur[-1] + 1:
                cur.append(r)
            else:
                out.append(cur)
                cur = [r]
        out.append(cur)
        return out

    @classmethod
    def _emit_refs_range(cls, refs):
        """M1.E style: runs of consecutive refs as `a..b` (L>=3), joined by `,`."""
        if not refs:
            return ""
        parts = []
        for run in cls._runs(refs):
            if len(run) >= 3:
                parts.append(f"{run[0]}..{run[-1]}")
            else:
                parts.extend(str(r) for r in run)
        return ",".join(parts)

    @classmethod
    def _emit_composition(cls, sub):
        """Compositional emission: same as range but with `~` between groups."""
        if not sub:
            return ""
        parts = []
        for run in cls._runs(sub):
            if len(run) >= 3:
                parts.append(f"{run[0]}..{run[-1]}")
            else:
                parts.append("~".join(str(r) for r in run))
        return "~".join(parts)

    @classmethod
    def _count_ids_in_refs(cls, refs):
        """Numero de IDs que decoder aloca em emit_refs_range(refs)."""
        return sum(len(run) - 1 for run in cls._runs(refs) if len(run) >= 3)

    @staticmethod
    def _coletar_quebras(unicas, tokens_por_string):
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
                else:
                    cov = tok.length
                    if isinstance(tok, TokRefPref):
                        rs = 0
                    else:
                        rs = len(unicas[tok.string_id - 1]) - cov
                    for q in list(quebras[eid]):
                        if pos < q < pos + cov:
                            quebras[tok.string_id].add((q - pos) + rs)
                    pos += cov
        return quebras

    # ---- Phase A: tokenize ----

    def _tokenize_pieces(self, linhas, unicas, tokens_por_string):
        """Retorna (pieces_per_line, line_meta, atom_count).

        pieces_per_line[i]: lista ou None (se linha repetida)
          piece formato: ('lit', text, prov_atom_id) | ('refs', [prov_ids])
        line_meta[i]: (count_rle, eid, is_repeat)
        atom_count: total atoms provisionais alocados
        """
        quebras = self._coletar_quebras(unicas, tokens_por_string)
        unica_to_eid = {s: i + 1 for i, s in enumerate(unicas)}

        # frags_por_no[eid] = list of (start, end, atom_id) — para herdados
        frags_por_no = {}
        proximo_idx = 1
        eid_emitido = set()
        pieces_per_line = []
        line_meta = []

        for s_run, count in self._rle_adjacente(linhas):
            eid = unica_to_eid[s_run]
            if eid in eid_emitido:
                pieces_per_line.append(None)
                line_meta.append((count, eid, True))
                continue

            s = unicas[eid - 1]
            tokens = tokens_por_string[eid - 1]
            qa = quebras[eid]
            frags_por_no[eid] = []
            base = []
            pos = 0
            for tok in tokens:
                if isinstance(tok, TokLit):
                    sl, el = pos, pos + len(tok.text)
                    qs = sorted(q for q in qa if sl < q < el)
                    for a, b in zip([sl] + qs, qs + [el]):
                        idx = proximo_idx
                        proximo_idx += 1
                        frags_por_no[eid].append((a, b, idx))
                        base.append(('lit', s[a:b], idx))
                    pos = el
                else:
                    if isinstance(tok, TokRefPref):
                        rs = 0
                    else:
                        rs = len(unicas[tok.string_id - 1]) - tok.length
                    src_frags = frags_por_no[tok.string_id]
                    herdados = [(a, b, idx) for (a, b, idx) in src_frags
                                if a >= rs and b > rs
                                and (a - rs) < tok.length
                                and (b - rs) <= tok.length] if isinstance(tok, TokRefSuf) else [
                        (a, b, idx) for (a, b, idx) in src_frags
                        if a < tok.length and b <= tok.length]
                    for (a, b, idx) in herdados:
                        frags_por_no[eid].append(
                            (pos + (a - rs), pos + (b - rs), idx))
                        base.append(('ref', idx))
                    pos += tok.length

            # Agrupa refs consecutivas em piece único
            pieces = []
            i = 0
            while i < len(base):
                if base[i][0] == 'ref':
                    refs = [base[i][1]]
                    i += 1
                    while i < len(base) and base[i][0] == 'ref':
                        refs.append(base[i][1])
                        i += 1
                    pieces.append(('refs', refs))
                else:
                    pieces.append(('lit', base[i][1], base[i][2]))
                    i += 1
            pieces_per_line.append(pieces)
            line_meta.append((count, eid, False))
            eid_emitido.add(eid)

        return pieces_per_line, line_meta, proximo_idx - 1

    # ---- Phase B: detect compositions ----

    def _detect_compositions(self, pieces_per_line, atom_count):
        """Detector greedy iterativo. Modifica pieces_per_line in place.
        Substitui sub-tuplas detectadas por ('alias_marker', alias_temp, sub).
        Retorna lista de iter_info para trace."""
        next_alias = 1
        comp_acc_k = 0
        iter_traces = []

        while True:
            contagem = Counter()
            for pieces in pieces_per_line:
                if pieces is None:
                    continue
                for p in pieces:
                    if p[0] == 'refs':
                        refs = p[1]
                        for a in range(len(refs)):
                            for b in range(a + 2, len(refs) + 1):
                                contagem[tuple(refs[a:b])] += 1

            # Compute candidates with net
            candidates = []
            for sub, R in contagem.items():
                if R < 2:
                    continue
                baseline = len(self._emit_refs_range(list(sub)))
                K = len(sub)
                n_tam = len(str(atom_count + comp_acc_k + K - 1))
                if baseline <= n_tam:
                    continue
                candidates.append(((R - 1) * (baseline - n_tam),
                                    sub, R, baseline, n_tam))

            # Pick: ordem Counter (tie-break = primeiro inserido)
            best = None
            best_net = 0
            for net, sub, R, baseline, n_tam in candidates:
                if net > best_net:
                    best_net, best = net, (sub, R)

            iter_info = {
                'n_pairs': sum(1 for v in contagem.values() if v >= 2),
                'n_candidates': len(candidates),
                'candidates_sorted': sorted(candidates, reverse=True,
                                              key=lambda c: c[0]),
                'picked': best,
                'iter_num': len(iter_traces) + 1,
            }

            if best is None:
                iter_info['stopped'] = True
                iter_traces.append(iter_info)
                break

            sub, R = best
            alias_temp = next_alias
            next_alias += 1
            comp_acc_k += len(sub) - 1
            iter_info['alias_temp'] = alias_temp
            iter_info['lines_affected'] = []
            iter_info['n_substituicoes'] = 0

            K = len(sub)
            for li in range(len(pieces_per_line)):
                pieces = pieces_per_line[li]
                if pieces is None:
                    continue
                novos = []
                line_had_sub = False
                for p in pieces:
                    if p[0] != 'refs':
                        novos.append(p)
                        continue
                    refs = p[1]
                    i, buf = 0, []
                    while i < len(refs):
                        if (i + K <= len(refs)
                                and tuple(refs[i:i + K]) == sub):
                            if buf:
                                novos.append(('refs', buf))
                                buf = []
                            novos.append(('alias_marker',
                                           alias_temp, list(sub)))
                            i += K
                            iter_info['n_substituicoes'] += 1
                            line_had_sub = True
                        else:
                            buf.append(refs[i])
                            i += 1
                    if buf:
                        novos.append(('refs', buf))
                if line_had_sub:
                    iter_info['lines_affected'].append(li + 1)
                pieces_per_line[li] = novos

            iter_traces.append(iter_info)
            if len(iter_traces) >= 99:
                break

        return iter_traces

    # ---- Phase C: emit body (atom + composicao IDs interleaved) ----

    def _emit_body(self, pieces_per_line, line_meta):
        """Single pass emission. Allocates final IDs as decoder would.
        Retorna (body_lines, prov_to_final, alias_to_final, ref_sequences_per_line).
        """
        body = []
        current_id = 0
        prov_to_final = {}
        alias_to_final = {}
        ref_sequences = []  # for missed analysis

        for li, (count, eid, is_rep) in enumerate(line_meta):
            if is_rep:
                body.append(f"^{eid}")
                ref_sequences.append([])
                continue

            pieces = pieces_per_line[li]
            parts = []
            prev_type = None
            prev_lit_term_digit = False
            ref_seq = []

            for p in pieces:
                kind = p[0]

                # Separator before this piece
                if kind == 'lit':
                    if prev_type == 'lit':
                        parts.append('*')
                else:
                    # ref-like piece (refs/comp_def/comp_use)
                    if prev_type in ('refs', 'comp_def', 'comp_use'):
                        parts.append(',')
                    elif prev_type == 'lit' and prev_lit_term_digit:
                        parts.append('*')

                # Emit + advance current_id
                if kind == 'lit':
                    current_id += 1
                    prov_to_final[p[2]] = current_id
                    text_emit, prev_lit_term_digit = self._escape_lit(p[1])
                    parts.append(text_emit)
                    prev_type = 'lit'

                elif kind == 'refs':
                    refs_final = [prov_to_final[r] for r in p[1]]
                    current_id += self._count_ids_in_refs(refs_final)
                    parts.append(self._emit_refs_range(refs_final))
                    ref_seq.extend(refs_final)
                    prev_lit_term_digit = True
                    prev_type = 'refs'

                elif kind == 'alias_marker':
                    aid_temp, sub_prov = p[1], p[2]
                    K = len(sub_prov)
                    sub_final = [prov_to_final[r] for r in sub_prov]
                    if aid_temp not in alias_to_final:
                        current_id += K - 1
                        alias_to_final[aid_temp] = current_id
                        parts.append(self._emit_composition(sub_final))
                        ref_seq.append(current_id)
                        prev_type = 'comp_def'
                    else:
                        parts.append(str(alias_to_final[aid_temp]))
                        ref_seq.append(alias_to_final[aid_temp])
                        prev_type = 'comp_use'
                    prev_lit_term_digit = True

            line_resto = ''.join(parts)
            if count > 1:
                body.append(f"*{count}|{line_resto}")
            else:
                body.append(line_resto)
            ref_sequences.append(ref_seq)

        return body, prov_to_final, alias_to_final, ref_sequences

    # ---- trace builders ----

    def _build_trace(self, pieces_per_line, iter_traces,
                      prov_to_final, alias_to_final, ref_sequences):
        t = []
        t.append(f"# Optimization trace — syntax={self.name}")
        t.append("")
        t.append("=== DETECTOR ITERATIONS ===")
        t.append("")
        for info in iter_traces:
            t.append(f"--- Iter {info['iter_num']} ---")
            t.append(f"Sub-tuplas K>=2 com R>=2: {info['n_pairs']}  "
                     f"net>0: {info['n_candidates']}")
            if info['iter_num'] > 1:
                t.append("NOTA: alias_markers de iters anteriores OPACOS "
                         "pra Counter")
            if info['picked'] is None:
                t.append("Nenhum candidato com net > 0. STOP.")
                t.append("")
                continue
            picked_sub = info['picked'][0]
            for k_idx, (net, sub, R, baseline, n_tam) in enumerate(
                    info['candidates_sorted'][:10]):
                pick = " <- PICK" if sub == picked_sub else ""
                sub_str = self._emit_refs_range(list(sub))
                t.append(f"  {sub_str:20s} | R={R} Lr={baseline} "
                         f"len(N)~{n_tam} net=({R-1})*({baseline}-{n_tam})"
                         f"={net}{pick}")
            top_net = info['candidates_sorted'][0][0]
            tied = [c for c in info['candidates_sorted'] if c[0] == top_net]
            if len(tied) > 1:
                t.append(f"  AMBIGUIDADE: {len(tied)} candidates "
                         f"empatam em net={top_net}; greedy escolheu "
                         f"primeiro por ordem Counter")
            t.append(f"Substituido em {info['n_substituicoes']} "
                     f"ocorrencias (linhas {info['lines_affected']})")
            t.append("")
        t.append("=== MISSED OPPORTUNITIES (post-hoc) ===")
        pair_count = Counter()
        pair_lines = defaultdict(list)
        for li, seq in enumerate(ref_sequences):
            for i in range(len(seq) - 1):
                pair = (seq[i], seq[i + 1])
                pair_count[pair] += 1
                if (li + 1) not in pair_lines[pair]:
                    pair_lines[pair].append(li + 1)
        next_id_est = max(list(prov_to_final.values()) +
                           list(alias_to_final.values()) + [0]) + 1
        len_n_est = len(str(next_id_est))
        missed = []
        for pair, R in pair_count.items():
            if R < 2:
                continue
            baseline = len(self._emit_refs_range(list(pair)))
            if baseline <= len_n_est:
                continue
            net = (R - 1) * (baseline - len_n_est)
            if net > 0:
                missed.append((net, pair, R, baseline))
        missed.sort(reverse=True)
        t.append("Pares adjacentes no body com R>=2 nao detectados "
                 "(causa: alias_marker opaco em iters subsequentes):")
        t.append("")
        total = 0
        for net, pair, R, baseline in missed[:30]:
            lines_str = ",".join(str(l) for l in pair_lines[pair])
            t.append(f"  pair=({pair[0]},{pair[1]}) R={R} "
                     f"lines=[{lines_str}] "
                     f"baseline=`{self._emit_refs_range(list(pair))}`"
                     f"={baseline} est_savings={net}")
            total += net
        if not missed:
            t.append("  (nenhum)")
        t.append("")
        t.append(f"Total estimated missed bytes: {total}")
        self._trace = t

    def _build_rede(self, pieces_per_line, prov_to_final,
                     alias_to_final, ref_sequences):
        """Visao da rede: atomos, composicoes, frequencia de uso."""
        r = []
        r.append(f"# Rede de atomos + composicoes — {self.name}")
        r.append("")
        r.append("=== ATOMS (final IDs) ===")
        prov_to_lit = {}
        for pieces in pieces_per_line:
            if pieces is None:
                continue
            for p in pieces:
                if p[0] == 'lit':
                    prov_to_lit[p[2]] = p[1]
        for prov in sorted(prov_to_final):
            r.append(f"  final {prov_to_final[prov]:3d}: "
                     f"{prov_to_lit.get(prov, '?')!r}")
        r.append("")
        r.append("=== COMPOSITIONS (final IDs, ordem body) ===")
        for li, pieces in enumerate(pieces_per_line):
            if pieces is None:
                continue
            for p in pieces:
                if p[0] == 'alias_marker':
                    aid = p[1]
                    if aid not in alias_to_final:
                        continue
                    fid = alias_to_final[aid]
                    sub_final = [prov_to_final[r_] for r_ in p[2]]
                    r.append(f"  final {fid:3d} = composicao{sub_final} "
                             f"(emit `{self._emit_composition(sub_final)}`)")
                    alias_to_final.pop(aid, None)  # so' lista 1 vez
        # Frequencia uso
        r.append("")
        r.append("=== USO POR REF (id → contagem em body) ===")
        usage = Counter()
        for seq in ref_sequences:
            usage.update(seq)
        for ref_id, n in sorted(usage.items(), key=lambda x: (-x[1], x[0])):
            r.append(f"  ref {ref_id:3d}: {n}x")
        self._rede = r

    # ---- main encode + decode ----

    def encode(self, linhas, unicas, tokens_por_string, header):
        pieces_per_line, line_meta, atom_count = self._tokenize_pieces(
            linhas, unicas, tokens_por_string)
        iter_traces = self._detect_compositions(pieces_per_line, atom_count)
        body, prov_to_final, alias_to_final, ref_seqs = self._emit_body(
            pieces_per_line, line_meta)
        # Build trace + rede after emit (need final IDs)
        self._build_trace(pieces_per_line, iter_traces,
                           prov_to_final, dict(alias_to_final), ref_seqs)
        self._build_rede(pieces_per_line, prov_to_final,
                          dict(alias_to_final), ref_seqs)
        return "\n".join(body) + "\n"

    # ---- decode (identico ao M6.C) ----

    def _parse_decl(self, resto, frags, prox_idx):
        partes = []
        i, n = 0, len(resto)
        while i < n:
            ch = resto[i]
            if ch == '*':
                i += 1
            elif ch.isdigit():
                j = i
                while j < n:
                    c = resto[j]
                    if c.isdigit() or c == ',':
                        j += 1
                    elif c == '.' and j + 1 < n and resto[j + 1] == '.':
                        j += 2
                    elif c == '~':
                        j += 1
                    else:
                        break
                for unit in resto[i:j].split(','):
                    if not unit:
                        continue
                    refs = []
                    for grp in unit.split('~'):
                        if '..' in grp:
                            a, b = grp.split('..')
                            refs.extend(range(int(a), int(b) + 1))
                        else:
                            refs.append(int(grp))
                    if len(refs) >= 2:
                        prev = frags[refs[0]]
                        for r in refs[1:]:
                            new = prev + frags[r]
                            prox_idx[0] += 1
                            frags[prox_idx[0]] = new
                            prev = new
                        partes.append(prev)
                    else:
                        partes.append(frags[refs[0]])
                i = j
            else:
                buf = []
                while i < n:
                    c = resto[i]
                    if c == '\\':
                        i += 1
                        if i >= n:
                            raise ValueError("escape no fim de linha")
                        nc = resto[i]
                        if nc.isdigit():
                            j = i
                            while j < n and resto[j].isdigit():
                                j += 1
                            buf.append(resto[i:j])
                            i = j
                        else:
                            buf.append(nc)
                            i += 1
                    elif c.isdigit() or c in ('*', '~'):
                        break
                    else:
                        buf.append(c)
                        i += 1
                texto = ''.join(buf)
                prox_idx[0] += 1
                frags[prox_idx[0]] = texto
                partes.append(texto)
        return ''.join(partes)

    def decode(self, tcf_text):
        frags = {}
        prox_idx = [0]
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
                s_no = nos_decl[int(resto[1:]) - 1]
            else:
                s_no = self._parse_decl(resto, frags, prox_idx)
                nos_decl.append(s_no)
            saida.extend([s_no] * count)
        return saida
