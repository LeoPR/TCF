"""Sub-exp 01 — profile granular _detect_compositions.

Profile lineitem 5k single-col mais pesado (l_comment ou l_partkey).
Breakdown:
1. Tempo total encode
2. Tempo em _detect_compositions
3. Dentro de _detect_compositions:
   - rebuild Counter (outer loop linhas 238-251)
   - candidates loop (linhas 254-295)
   - _estimate_baseline_chars total
   - pick best (linhas 298-302)
   - substitution (linhas 318-356)
4. Numero de iters do outer loop

Decisao go/no-go pra prototype incremental:
- Se Counter rebuild > 30% do _detect_compositions: GO
- Caso contrario: NO-GO (counter incremental nao vale)

Usa instrumentacao manual (cProfile detecta funcoes, nao secoes
internas — precisa adicionar timestamps).
"""

from __future__ import annotations

import csv
import sys
import time
from collections import Counter, OrderedDict
from pathlib import Path

THIS = Path(__file__).parent
ROOT = THIS.parents[4]
SCRIPTS = ROOT / "scripts"
SRC = ROOT / "src"

sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(SRC))

from dataset_reader import DatasetReader  # noqa: E402
from tcf.composicional.syntax import M8AVirtualRefsSyntax  # noqa: E402
from tcf.column_features import analyze_column  # noqa: E402
from tcf.auto_min_len import detect_min_len_from_features  # noqa: E402
from tcf.core.online import processar  # noqa: E402


def dedup_preserve_order(values):
    seen = OrderedDict()
    for v in values:
        seen[v] = True
    return list(seen.keys())


# Patched _detect_compositions com instrumentacao
class InstrumentedSyntax(M8AVirtualRefsSyntax):
    """Subclass com timing instrumentacao por secao."""

    def __init__(self):
        super().__init__()
        self.timings = {
            'rebuild_counter': 0.0,
            'build_alias_first_line': 0.0,
            'build_candidates': 0.0,
            'estimate_baseline_calls': 0,
            'pick_best': 0.0,
            'substitute': 0.0,
            'iters_total': 0,
            'lines_total': 0,
            'lines_affected_per_iter': [],
        }

    def _detect_compositions(self, pieces_per_line, atom_count):
        next_alias = 1
        comp_acc_k = 0
        alias_to_sub = {}
        iter_traces = []

        n_lines = sum(1 for p in pieces_per_line if p is not None)
        self.timings['lines_total'] = n_lines

        while True:
            # ---- Section: rebuild Counter ----
            t0 = time.perf_counter()
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
            self.timings['rebuild_counter'] += time.perf_counter() - t0

            # ---- Section: build alias_first_line ----
            t0 = time.perf_counter()
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
            self.timings['build_alias_first_line'] += time.perf_counter() - t0

            # ---- Section: build candidates ----
            t0 = time.perf_counter()
            candidates = []
            for sub, R in contagem.items():
                if R < 2:
                    continue
                virtual_count = sum(1 for x in sub if x < 0)
                if virtual_count > 1:
                    continue
                if virtual_count == 1:
                    virt_pos = next(i for i, x in enumerate(sub) if x < 0)
                    if virt_pos > 0:
                        virt_alias = -sub[virt_pos]
                        if alias_first_line.get(virt_alias,
                                                  float('inf')) >= sub_first_line[sub]:
                            continue
                self.timings['estimate_baseline_calls'] += 1
                baseline = self._estimate_baseline_chars(
                    sub, atom_count, comp_acc_k)
                K = len(sub)
                n_tam = len(str(atom_count + comp_acc_k + K - 1))
                if baseline <= n_tam:
                    continue
                candidates.append(((R - 1) * (baseline - n_tam),
                                    sub, R, baseline, n_tam))
            self.timings['build_candidates'] += time.perf_counter() - t0

            # ---- Section: pick best ----
            t0 = time.perf_counter()
            best = None
            best_net = 0
            for net, sub, R, baseline, n_tam in candidates:
                if net > best_net:
                    best_net, best = net, (sub, R)
            self.timings['pick_best'] += time.perf_counter() - t0

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
                self.timings['iters_total'] = len(iter_traces)
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

            # ---- Section: substitute ----
            t0 = time.perf_counter()
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
            self.timings['substitute'] += time.perf_counter() - t0
            self.timings['lines_affected_per_iter'].append(len(iter_info['lines_affected']))

            iter_traces.append(iter_info)
            if len(iter_traces) >= 99:
                self.timings['iters_total'] = len(iter_traces)
                break

        return alias_to_sub, iter_traces


