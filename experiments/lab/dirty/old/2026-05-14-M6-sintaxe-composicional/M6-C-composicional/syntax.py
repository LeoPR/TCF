"""M6.C — Sintaxe composicional.

Markers entre refs sao operadores:
- `,` entre refs: concat sem criar ref (efemero)
- `~` entre refs: concat + cria novo ref auto-nomeado (pairwise binary)
- `a..b` (range): caso particular de composicao por sequencia
- Reuso: bare ref id (sem prefixo `&`)

Decoder:
- Mantem `frags` (dict id → texto) crescendo linearmente
- Cada composicao (unit de refs joined por `~` ou range) cria K-1 IDs
- Pairwise left-assoc: chain `a~b~c` cria ((a+b)+c), 2 IDs.

Net per composicao R-uso (vs nao-aliasing):
  net = (R-1) * (baseline_inline - len(N_final))
"""

import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from online import Token, TokLit, TokRefPref, TokRefSuf
from syntax_base import Syntax


class M6CComposicionalSyntax(Syntax):

    name = "M6-C-composicional"

    def __init__(self):
        self._trace = []

    def get_trace(self):
        return "\n".join(self._trace)

    # ---- helpers ----

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
            elif c in ('*', '\\', '~'):
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
        """M1.E style: ranges joined by `,`."""
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

    @staticmethod
    def _emit_composition(sub):
        """Composicao: subgrupos consecutivos como range (L>=3), demais
        como refs individuais; tudo joined por `~`."""
        if not sub:
            return ""
        runs = []
        cur = [sub[0]]
        for r in sub[1:]:
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
                partes.append("~".join(str(r) for r in run))
        return "~".join(partes)

    @staticmethod
    def _count_ids_in_refs(refs):
        """Count IDs decoder allocates from _emit_refs_range(refs)
        emission (ranges of L>=3 allocate L-1 IDs each)."""
        if not refs:
            return 0
        runs = []
        cur = [refs[0]]
        for r in refs[1:]:
            if r == cur[-1] + 1:
                cur.append(r)
            else:
                runs.append(cur)
                cur = [r]
        runs.append(cur)
        return sum(len(run) - 1 for run in runs if len(run) >= 3)

    # ---- encode ----

    def encode(self, linhas_originais, strings_unicas,
                tokens_por_string, header):
        self._trace = []
        self._trace.append(f"# Optimization trace — syntax={self.name}")
        self._trace.append("")
        quebras = self._coletar_quebras(strings_unicas, tokens_por_string)
        unica_to_eid = {s: i + 1 for i, s in enumerate(strings_unicas)}

        # FASE 1: gerar pedacos base por linha (igual M4.C1')
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
                            base.append(('lit', s[a:b], idx))
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
                    tipo = base[i][0]
                    if tipo == 'ref':
                        run = [base[i][1]]
                        i += 1
                        while i < len(base) and base[i][0] == 'ref':
                            run.append(base[i][1])
                            i += 1
                        pedacos.append(('refs', run))
                    else:
                        # lit: (tipo, text, atom_id)
                        pedacos.append(('lit', base[i][1], base[i][2]))
                        i += 1
                linha_pedacos.append(pedacos)
                linha_meta.append((count, eid, False))
                eid_emitido.add(eid)
            else:
                linha_pedacos.append(None)
                linha_meta.append((count, eid, True))

        atom_count = proximo_idx - 1

        # Trace: atoms allocated by Phase 1 (provisional IDs)
        self._trace.append("=== ATOMS — Phase 1 provisional IDs ===")
        self._trace.append(f"Total atomos: {atom_count}")
        atom_seen = set()
        for pedacos in linha_pedacos:
            if pedacos is None:
                continue
            for p in pedacos:
                if p[0] == 'lit' and p[2] not in atom_seen:
                    atom_seen.add(p[2])
                    self._trace.append(f"  prov {p[2]:3d}: {p[1]!r}")
        self._trace.append("")

        # FASE 2-4: detector iterativo de composicoes
        proximo_alias_temp = 1
        composicoes_acumuladas_k = 0
        iter_count = 0
        self._trace.append("=== DETECTOR ITERATIONS ===")
        self._trace.append("")
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

            # Build all candidates with net (em ordem de Counter insertion)
            candidates = []
            for sub, R in contagem.items():
                if R < 2:
                    continue
                baseline = len(self._emit_refs_range(list(sub)))
                K = len(sub)
                n_tam = len(str(atom_count + composicoes_acumuladas_k + K - 1))
                if baseline <= n_tam:
                    continue
                net = (R - 1) * (baseline - n_tam)
                candidates.append((net, sub, R, baseline, n_tam))

            # Pick: respeita ordem Counter (tie-break = primeiro inserido)
            melhor = None
            melhor_net = 0
            for net, sub, R, baseline, n_tam in candidates:
                if net > melhor_net:
                    melhor_net = net
                    melhor = (sub, R)

            # Ordenacao para trace display
            candidates_for_trace = sorted(
                candidates, reverse=True, key=lambda c: c[0])

            # Trace iteration
            n_pairs_total = sum(1 for v in contagem.values() if v >= 2)
            self._trace.append(f"--- Iter {iter_count} ---")
            self._trace.append(
                f"Sub-tuplas K>=2 com R>=2: {n_pairs_total}  "
                f"net>0: {len(candidates)}")
            if iter_count > 1:
                self._trace.append(
                    "NOTA: alias_markers de iters anteriores sao "
                    "OPACOS pra Counter (limitacao greedy)")
            if candidates_for_trace:
                self._trace.append("Top 10 por net:")
                picked_sub = melhor[0] if melhor else None
                for k_idx, (net, sub, R, baseline, n_tam) in enumerate(candidates_for_trace[:10]):
                    pick = " <- PICK" if sub == picked_sub else ""
                    sub_str = self._emit_refs_range(list(sub))
                    self._trace.append(
                        f"  {sub_str:20s} | R={R} Lr={baseline} "
                        f"len(N)~{n_tam} net=({R-1})*({baseline}-{n_tam})"
                        f"={net}{pick}")
                # Ambiguity check: more than 1 with same max net
                top_net = candidates_for_trace[0][0]
                tied = [c for c in candidates_for_trace if c[0] == top_net]
                if len(tied) > 1:
                    self._trace.append(
                        f"  AMBIGUIDADE: {len(tied)} candidates "
                        f"empatam em net={top_net}; greedy escolheu o 1o por ordem Counter")
            else:
                self._trace.append("Nenhum candidato com net > 0. STOP.")

            if melhor is None:
                self._trace.append("")
                break

            sub, R = melhor
            alias_id_temp = proximo_alias_temp
            proximo_alias_temp += 1
            composicoes_acumuladas_k += len(sub) - 1

            K = len(sub)
            n_subs = 0
            lines_affected = []
            for li in range(len(linha_pedacos)):
                pedacos = linha_pedacos[li]
                if pedacos is None:
                    continue
                novos = []
                line_had_sub = False
                for p in pedacos:
                    if p[0] != 'refs':
                        novos.append(p)
                        continue
                    refs = p[1]
                    i = 0
                    buf = []
                    while i < len(refs):
                        if (i + K <= len(refs)
                                and tuple(refs[i:i + K]) == sub):
                            if buf:
                                novos.append(('refs', buf))
                                buf = []
                            novos.append(('alias_marker',
                                           alias_id_temp, list(sub)))
                            i += K
                            n_subs += 1
                            line_had_sub = True
                        else:
                            buf.append(refs[i])
                            i += 1
                    if buf:
                        novos.append(('refs', buf))
                if line_had_sub:
                    lines_affected.append(li + 1)
                linha_pedacos[li] = novos

            self._trace.append(
                f"Substituido em {n_subs} ocorrencias "
                f"(linhas {lines_affected}); aloca {K-1} composition IDs.")
            self._trace.append("")

        self._trace.append(f"=== STOPPED apos iter {iter_count} ===")
        self._trace.append("")

        # FASE 5: scan body em ordem, atribuir IDs, mapear prov_to_final
        # Decoder aloca IDs interleaved com atoms (lit segments) +
        # composicoes. Encoder simula + mapeia atom IDs prov -> final.
        current_id = 0
        prov_to_final = {}  # provisional atom id -> decoder final id
        comp_id_map = {}    # alias_id_temp -> final_id

        for li in range(len(linha_pedacos)):
            pedacos = linha_pedacos[li]
            if pedacos is None:
                continue
            novos = []
            for p in pedacos:
                if p[0] == 'lit':
                    current_id += 1
                    text = p[1]
                    atom_prov = p[2]
                    prov_to_final[atom_prov] = current_id
                    novos.append(('lit', text))
                elif p[0] == 'refs':
                    refs_prov = p[1]
                    refs_final = [prov_to_final[r] for r in refs_prov]
                    current_id += self._count_ids_in_refs(refs_final)
                    novos.append(('refs', refs_final))
                elif p[0] == 'alias_marker':
                    aid_temp, sub_prov = p[1], p[2]
                    K = len(sub_prov)
                    sub_final = [prov_to_final[r] for r in sub_prov]
                    if aid_temp not in comp_id_map:
                        current_id += K - 1
                        comp_id_map[aid_temp] = current_id
                        novos.append(('composition_def', current_id,
                                       sub_final))
                    else:
                        novos.append(('composition_use',
                                       comp_id_map[aid_temp]))
            linha_pedacos[li] = novos

        # Trace: prov -> final mapping + compositions
        self._trace.append("=== prov -> final atom mapping (Phase 5) ===")
        for prov, final in sorted(prov_to_final.items()):
            self._trace.append(f"  prov {prov:3d} -> final {final:3d}")
        self._trace.append("")

        self._trace.append("=== Compositions (final IDs, ordem body) ===")
        comp_seen = set()
        for li in range(len(linha_pedacos)):
            pedacos = linha_pedacos[li]
            if pedacos is None:
                continue
            for p in pedacos:
                if p[0] == 'composition_def':
                    fid = p[1]
                    if fid in comp_seen:
                        continue
                    comp_seen.add(fid)
                    sub_final = p[2]
                    self._trace.append(
                        f"  comp final {fid:3d} = composition of {sub_final} "
                        f"(emit `{self._emit_composition(sub_final)}`)")
        self._trace.append("")

        # Post-hoc: missed opportunities (adjacent ref pairs nao detectadas)
        pair_count = Counter()
        pair_lines = defaultdict(list)
        for li in range(len(linha_pedacos)):
            pedacos = linha_pedacos[li]
            if pedacos is None:
                continue
            ref_seq = []
            for p in pedacos:
                if p[0] == 'refs':
                    ref_seq.extend(p[1])
                elif p[0] == 'composition_def':
                    ref_seq.append(p[1])
                elif p[0] == 'composition_use':
                    ref_seq.append(p[1])
            for i in range(len(ref_seq) - 1):
                pair = (ref_seq[i], ref_seq[i + 1])
                pair_count[pair] += 1
                if (li + 1) not in pair_lines[pair]:
                    pair_lines[pair].append(li + 1)

        next_id_est = current_id + 1
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

        self._trace.append("=== MISSED OPPORTUNITIES (post-hoc) ===")
        self._trace.append(
            "Pares (X, Y) adjacentes no body final com R>=2 "
            "e net>0 que detector greedy nao capturou:")
        self._trace.append("")
        total_missed = 0
        for net, pair, R, baseline in missed[:30]:
            lines_str = ",".join(str(l) for l in pair_lines[pair])
            self._trace.append(
                f"  pair=({pair[0]},{pair[1]}) "
                f"R={R} lines=[{lines_str}] "
                f"baseline=`{self._emit_refs_range(list(pair))}`={baseline} "
                f"len(N)~{len_n_est} est_savings={net}")
            total_missed += net
        if not missed:
            self._trace.append("  (nenhum)")
        self._trace.append("")
        self._trace.append(f"Total estimated missed bytes: {total_missed}")
        self._trace.append("")
        self._trace.append(
            "NOTA: estimativa otimista — applying any missed alias "
            "may re-shuffle len(N), affecting others. Use as "
            "indicacao qualitativa.")

        # FASE 6: serializar
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
                        if prev_tipo in ('refs', 'composition_def',
                                          'composition_use'):
                            partes.append(',')
                        elif prev_tipo == 'lit' and prev_emit_termina_em_digito:
                            partes.append('*')
                        partes.append(self._emit_refs_range(p[1]))
                        prev_emit_termina_em_digito = True
                        prev_tipo = 'refs'
                    elif t == 'composition_def':
                        if prev_tipo in ('refs', 'composition_def',
                                          'composition_use'):
                            partes.append(',')
                        elif prev_tipo == 'lit' and prev_emit_termina_em_digito:
                            partes.append('*')
                        partes.append(self._emit_composition(p[2]))
                        prev_emit_termina_em_digito = True
                        prev_tipo = 'composition_def'
                    elif t == 'composition_use':
                        if prev_tipo in ('refs', 'composition_def',
                                          'composition_use'):
                            partes.append(',')
                        elif prev_tipo == 'lit' and prev_emit_termina_em_digito:
                            partes.append('*')
                        partes.append(str(p[1]))
                        prev_emit_termina_em_digito = True
                        prev_tipo = 'composition_use'
                linha_resto = ''.join(partes)

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
                # parse refs block (digits, ',', '..', '~')
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
                refs_block = resto[i:j]
                # Split by `,` to get composition units
                units = refs_block.split(',')
                for unit in units:
                    if not unit:
                        continue
                    # Within unit: split by `~` to get groups (ref or range)
                    groups = unit.split('~')
                    unit_refs = []
                    for grp in groups:
                        if '..' in grp:
                            a, b = grp.split('..')
                            for v in range(int(a), int(b) + 1):
                                unit_refs.append(v)
                        else:
                            unit_refs.append(int(grp))
                    if len(unit_refs) >= 2:
                        # Pairwise composition: K-1 IDs allocated
                        prev_str = frags[unit_refs[0]]
                        for ref in unit_refs[1:]:
                            new_str = prev_str + frags[ref]
                            proximo_idx_ref[0] += 1
                            frags[proximo_idx_ref[0]] = new_str
                            prev_str = new_str
                        partes.append(prev_str)
                    else:
                        partes.append(frags[unit_refs[0]])
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
                    elif c.isdigit() or c in ('*', '~'):
                        break
                    else:
                        buf.append(c)
                        i += 1
                texto = ''.join(buf)
                proximo_idx_ref[0] += 1
                frags[proximo_idx_ref[0]] = texto
                partes.append(texto)
        return ''.join(partes)

    def decode(self, tcf_text):
        frags = {}
        proximo_idx_ref = [0]
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
