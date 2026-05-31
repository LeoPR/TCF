"""Audit: identifica oportunidades residuais no body fork (pos tentativa 02).

Para cada par/tripla de linhas consecutivas NAO-compactadas, classifica:
- Tipo A: mesmo length, diffs em digit positions (escape ou ref)
- Tipo B: lengths diferem mas tokens parecidos
- Tipo C: completamente diferentes (fora de alcance grammar)

Reporta bytes residuais por tipo, por dataset.

Outputs:
- audit.md (sintese)
- outputs/<dataset>/body-fork-analyzed.tcf (copia do input pra inspecao)
- outputs/<dataset>/pairs-detailed.md (per-pair detalhado)
- outputs/<dataset>/residual-stats.txt (numerico)
"""

from __future__ import annotations

from pathlib import Path

THIS = Path(__file__).parent
LAB = THIS.parent
FORK_OUTPUTS = LAB / "02-hcc-sozinho-rle-near-identical" / "outputs"
OUTPUTS = THIS / "outputs"

DATASETS = [
    "D11a-datas-dia",
    "D11b-datas-borda",
    "D11c-datas-mensal",
    "D11d-datetime-min",
    "D11e-datetime-mensal",
    "D11f-datetime-ms",
    "D11g-datetime-us",
    "D11h-datetime-ns",
]


def write_lf(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content.encode("utf-8"))


def is_compacted_marker(line: str) -> bool:
    """Linha ja' e' RLE/seq-RLE marker?"""
    if not line.startswith("*"):
        return False
    bar = line.find("|")
    return bar > 0


def classify_pair(line_a: str, line_b: str) -> tuple[str, str]:
    """Classifica par (line_a, line_b) consecutivos.

    Retorna (tipo, justificativa) onde tipo in {'A', 'B', 'C', 'identical'}.
    """
    if line_a == line_b:
        return ("identical", "iguais (RLE puro ja' deve agrupar)")
    if len(line_a) == len(line_b):
        diffs = [k for k in range(len(line_a)) if line_a[k] != line_b[k]]
        all_diff_digit = all(line_a[k].isdigit() and line_b[k].isdigit()
                             for k in diffs)
        if all_diff_digit:
            return ("A", f"mesmo length ({len(line_a)}), {len(diffs)} diffs todos digit")
        return ("C", f"mesmo length, mas diffs incluem non-digit em pos {diffs}")
    common_chars = set(line_a) & set(line_b)
    if len(common_chars) >= 3:
        return ("B", f"lengths diferem ({len(line_a)} vs {len(line_b)}), {len(common_chars)} chars compartilhados")
    return ("C", f"lengths diferem, pouca sobreposicao")


def find_arith_seq_in_digits(line_a: str, line_b: str) -> list[tuple[int, int, int]]:
    """Retorna runs de digits e calcula delta. (start, end_exclusive, delta)."""
    runs = []
    i = 0
    n = len(line_a)
    while i < n:
        if line_a[i].isdigit() and line_b[i].isdigit():
            j = i
            while j < n and line_a[j].isdigit() and line_b[j].isdigit():
                j += 1
            a_int = int(line_a[i:j])
            b_int = int(line_b[i:j])
            if a_int != b_int:
                runs.append((i, j, b_int - a_int))
            i = j
        else:
            i += 1
    return runs


def char_diff_marker(line_a: str, line_b: str) -> str:
    """Retorna string com `^` nas posicoes diferentes."""
    if len(line_a) != len(line_b):
        return f"(lengths diferem: {len(line_a)} vs {len(line_b)})"
    out = []
    for k in range(len(line_a)):
        out.append('^' if line_a[k] != line_b[k] else ' ')
    return ''.join(out)


