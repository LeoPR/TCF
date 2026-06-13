"""M8.A — Detector unificado.

CAMADA-2 do TCF. Codnome dirty-lab `M8.A`; nome canonical: HCC (Hierarchical
Compositional Coding) — spec `docs/algorithms/HCC.md`. Esta classe
(`M8AVirtualRefsSyntax`) e' o detector; `hcc_seqrle.py` estende com seq-RLE.
GATE byte-canonical: mudanca em `_detect_compositions` DEVE passar
`tests/test_real_world_snapshots.py` + `tests/test_core_rt.py`.

Generalizacao do M7.A: refs atomicos (id positivo = prov atom) e refs
virtuais (id negativo = -alias_temp) compartilham o mesmo espaco em
'refs' pieces. Detector itera uniformemente em sub-tuplas mixtos.

Pair (atom, alias_anterior) e' apenas mais um candidato.

Emit recursivo: alias com sub contendo virtuals nao-emitidos faz
expansao inline (emit das inner_aliases primeiro como units separadas
por `,`, depois o alias externo como composition unit).

Convencao output: sem brackets, single LF (docs/algorithms/output-convention.md).
"""

from collections import Counter, defaultdict

# Welding step 2 (2026-05-17): adaptado de
# experiments/lab/dirty/old/2026-05-16-.../M8-A-detector-unificado/syntax.py.
# Apenas estes 2 imports mudaram (path do dirty para src/tcf/core/);
# logica de encode/decode permanece byte-exata. Validado em M12.
from tcf.core.online import TokLit, TokRefPref, TokRefSuf
from tcf.core.syntax_base import Syntax