def encode_col_instrumented(values, header="val"):
    """Encode com syntax instrumentado, retorna (body, timings)."""
    unicas = dedup_preserve_order(values)
    features = analyze_column(values)
    min_len = detect_min_len_from_features(features)
    tokens, _ = processar(unicas, min_len=min_len)
    syn = InstrumentedSyntax()
    body = syn.encode(values, unicas, tokens, header)
    return body, syn.timings


def main():
    print("=== Sub-exp 01 — profile breakdown _detect_compositions ===\n")

    reader = DatasetReader("tpch-sf001")
    rows = reader.rows("lineitem", limit=5000)
    cols = {c: [str(r[c]) if r[c] is not None else "" for r in rows]
            for c in rows[0].keys()}
    reader.close()

    # Profile 3 colunas representativas
    targets = ["l_comment", "l_extendedprice", "l_partkey"]
    print(f"Profiling lineitem 5k columns: {targets}\n")

    all_timings = {}
    for cname in targets:
        if cname not in cols:
            continue
        values = cols[cname]
        t_encode_start = time.perf_counter()
        body, timings = encode_col_instrumented(values)
        t_encode_total = time.perf_counter() - t_encode_start
        timings['encode_total'] = t_encode_total
        timings['bytes_body'] = len(body.encode("utf-8"))
        all_timings[cname] = timings

        # Sum sections
        t_dc = (timings['rebuild_counter'] + timings['build_alias_first_line']
                + timings['build_candidates'] + timings['pick_best']
                + timings['substitute'])

        print(f"--- {cname} (bytes={timings['bytes_body']}, iters={timings['iters_total']}) ---")
        print(f"  encode_total: {t_encode_total:.3f}s")
        print(f"  _detect_compositions (sum sections): {t_dc:.3f}s "
              f"({t_dc / t_encode_total * 100:.1f}% do encode)")
        if t_dc > 0:
            print(f"    rebuild_counter:        {timings['rebuild_counter']:.3f}s "
                  f"({timings['rebuild_counter'] / t_dc * 100:.1f}% do _dc)")
            print(f"    build_alias_first_line: {timings['build_alias_first_line']:.3f}s "
                  f"({timings['build_alias_first_line'] / t_dc * 100:.1f}% do _dc)")
            print(f"    build_candidates:       {timings['build_candidates']:.3f}s "
                  f"({timings['build_candidates'] / t_dc * 100:.1f}% do _dc)")
            print(f"    pick_best:              {timings['pick_best']:.3f}s "
                  f"({timings['pick_best'] / t_dc * 100:.1f}% do _dc)")
            print(f"    substitute:             {timings['substitute']:.3f}s "
                  f"({timings['substitute'] / t_dc * 100:.1f}% do _dc)")
        print(f"  estimate_baseline_calls: {timings['estimate_baseline_calls']}")
        print(f"  lines_total: {timings['lines_total']}, "
              f"lines_affected_per_iter avg: "
              f"{sum(timings['lines_affected_per_iter']) / max(1, len(timings['lines_affected_per_iter'])):.1f}")
        print()

    # Veredito
    print("=== Veredito go/no-go ===\n")
    max_rebuild_pct = 0
    for cname, timings in all_timings.items():
        t_dc = (timings['rebuild_counter'] + timings['build_alias_first_line']
                + timings['build_candidates'] + timings['pick_best']
                + timings['substitute'])
        if t_dc > 0:
            rebuild_pct = timings['rebuild_counter'] / t_dc * 100
            max_rebuild_pct = max(max_rebuild_pct, rebuild_pct)
            n_affected = (sum(timings['lines_affected_per_iter'])
                          / max(1, len(timings['lines_affected_per_iter'])))
            n_total = timings['lines_total']
            affected_pct = n_affected / n_total * 100 if n_total else 0
            print(f"  {cname}: rebuild_counter = {rebuild_pct:.1f}% do _dc, "
                  f"lines_afetadas avg = {affected_pct:.1f}% do total")

    print(f"\nMax rebuild_counter pct: {max_rebuild_pct:.1f}%")
    if max_rebuild_pct >= 30:
        print("** GO: counter incremental vale prototype **")
    else:
        print("** NO-GO: rebuild_counter < 30% — counter incremental nao vale **")
        print("  Adiar H-PERF-05d. Outras hipoteses Pacote 4 (Cython port) podem ter mais valor.")

    # Report
    report = [
        "# Sub-exp 01 — profile breakdown _detect_compositions",
        "",
        "## Setup",
        "",
        "Profile com instrumentacao manual (subclass InstrumentedSyntax).",
        "Lineitem 5k, 3 colunas representativas (l_comment, l_extendedprice, l_partkey).",
        "",
        "## Breakdown por coluna",
        "",
        "| Col | bytes | iters | encode (s) | _dc (s) | rebuild_counter (s/%) | build_alias_first_line | build_candidates | substitute |",
        "|---|---:|---:|---:|---:|---|---|---|---|",
    ]
    for cname, t in all_timings.items():
        t_dc = (t['rebuild_counter'] + t['build_alias_first_line']
                + t['build_candidates'] + t['pick_best'] + t['substitute'])
        rebuild_pct = t['rebuild_counter'] / t_dc * 100 if t_dc else 0
        afl_pct = t['build_alias_first_line'] / t_dc * 100 if t_dc else 0
        bc_pct = t['build_candidates'] / t_dc * 100 if t_dc else 0
        sub_pct = t['substitute'] / t_dc * 100 if t_dc else 0
        report.append(
            f"| {cname} | {t['bytes_body']} | {t['iters_total']} | "
            f"{t['encode_total']:.3f} | {t_dc:.3f} | "
            f"{t['rebuild_counter']:.3f} ({rebuild_pct:.1f}%) | "
            f"{t['build_alias_first_line']:.3f} ({afl_pct:.1f}%) | "
            f"{t['build_candidates']:.3f} ({bc_pct:.1f}%) | "
            f"{t['substitute']:.3f} ({sub_pct:.1f}%) |"
        )

    report.extend([
        "",
        "## Linhas afetadas por iter (% do total)",
        "",
        "| Col | lines_total | lines_affected avg | % |",
        "|---|---:|---:|---:|",
    ])
    for cname, t in all_timings.items():
        n_affected = (sum(t['lines_affected_per_iter'])
                      / max(1, len(t['lines_affected_per_iter'])))
        pct = n_affected / t['lines_total'] * 100 if t['lines_total'] else 0
        report.append(f"| {cname} | {t['lines_total']} | {n_affected:.1f} | "
                      f"{pct:.1f}% |")

    report.extend([
        "",
        "## Veredito",
        "",
        f"**Max rebuild_counter pct entre colunas testadas: {max_rebuild_pct:.1f}%**",
        "",
    ])
    if max_rebuild_pct >= 30:
        report.append("**GO**: counter incremental vale prototype "
                      "(rebuild_counter dominante).")
    else:
        report.append(f"**NO-GO**: rebuild_counter < 30% "
                      f"({max_rebuild_pct:.1f}%). Counter incremental nao "
                      f"traria ganho significativo. Adiar H-PERF-05d.")
        report.append("")
        report.append("Outras hipoteses Pacote 4 com mais potencial:")
        report.append("- H-PERF-06 Cython/Rust port (alto custo, alto ganho)")
        report.append("- Otimizar secao dominante real (build_candidates ou substitute)")

    out = THIS / "result.md"
    out.write_bytes(("\n".join(report) + "\n").encode("utf-8"))
    print(f"\nresult.md: {out}")


if __name__ == "__main__":
    main()