def audit_dataset(ds: str) -> dict:
    body_path = FORK_OUTPUTS / ds / "2-body-fork.tcf"
    text = body_path.read_text(encoding="utf-8")
    lines = text.rstrip('\n').split('\n')

    pairs = []
    runs_already = []  # markers ja' compactados
    i = 0
    while i < len(lines):
        if is_compacted_marker(lines[i]):
            runs_already.append((i + 1, lines[i]))
            i += 1
            continue
        if i < len(lines) - 1:
            a = lines[i]
            b = lines[i + 1]
            if is_compacted_marker(b):
                i += 1
                continue
            tipo, just = classify_pair(a, b)
            entry = {
                'line_a_idx': i + 1,
                'line_b_idx': i + 2,
                'line_a': a,
                'line_b': b,
                'tipo': tipo,
                'just': just,
            }
            if tipo == 'A':
                digit_runs = find_arith_seq_in_digits(a, b)
                entry['digit_runs'] = digit_runs
                if digit_runs:
                    deltas = [r[2] for r in digit_runs]
                    entry['delta_consistent'] = (len(set(deltas)) == 1)
                    entry['delta'] = deltas[0] if entry['delta_consistent'] else None
                    # Quais sao escape-digit vs ref-id?
                    entry['note_escape'] = (
                        'detector atual exige escape-digit; aqui nao tem `\\`'
                        if '\\' not in a else
                        'tem escape-digit; pegavel'
                    )
                else:
                    entry['delta_consistent'] = False
                    entry['delta'] = None
            pairs.append(entry)
        i += 1

    tipo_counts = {'A': 0, 'B': 0, 'C': 0, 'identical': 0}
    bytes_per_tipo = {'A': 0, 'B': 0, 'C': 0, 'identical': 0}
    for p in pairs:
        tipo_counts[p['tipo']] += 1
        bytes_per_tipo[p['tipo']] += len(p['line_b']) + 1

    return {
        'dataset': ds,
        'pairs': pairs,
        'tipo_counts': tipo_counts,
        'bytes_per_tipo': bytes_per_tipo,
        'total_pairs': len(pairs),
        'total_lines': len(lines),
        'runs_already': runs_already,
        'body_text': text,
        'body_lines': lines,
    }


def render_dataset_pairs_md(r: dict) -> str:
    """Detalhado pra outputs/<ds>/pairs-detailed.md."""
    out = [
        f"# Pairs detalhados — {r['dataset']}",
        "",
        f"Total linhas body fork: {r['total_lines']}",
        f"Pares nao-compactados: {r['total_pairs']}",
        f"Runs ja' compactados (markers `*N|` ou `*N+delta|`): {len(r['runs_already'])}",
        "",
        "## Runs ja' compactados",
        "",
    ]
    if r['runs_already']:
        for idx, marker in r['runs_already']:
            out.append(f"- linha {idx}: `{marker}`")
    else:
        out.append("(nenhum)")
    out.append("")
    out.append("## Body inteiro (referencia)")
    out.append("")
    out.append("```")
    for i, ln in enumerate(r['body_lines']):
        marker = "*" if is_compacted_marker(ln) else " "
        out.append(f"{marker}{i+1:3d} {ln}")
    out.append("```")
    out.append("")
    out.append("(prefixo `*` = ja' compactado)")
    out.append("")
    out.append("## Cada par nao-compactado, em detalhe")
    out.append("")
    if not r['pairs']:
        out.append("(nenhum)")
        return "\n".join(out) + "\n"
    for p in r['pairs']:
        out.append(f"### Par linhas {p['line_a_idx']}-{p['line_b_idx']} — Tipo {p['tipo']}")
        out.append("")
        out.append(f"**Justificativa**: {p['just']}")
        out.append("")
        out.append("```")
        out.append(f"a: `{p['line_a']}`")
        out.append(f"b: `{p['line_b']}`")
        if len(p['line_a']) == len(p['line_b']):
            mark = char_diff_marker(p['line_a'], p['line_b'])
            out.append(f"    {mark} (^ = diff)")
        out.append("```")
        out.append("")
        if p['tipo'] == 'A':
            out.append(f"**Digit runs com delta**: {p.get('digit_runs')}")
            out.append(f"**Delta consistente?** {p.get('delta_consistent')} "
                       f"(delta={p.get('delta')})")
            out.append(f"**Nota**: {p.get('note_escape', '')}")
            out.append("")
        elif p['tipo'] == 'B':
            out.append("**Caminho pra tratar**: requer cooperacao OBAT (manter shape) "
                       "OU grammar nova (refs relativos)")
            out.append("")
        elif p['tipo'] == 'C':
            out.append("**Caminho pra tratar**: fora de alcance grammar atual")
            out.append("")
    return "\n".join(out) + "\n"


def render_dataset_stats(r: dict) -> str:
    """Numerico — outputs/<ds>/residual-stats.txt."""
    out = [
        f"# Residual stats — {r['dataset']}",
        "",
        f"body_lines_total: {r['total_lines']}",
        f"pairs_nao_compactados: {r['total_pairs']}",
        f"runs_ja_compactados: {len(r['runs_already'])}",
        "",
        "## Por tipo",
    ]
    for tipo in ['A', 'B', 'C', 'identical']:
        out.append(f"  {tipo}: count={r['tipo_counts'][tipo]:2}  "
                   f"bytes={r['bytes_per_tipo'][tipo]:4}")
    out.append("")
    out.append("## Total bytes residual")
    total = sum(r['bytes_per_tipo'].values())
    out.append(f"  {total}")
    return "\n".join(out) + "\n"