class M8AVirtualRefsSyntax(Syntax):

    name = "M8-A-virtual-refs"

    def __init__(self):
        self._trace = []
        self._rede = []

    def get_trace(self):
        return "\n".join(self._trace) if self._trace else ""

    def get_rede(self):
        return "\n".join(self._rede) if self._rede else ""

    # ---- helpers (igual M7.A) ----

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
    def _runs_pos(refs):
        """Runs de consecutivos POSITIVOS (atomic finals)."""
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
        """M1.E: ranges de consecutivos L>=3 unidos por `,`."""
        if not refs:
            return ""
        parts = []
        for run in cls._runs_pos(refs):
            if len(run) >= 3:
                parts.append(f"{run[0]}..{run[-1]}")
            else:
                parts.extend(str(r) for r in run)
        return ",".join(parts)

    @classmethod
    def _emit_composition(cls, chain):
        """Chain (todos positivos) unida por `~` com range nos subgrupos consecutivos."""
        if not chain:
            return ""
        parts = []
        for run in cls._runs_pos(chain):
            if len(run) >= 3:
                parts.append(f"{run[0]}..{run[-1]}")
            else:
                parts.append("~".join(str(r) for r in run))
        return "~".join(parts)

    @classmethod
    def _count_ids_in_refs(cls, refs):
        """IDs alocados em emit_refs_range(refs)."""
        return sum(len(run) - 1 for run in cls._runs_pos(refs) if len(run) >= 3)

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
        """Identica a M7.A: pieces = ('lit', text, atom_id) | ('refs', [prov_ids])."""
        quebras = self._coletar_quebras(unicas, tokens_por_string)
        unica_to_eid = {s: i + 1 for i, s in enumerate(unicas)}
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
                    if isinstance(tok, TokRefSuf):
                        herdados = [(a, b, idx) for (a, b, idx) in src_frags
                                    if a >= rs and b > rs
                                    and (a - rs) < tok.length
                                    and (b - rs) <= tok.length]
                    else:
                        herdados = [(a, b, idx) for (a, b, idx) in src_frags
                                    if a < tok.length and b <= tok.length]
                    for (a, b, idx) in herdados:
                        frags_por_no[eid].append(
                            (pos + (a - rs), pos + (b - rs), idx))
                        base.append(('ref', idx))
                    pos += tok.length

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

    # ---- Phase B: detect (unified) ----

    def _detect_compositions(self, pieces_per_line, atom_count):
        """Detector unificado: 'refs' lists contem ids mixtos
        (positivos = atomic prov, negativos = virtual aliases).
        Sub-tuplas counted naturalmente.

        Retorna (alias_to_sub, iter_traces).
        """
        next_alias = 1
        comp_acc_k = 0
        alias_to_sub = {}
        iter_traces = []

        while True:
            contagem = Counter()
            sub_first_line = {}
            for li, pieces in enumerate(pieces_per_line):
                if pieces is None:
                    continue
                for p in pieces:
                    if p[0] == 'refs':
                        refs = p[1]
                        for a in range(len(refs)):
                            for b in range(a + 2, len(refs) + 1):
                                sub = tuple(refs[a:b])
                                contagem[sub] += 1
                                if sub not in sub_first_line:
                                    sub_first_line[sub] = li

            # Compute alias_first_line: primeiro li onde -alias aparece em body
            alias_first_line = {}
            for li, pieces in enumerate(pieces_per_line):
                if pieces is None:
                    continue
                for p in pieces:
                    if p[0] == 'refs':
                        for ref in p[1]:
                            if ref < 0:
                                a = -ref
                                if a not in alias_first_line:
                                    alias_first_line[a] = li

            # Build candidates com filtro relaxado:
            # - 0 virtuais OU
            # - 1 virtual com:
            #     (a) virtual em position 0, OU
            #     (b) virtual em pos > 0 MAS alias_first_line < sub_first_line
            #         (= alias e' RESOLVIDA antes do sub's def emission,
            #          entao inline expansion usa final_id direto).
            # H-PERF-06-v2 (ADR-0019): cheap upper-bound prune + running-max
            # inline. Antes de chamar _estimate_baseline_chars (caro, ~18% do
            # encode), descarta subs cujo net NAO pode bater o best ja' visto.
            # Safety byte-canonical: o upper bound e' conservador —
            #   net = (R-1)*(baseline - n_tam), baseline <= K*n_est_ub + (K-1),
            #   n_tam >= n_tam_min (K>=2). n_est_ub >= n_est de
            #   _estimate_baseline_chars e n_tam_min <= n_tam => ub_net >= net.
            # Logo so' pula candidatos que tambem perderiam o pick. Ordem do
            # Counter preservada (tie-break first-wins identico ao 2-pass).
            n_est_ub = max(2, len(str(atom_count + comp_acc_k + len(contagem) + 9)))
            n_tam_min = len(str(atom_count + comp_acc_k + 1))

            candidates = []
            best = None
            best_net = 0
            for sub, R in contagem.items():
                if R < 2:
                    continue
                K = len(sub)
                ub_net = (R - 1) * (K * n_est_ub + (K - 1) - n_tam_min)
                if ub_net <= best_net:
                    continue
                virtual_count = sum(1 for x in sub if x < 0)
                if virtual_count > 1:
                    continue
                if virtual_count == 1:
                    virt_pos = next(i for i, x in enumerate(sub) if x < 0)
                    if virt_pos > 0:
                        # Check body-order: alias deve estar resolvida antes
                        virt_alias = -sub[virt_pos]
                        if alias_first_line.get(virt_alias,
                                                  float('inf')) >= sub_first_line[sub]:
                            continue
                baseline = self._estimate_baseline_chars(
                    sub, atom_count, comp_acc_k)
                n_tam = len(str(atom_count + comp_acc_k + K - 1))
                if baseline <= n_tam:
                    continue
                net = (R - 1) * (baseline - n_tam)
                candidates.append((net, sub, R, baseline, n_tam))
                # Running-max inline; tie-break preservado (> estrito => primeiro
                # inserido na ordem do Counter vence, identico ao 2-pass original).
                if net > best_net:
                    best_net = net
                    best = (sub, R)

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
            alias_to_sub[alias_temp] = list(sub)
            virtual_id = -alias_temp
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
                    new_refs = []
                    i = 0
                    while i < len(refs):
                        if (i + K <= len(refs)
                                and tuple(refs[i:i + K]) == sub):
                            new_refs.append(virtual_id)
                            i += K
                            iter_info['n_substituicoes'] += 1
                            line_had_sub = True
                        else:
                            new_refs.append(refs[i])
                            i += 1
                    if new_refs:
                        novos.append(('refs', new_refs))
                if line_had_sub:
                    iter_info['lines_affected'].append(li + 1)
                pieces_per_line[li] = novos

            iter_traces.append(iter_info)
            if len(iter_traces) >= 99:
                break

        return alias_to_sub, iter_traces

    def _estimate_baseline_chars(self, sub, atom_count, comp_acc_k):
        """Estima chars do emit `,`-separado da sub (mixed atom/virtual).
        Virtuals contam como ~len(str(id_estimado)) chars."""
        n_est = max(2, len(str(atom_count + comp_acc_k + 1)))
        parts = []
        i = 0
        while i < len(sub):
            if sub[i] > 0:
                # run atomic
                run = [sub[i]]
                j = i + 1
                while j < len(sub) and sub[j] > 0 and sub[j] == run[-1] + 1:
                    run.append(sub[j])
                    j += 1
                if len(run) >= 3:
                    parts.append(f"{run[0]}..{run[-1]}")
                else:
                    parts.extend(str(r) for r in run)
                i = j
            else:
                # virtual: estimate 2 digits
                parts.append("9" * n_est)
                i += 1
        return len(",".join(parts))

    # ---- Phase C: emit (atom + composicao IDs interleaved) ----

    def _emit_body(self, pieces_per_line, line_meta, alias_to_sub):
        """Single pass emit. Walks pieces; for 'refs' with virtuals,
        recursively emits inner aliases as separate `,`-units before
        each alias def's chain unit."""
        body = []
        prov_to_final = {}
        alias_to_final = {}
        state = {
            'current_id': [0],
            'prov_to_final': prov_to_final,
            'alias_to_final': alias_to_final,
            'alias_to_sub': alias_to_sub,
            'ref_seqs': [],
        }
        # state['ref_seq'] is per-line; allocated inside loop

        for li, (count, eid, is_rep) in enumerate(line_meta):
            if is_rep:
                # Bug fix 2026-05-15: ramo `is_rep` (eid ja emitido) ignorava
                # `count` da RLE-group atual, perdendo linhas no decode quando
                # um mesmo valor aparece em multiplos grupos nao-consecutivos
                # com count>=2 no grupo posterior. Caso nao exercitado em D1-D9
                # (byte-canonical preservado), mas exercitado por pre-tx
                # incremental (deltas repetidos em grupos separados).
                if count > 1:
                    body.append(f"*{count}|^{eid}")
                else:
                    body.append(f"^{eid}")
                state['ref_seqs'].append([])
                continue

            pieces = pieces_per_line[li]
            parts = []
            prev_type = None
            prev_lit_term_digit = False
            ref_seq = []
            state['ref_seq'] = ref_seq

            for p in pieces:
                kind = p[0]

                if kind == 'lit':
                    if prev_type == 'lit':
                        parts.append('*')
                    elif prev_type == 'refs' and p[1] and p[1][0] in (',', '~'):
                        # Bug fix 2026-05-19 (ADR-0007): separator `*` quando
                        # ref->lit transition e lit comeca com `,` ou `~`.
                        # Sem o separator, parser do decoder entra ref mode
                        # em "1,..." e consome o `,` como continuacao do ref
                        # expression, perdendo o `,` literal. Descoberto em
                        # EXP-013 TPC-H (p_comment 'pending, bold' -> 'pending bold').
                        parts.append('*')
                    state['current_id'][0] += 1
                    prov_to_final[p[2]] = state['current_id'][0]
                    text_emit, prev_lit_term_digit = self._escape_lit(p[1])
                    parts.append(text_emit)
                    prev_type = 'lit'

                else:  # 'refs'
                    if prev_type == 'refs':
                        parts.append(',')
                    elif prev_type == 'lit' and prev_lit_term_digit:
                        parts.append('*')

                    refs = p[1]
                    run_emit = self._emit_ref_run(refs, state)
                    parts.append(run_emit)
                    prev_lit_term_digit = True
                    prev_type = 'refs'

            linha_resto = ''.join(parts)
            if count > 1:
                body.append(f"*{count}|{linha_resto}")
            else:
                body.append(linha_resto)
            state['ref_seqs'].append(ref_seq)

        return body, prov_to_final, alias_to_final, state['ref_seqs']

    def _emit_ref_run(self, refs, state):
        """Emit run de refs mixtos (atomic positivo + virtual negativo).
        Segments: atomic runs consecutivos → M1.E range;
                  virtual → alias def (recursive) ou use.
        Joined por `,`."""
        segments = []
        i = 0
        while i < len(refs):
            if refs[i] > 0:
                # Run de atoms
                atom_run = []
                while i < len(refs) and refs[i] > 0:
                    atom_run.append(state['prov_to_final'][refs[i]])
                    i += 1
                segments.append(self._emit_refs_range(atom_run))
                state['current_id'][0] += self._count_ids_in_refs(atom_run)
                state['ref_seq'].extend(atom_run)
            else:
                # Virtual: emit alias (def or use)
                alias_temp = -refs[i]
                seg = self._emit_alias(alias_temp, state)
                segments.append(seg)
                i += 1
        return ','.join(segments)

    def _emit_alias(self, alias_temp, state):
        """Emit alias: bare final id (se ja' emitido) OU def composition.
        Para def: INLINE EXPANSION — sub flatten recursivo numa chain
        linear; pairwise binarization aloca K-1 IDs. Inner aliases
        unresolved completam em positions intermediarias e ganham
        finals correspondentes (so' funciona se inner esta em position 0,
        garantido pelo filtro do detector)."""
        if alias_temp in state['alias_to_final']:
            fid = state['alias_to_final'][alias_temp]
            state['ref_seq'].append(fid)
            return str(fid)

        # First emission: build linear chain inline-expanded
        linear = []
        completions = []  # (linear_index_at_completion, alias_temp)

        def expand(elem):
            if elem > 0:
                linear.append(state['prov_to_final'][elem])
            else:
                inner = -elem
                if inner in state['alias_to_final']:
                    # Already emitted: use single final id
                    linear.append(state['alias_to_final'][inner])
                else:
                    # Recursively expand inner's sub (inner is at position 0)
                    for inner_elem in state['alias_to_sub'][inner]:
                        expand(inner_elem)
                    completions.append((len(linear) - 1, inner))

        for elem in state['alias_to_sub'][alias_temp]:
            expand(elem)
        completions.append((len(linear) - 1, alias_temp))

        emission = self._emit_composition(linear)
        K = len(linear)
        base = state['current_id'][0]
        state['current_id'][0] += K - 1

        # Assign final IDs by pairwise position
        # ID at linear index k (0-based, k>=1) is base + k
        for idx, ali in completions:
            if ali not in state['alias_to_final'] and idx >= 1:
                state['alias_to_final'][ali] = base + idx

        state['ref_seq'].append(state['alias_to_final'][alias_temp])
        return emission

    # ---- trace + rede builders ----

    def _build_trace(self, iter_traces, prov_to_final,
                      alias_to_final, ref_seqs):
        t = [f"# Optimization trace — syntax={self.name}", ""]
        t.append("=== DETECTOR ITERATIONS (unified — atoms + virtuals) ===")
        t.append("")
        for info in iter_traces:
            t.append(f"--- Iter {info['iter_num']} ---")
            t.append(f"Sub-tuplas K>=2 com R>=2: {info['n_pairs']}  "
                     f"net>0: {info['n_candidates']}")
            if info['picked'] is None:
                t.append("Nenhum candidato com net > 0. STOP.")
                t.append("")
                continue
            picked_sub = info['picked'][0]
            for k_idx, (net, sub, R, baseline, n_tam) in enumerate(
                    info['candidates_sorted'][:10]):
                pick = " <- PICK" if sub == picked_sub else ""
                sub_str = self._fmt_sub(sub)
                t.append(f"  {sub_str:24s} | R={R} Lr={baseline} "
                         f"len(N)~{n_tam} net=({R-1})*({baseline}-{n_tam})"
                         f"={net}{pick}")
            top_net = info['candidates_sorted'][0][0]
            tied = [c for c in info['candidates_sorted'] if c[0] == top_net]
            if len(tied) > 1:
                t.append(f"  AMBIGUIDADE: {len(tied)} candidates "
                         f"empatam em net={top_net}")
            t.append(f"Substituido em {info['n_substituicoes']} "
                     f"ocorrencias (linhas {info['lines_affected']})")
            t.append("")
        # Missed (post-hoc on emitted ref_seqs)
        t.append("=== MISSED OPPORTUNITIES (post-hoc) ===")
        pair_count = Counter()
        pair_lines = defaultdict(list)
        for li, seq in enumerate(ref_seqs):
            for i in range(len(seq) - 1):
                pair = (seq[i], seq[i + 1])
                pair_count[pair] += 1
                if (li + 1) not in pair_lines[pair]:
                    pair_lines[pair].append(li + 1)
        next_id = max(list(prov_to_final.values()) +
                       list(alias_to_final.values()) + [0]) + 1
        len_n = len(str(next_id))
        missed = []
        for pair, R in pair_count.items():
            if R < 2:
                continue
            baseline = len(self._emit_refs_range(list(pair)))
            if baseline <= len_n:
                continue
            net = (R - 1) * (baseline - len_n)
            if net > 0:
                missed.append((net, pair, R, baseline))
        missed.sort(reverse=True)
        if not missed:
            t.append("  (nenhum)")
        else:
            for net, pair, R, baseline in missed[:30]:
                lines_str = ",".join(str(l) for l in pair_lines[pair])
                t.append(f"  pair=({pair[0]},{pair[1]}) R={R} "
                         f"lines=[{lines_str}] "
                         f"baseline={baseline} est_savings={net}")
        t.append("")
        t.append(f"Total estimated missed: {sum(m[0] for m in missed)}")
        self._trace = t

    @staticmethod
    def _fmt_sub(sub):
        return ",".join(str(s) if s > 0 else f"a{-s}" for s in sub)

    def _build_rede(self, pieces_per_line, prov_to_final,
                     alias_to_final, alias_to_sub, ref_seqs):
        r = [f"# Rede de atomos + composicoes — {self.name}", ""]
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
        r.append("=== COMPOSITIONS (final IDs) ===")
        for atemp, fid in sorted(alias_to_final.items(),
                                   key=lambda x: x[1]):
            sub = alias_to_sub[atemp]
            sub_fmt = self._fmt_sub(sub)
            r.append(f"  final {fid:3d} = a{atemp} composicao({sub_fmt})")
        r.append("")
        r.append("=== USO POR REF ===")
        usage = Counter()
        for seq in ref_seqs:
            usage.update(seq)
        for ref_id, n in sorted(usage.items(), key=lambda x: (-x[1], x[0])):
            r.append(f"  ref {ref_id:3d}: {n}x")
        self._rede = r

    # ---- main encode + decode ----

    def encode(self, linhas, unicas, tokens_por_string, header):
        pieces_per_line, line_meta, atom_count = self._tokenize_pieces(
            linhas, unicas, tokens_por_string)
        alias_to_sub, iter_traces = self._detect_compositions(
            pieces_per_line, atom_count)
        body, prov_to_final, alias_to_final, ref_seqs = self._emit_body(
            pieces_per_line, line_meta, alias_to_sub)
        self._build_trace(iter_traces, prov_to_final,
                           dict(alias_to_final), ref_seqs)
        self._build_rede(pieces_per_line, prov_to_final,
                          dict(alias_to_final), alias_to_sub, ref_seqs)
        # No brackets, single LF
        return "\n".join(body) + "\n"

    # ---- decode (igual M7.A) ----

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
            # Bug fixes 2026-05-18 (EXP-012 + EXP-013):
            # 1. NAO strip — strip removia leading/trailing whitespace
            #    de literais (descoberto em TPC-H region/nation comments
            #    com trailing space).
            # 2. NAO skipar empty linha — representa string vazia
            #    legitima (encoder emite body.append('') quando lit e' "").
            # Brackets `[`/`]` ainda skipados pra back-compat de formato antigo.
            linha = raw
            if linha in ("[", "]"):
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


# ---------------------------------------------------------------------------
# H-PERF-06-v2 Fase B (ADR-0020): acelerador Cython OPCIONAL de
# _detect_compositions. Se a extensao compilada (tcf._core.detect) estiver
# presente, substitui o metodo pure-Python acima por ela — output byte-identico
# (validado: D1-D9=1523B, D17a=322B, fixtures real-world; ~2.1-2.3x mais rapido).
# Senao (install sem compilador), fallback silencioso pro pure-Python — o
# pacote funciona identico, so' mais lento. NUNCA falha por ausencia da extensao.
# ---------------------------------------------------------------------------
try:  # pragma: no cover - depende de build opcional
    from tcf._core.detect import _detect_compositions as _detect_compositions_cy
    M8AVirtualRefsSyntax._detect_compositions = _detect_compositions_cy
    M8AVirtualRefsSyntax._detect_compositions_accelerated = True
except Exception:  # ImportError ou falha de carga da extensao
    M8AVirtualRefsSyntax._detect_compositions_accelerated = False