def render_audit(results: list[dict]) -> str:
    out = [
        "# Audit — oportunidades residuais pos-tentativa 02",
        "",
        "## Resumo (todos D11a-h)",
        "",
        "| Dataset | total lines | pairs nao-compact | A | B | C | identical |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for r in results:
        tc = r['tipo_counts']
        out.append(
            f"| {r['dataset']} | {r['total_lines']} | {r['total_pairs']} | "
            f"{tc['A']} | {tc['B']} | {tc['C']} | {tc['identical']} |"
        )
    out.append("")
    out.append("## Bytes potencialmente recuperaveis (por tipo)")
    out.append("")
    out.append("| Dataset | A (bytes) | B (bytes) | C (bytes) |")
    out.append("|---|---:|---:|---:|")
    total_A = 0
    total_B = 0
    total_C = 0
    for r in results:
        bp = r['bytes_per_tipo']
        out.append(f"| {r['dataset']} | {bp['A']} | {bp['B']} | {bp['C']} |")
        total_A += bp['A']
        total_B += bp['B']
        total_C += bp['C']
    out.append(f"| **TOTAL** | **{total_A}** | **{total_B}** | **{total_C}** |")
    out.append("")
    out.append("Legenda:")
    out.append("- **A**: mesmo length, diffs todos digit → potencialmente tratavel se delta consistente")
    out.append("- **B**: lengths diferem, alguma sobreposicao → tratavel exigiria grammar nova OU OBAT cooperar")
    out.append("- **C**: fora de alcance grammar atual")
    out.append("- **identical**: deveria ja' ter sido pego pelo RLE puro do canonical")
    out.append("")
    out.append("## Outputs por dataset")
    out.append("")
    out.append("Cada dataset tem 3 arquivos em `outputs/<dataset>/`:")
    out.append("- `body-fork-analyzed.tcf` — copia do input (do sub-exp 02) pra inspecao auto-contida")
    out.append("- `pairs-detailed.md` — cada par nao-compactado com a, b, diff marker, justificativa, caminho-pra-tratar")
    out.append("- `residual-stats.txt` — numerico (count + bytes por tipo)")
    out.append("")
    out.append("## Detalhes por dataset (so' pares nao-compactados — sintese)")
    out.append("")
    for r in results:
        out.append(f"### {r['dataset']}")
        out.append("")
        out.append(f"→ [pairs-detailed.md](outputs/{r['dataset']}/pairs-detailed.md) "
                   f"| [body-fork-analyzed.tcf](outputs/{r['dataset']}/body-fork-analyzed.tcf) "
                   f"| [residual-stats.txt](outputs/{r['dataset']}/residual-stats.txt)")
        out.append("")
        if not r['pairs']:
            out.append("(nenhum par nao-compactado)")
            out.append("")
            continue
        out.append("| Linhas | Tipo | A: delta? | a | b | justificativa |")
        out.append("|---|---|---|---|---|---|")
        for p in r['pairs']:
            delta_str = ""
            if p['tipo'] == 'A':
                if p.get('delta_consistent'):
                    delta_str = f"Δ={p['delta']:+d}"
                else:
                    delta_str = "incon."
            out.append(
                f"| {p['line_a_idx']}-{p['line_b_idx']} | {p['tipo']} | "
                f"{delta_str} | `{p['line_a']}` | `{p['line_b']}` | "
                f"{p['just']} |"
            )
        out.append("")
    return "\n".join(out) + "\n"


def main() -> None:
    print("=== Audit — oportunidades residuais ===\n")
    results = []
    for ds in DATASETS:
        r = audit_dataset(ds)
        results.append(r)
        # Per-dataset outputs
        ds_dir = OUTPUTS / ds
        write_lf(ds_dir / "body-fork-analyzed.tcf", r['body_text'])
        write_lf(ds_dir / "pairs-detailed.md", render_dataset_pairs_md(r))
        write_lf(ds_dir / "residual-stats.txt", render_dataset_stats(r))
        tc = r['tipo_counts']
        bp = r['bytes_per_tipo']
        print(
            f"  {ds:24}  "
            f"pairs={r['total_pairs']:2}  "
            f"A={tc['A']} ({bp['A']}B)  "
            f"B={tc['B']} ({bp['B']}B)  "
            f"C={tc['C']} ({bp['C']}B)  "
            f"runs_ja={len(r['runs_already'])}"
        )

    # Top-level audit.md
    write_lf(THIS / "audit.md", render_audit(results))
    print(f"\naudit.md: {THIS / 'audit.md'}")
    print(f"outputs/: {OUTPUTS}")
    print(f"  -> {len(DATASETS)} dirs, cada uma com 3 arquivos")


if __name__ == "__main__":
    main()
