"""Geracao de tabelas markdown formatadas (bold/italic/sort).

Cada `write_NN_*()` produz um arquivo `reports/NN-*.md` independente.
Indice em `README.md` (gerado externamente).
"""

from __future__ import annotations

import statistics
from pathlib import Path
from typing import Iterable


def fmt_minmax(
    values: list[float],
    fmtstr: str = "{:.0f}",
    bold_min: bool = True,
    italic_second_min: bool = True,
) -> list[str]:
    """Marca **min** (bold) e _segundo-min_ (italico) em uma linha."""
    if not values:
        return []
    sorted_unique = sorted(set(values))
    min_v = sorted_unique[0]
    second_min = sorted_unique[1] if len(sorted_unique) > 1 else None
    out = []
    for v in values:
        s = fmtstr.format(v)
        if bold_min and v == min_v:
            out.append(f"**{s}**")
        elif italic_second_min and second_min is not None and v == second_min:
            out.append(f"_{s}_")
        else:
            out.append(s)
    return out


def make_table(
    headers: list[str],
    rows: list[list[str]],
    align_right_cols: Iterable[int] = (),
) -> str:
    """Tabela markdown com alinhamento opcional."""
    align_right = set(align_right_cols)
    aligns = ["---:" if i in align_right else "---" for i in range(len(headers))]
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("|" + "|".join(aligns) + "|")
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


# ---- 00-resumo ------------------------------------------------------------

def write_resumo(
    path: Path,
    per_dataset: dict,
    ds_list: list[str],
    formats: list[str],
    compressors: list[str],
    config: dict,
    timestamp: str,
) -> None:
    out: list[str] = []
    out.append("# EXP-008 — Resumo executivo\n")
    out.append(f"**Data execucao**: {timestamp}\n")
    out.append(f"**Datasets**: {len(ds_list)}")
    out.append(f"**Formatos input**: {', '.join(formats)}")
    out.append(f"**Compressores**: {', '.join(compressors)} (niveis maximos)")
    out.append(
        f"**Reps**: serialize/parse={config['reps_serialize']}, "
        f"compress/decompress={config['reps_compress']}"
    )
    out.append("")

    # Totais por formato (raw, sem compressao)
    totals_raw = {
        f: sum(per_dataset[d]["formats"][f]["bytes"] for d in ds_list)
        for f in formats
    }
    out.append("## Totais por formato (sem compressao)\n")
    fmt_rows = []
    fmt_vals = [totals_raw[f] for f in formats]
    fmt_cells = fmt_minmax(fmt_vals, "{:.0f}")
    for f, cell in zip(formats, fmt_cells):
        fmt_rows.append([f, cell])
    out.append(make_table(["formato", "bytes total"], fmt_rows, [1]))
    out.append("")
    out.append(
        "**Bold** = formato mais compacto sem compressao. "
        "_Italico_ = segundo mais compacto.\n"
    )

    # Matriz formato × compressor (totais)
    out.append("## Totais por formato × compressor\n")
    headers = ["formato"] + compressors
    matrix: list[list[float]] = []
    for f in formats:
        row = [
            sum(
                per_dataset[d]["formats"][f]["compressors"][c]["bytes"]
                for d in ds_list
            )
            for c in compressors
        ]
        matrix.append(row)

    rows = []
    for f, row_vals in zip(formats, matrix):
        cells = fmt_minmax(row_vals, "{:.0f}")
        rows.append([f] + cells)
    out.append(make_table(headers, rows, list(range(1, len(headers)))))
    out.append("")
    out.append(
        "Cada celula = **bytes totais** da soma dos 15 datasets "
        "comprimidos com (formato, compressor). **Bold** = melhor "
        "compressor pra esse formato. _Italico_ = segundo.\n"
    )

    # Best overall
    best = None
    for fi, f in enumerate(formats):
        for ci, c in enumerate(compressors):
            v = matrix[fi][ci]
            if best is None or v < best[2]:
                best = (f, c, v)
    raw_total_csv = totals_raw["csv"]
    out.append("## Combinacao mais compacta\n")
    out.append(
        f"- **Vencedor (bytes totais)**: `{best[0]} → {best[1]}` "
        f"com {best[2]} bytes total ({best[2]/raw_total_csv*100:.1f}% "
        f"do raw CSV)."
    )
    out.append(
        f"- **Limite inferior empirico** (menor por dataset): "
        f"`{_best_per_dataset_total(per_dataset, ds_list, formats, compressors)}`"
        f" bytes total."
    )
    out.append("")

    # RT
    rt_format = all(
        per_dataset[d]["formats"][f]["rt"]
        for d in ds_list for f in formats
    )
    rt_full = all(
        per_dataset[d]["formats"][f]["compressors"][c]["rt_full"]
        for d in ds_list for f in formats for c in compressors
    )
    out.append("## Roundtrip\n")
    out.append(
        f"- RT formato (parse(serialize(D)) == D): "
        f"**{_count_rt_format(per_dataset, ds_list, formats)}** OK."
    )
    out.append(
        f"- RT full (parse(decompress(compress(serialize(D)))) == D): "
        f"**{_count_rt_full(per_dataset, ds_list, formats, compressors)}** OK."
    )
    if rt_format and rt_full:
        out.append("- **Sem falhas detectadas.**")
    out.append("")

    out.append("## Indice de reports\n")
    out.append("- [01-bytes-por-formato.md](01-bytes-por-formato.md) — bytes por dataset × formato")
    out.append("- [02-bytes-por-classe.md](02-bytes-por-classe.md) — bytes agregados por classe de compressor")
    out.append("- [03-latencia.md](03-latencia.md) — latencia serialize/parse/compress/decompress")
    out.append("- [04-roundtrip.md](04-roundtrip.md) — verificacao de RT em todas as combinacoes")
    out.append("- [05-campeao-por-dataset.md](05-campeao-por-dataset.md) — menor combinacao por dataset")
    out.append("")

    path.write_text("\n".join(out), encoding="utf-8", newline="\n")


def _best_per_dataset_total(per_dataset, ds_list, formats, compressors):
    total = 0
    for d in ds_list:
        best = min(
            per_dataset[d]["formats"][f]["compressors"][c]["bytes"]
            for f in formats for c in compressors
        )
        total += best
    return total


def _count_rt_format(per_dataset, ds_list, formats):
    ok = sum(
        1 for d in ds_list for f in formats
        if per_dataset[d]["formats"][f]["rt"]
    )
    return f"{ok}/{len(ds_list)*len(formats)}"


def _count_rt_full(per_dataset, ds_list, formats, compressors):
    ok = sum(
        1 for d in ds_list for f in formats for c in compressors
        if per_dataset[d]["formats"][f]["compressors"][c]["rt_full"]
    )
    return f"{ok}/{len(ds_list)*len(formats)*len(compressors)}"


# ---- 01-bytes-por-formato ------------------------------------------------

def write_bytes_por_formato(
    path: Path,
    per_dataset: dict,
    ds_list: list[str],
    formats: list[str],
) -> None:
    out: list[str] = []
    out.append("# 01 — Bytes por dataset × formato (sem compressao)\n")
    out.append(
        "Quanto cada formato textual ocupa por dataset, antes de "
        "qualquer compressao externa. "
        "**Bold** = menor por linha. _Italico_ = segundo menor.\n"
    )

    out.append("## Tabela\n")
    headers = ["dataset", "linhas"] + formats
    rows = []
    for d in ds_list:
        n_lines = per_dataset[d]["raw_lines"]
        vals = [per_dataset[d]["formats"][f]["bytes"] for f in formats]
        cells = fmt_minmax(vals)
        rows.append([d, str(n_lines)] + cells)
    # Total
    total_vals = [
        sum(per_dataset[d]["formats"][f]["bytes"] for d in ds_list)
        for f in formats
    ]
    total_cells = fmt_minmax(total_vals)
    total_lines = sum(per_dataset[d]["raw_lines"] for d in ds_list)
    rows.append(
        ["**TOTAL**", f"**{total_lines}**"]
        + [f"**{c}**" if "**" not in c else c for c in total_cells]
    )

    out.append(make_table(
        headers, rows,
        align_right_cols=list(range(1, len(headers))),
    ))
    out.append("")

    # Observacoes computadas
    out.append("## Observacoes\n")
    # Quem ganha quantos datasets?
    wins: dict[str, int] = {f: 0 for f in formats}
    for d in ds_list:
        vals = [(f, per_dataset[d]["formats"][f]["bytes"]) for f in formats]
        winner = min(vals, key=lambda x: x[1])[0]
        wins[winner] += 1
    wins_str = ", ".join(f"`{f}`={n}" for f, n in wins.items() if n > 0)
    out.append(f"- **Formato mais compacto por dataset**: {wins_str}.")

    # Ratio TCF vs CSV
    tcf_total = sum(per_dataset[d]["formats"]["tcf"]["bytes"] for d in ds_list)
    csv_total = sum(per_dataset[d]["formats"]["csv"]["bytes"] for d in ds_list)
    out.append(
        f"- **TCF / CSV total**: {tcf_total} / {csv_total} = "
        f"{tcf_total/csv_total*100:.1f}%."
    )
    # Ratio JSON-array vs CSV
    json_total = sum(per_dataset[d]["formats"]["json"]["bytes"] for d in ds_list)
    jsonl_total = sum(per_dataset[d]["formats"]["jsonl"]["bytes"] for d in ds_list)
    out.append(
        f"- **JSON array / CSV total**: {json_total} / {csv_total} = "
        f"{json_total/csv_total*100:.1f}%."
    )
    out.append(
        f"- **JSONL / CSV total**: {jsonl_total} / {csv_total} = "
        f"{jsonl_total/csv_total*100:.1f}%."
    )
    out.append("")
    out.append(
        "TCF, JSON e JSONL sao avaliados como **contra-prova de formato**: "
        "se TCF reduzir vs CSV, e JSON tambem reduzir, entao o ganho do "
        "TCF nao e' apenas escape de delimitador — e' compactacao "
        "de redundancia."
    )

    path.write_text("\n".join(out), encoding="utf-8", newline="\n")


# ---- 02-bytes-por-classe -------------------------------------------------

def write_bytes_por_classe(
    path: Path,
    per_dataset: dict,
    ds_list: list[str],
    formats: list[str],
    compressors_meta: dict[str, dict],
    classes: list[str],
) -> None:
    out: list[str] = []
    out.append("# 02 — Bytes por classe de compressor\n")
    out.append(
        "Compressores agrupados por **natureza de uso**. "
        "Ver [`../notes/classificacao-compressores.md`](../notes/classificacao-compressores.md)."
    )
    out.append("")

    out.append("## Membros por classe\n")
    rows = []
    for cls in classes:
        members = [
            c for c, meta in compressors_meta.items() if cls in meta["classes"]
        ]
        rows.append([f"`{cls}`", ", ".join(f"`{m}`" for m in members)])
    out.append(make_table(["classe", "membros"], rows))
    out.append("")

    # Para cada classe, total por (formato, compressor in classe)
    for cls in classes:
        members = [
            c for c, meta in compressors_meta.items() if cls in meta["classes"]
        ]
        if not members:
            continue

        out.append(f"## Classe `{cls}`\n")
        out.append(f"Compressores: {', '.join(f'`{m}`' for m in members)}\n")

        headers = ["dataset"] + [
            f"{f}/{c}" for f in formats for c in members
        ]
        rows = []
        for d in ds_list:
            vals = [
                per_dataset[d]["formats"][f]["compressors"][c]["bytes"]
                for f in formats for c in members
            ]
            cells = fmt_minmax(vals)
            rows.append([d] + cells)
        # Total
        total_vals = [
            sum(
                per_dataset[d]["formats"][f]["compressors"][c]["bytes"]
                for d in ds_list
            )
            for f in formats for c in members
        ]
        total_cells = fmt_minmax(total_vals)
        rows.append(["**TOTAL**"] + [f"**{c}**" if "**" not in c else c for c in total_cells])

        out.append(make_table(
            headers, rows,
            align_right_cols=list(range(1, len(headers))),
        ))
        out.append("")

    # Comparacao entre classes (best per class)
    out.append("## Melhor por dataset, por classe\n")
    out.append(
        "Para cada dataset, menor bytes alcancado em **qualquer** "
        "compressor da classe × **qualquer** formato. "
        "**Bold** = melhor classe pra esse dataset."
    )
    out.append("")
    headers = ["dataset"] + classes
    rows = []
    for d in ds_list:
        per_class = []
        for cls in classes:
            members = [
                c for c, meta in compressors_meta.items()
                if cls in meta["classes"]
            ]
            if not members:
                per_class.append(None)
                continue
            best = min(
                per_dataset[d]["formats"][f]["compressors"][c]["bytes"]
                for f in formats for c in members
            )
            per_class.append(best)

        # Format min/2nd-min
        vals_for_fmt = [v if v is not None else float("inf") for v in per_class]
        cells = fmt_minmax(vals_for_fmt)
        cells = [c if v is not None else "-" for c, v in zip(cells, per_class)]
        rows.append([d] + cells)
    out.append(make_table(
        headers, rows, align_right_cols=list(range(1, len(headers))),
    ))
    out.append("")

    path.write_text("\n".join(out), encoding="utf-8", newline="\n")


# ---- 03-latencia ---------------------------------------------------------

def write_latencia(
    path: Path,
    per_dataset: dict,
    ds_list: list[str],
    formats: list[str],
    compressors: list[str],
    config: dict,
) -> None:
    out: list[str] = []
    out.append("# 03 — Latencia (microssegundos)\n")
    out.append(
        f"Compressao nos niveis maximos. Medianas de "
        f"{config['reps_serialize']} reps (serialize/parse) e "
        f"{config['reps_compress']} reps (compress/decompress). "
        "Resolucao do clock ≈ 100ns em Windows; operacoes <10us tem "
        "ruido relevante.\n"
    )

    # Serialize/parse
    out.append("## Serialize / parse por formato\n")
    out.append("Mediana **entre datasets** (us).\n")
    headers = ["formato", "serialize", "parse"]
    rows = []
    ser_vals = []
    par_vals = []
    for f in formats:
        s_med = statistics.median(
            per_dataset[d]["formats"][f]["t_serialize_us"] for d in ds_list
        )
        p_med = statistics.median(
            per_dataset[d]["formats"][f]["t_parse_us"] for d in ds_list
        )
        ser_vals.append(s_med)
        par_vals.append(p_med)

    ser_cells = fmt_minmax(ser_vals, "{:.1f}")
    par_cells = fmt_minmax(par_vals, "{:.1f}")
    for f, sc, pc in zip(formats, ser_cells, par_cells):
        rows.append([f, sc, pc])
    out.append(make_table(headers, rows, [1, 2]))
    out.append("")

    # Compress por compressor (mediana entre formato × dataset)
    out.append("## Compress por compressor\n")
    out.append("Mediana **entre todos os pares (formato × dataset)** (us).\n")
    rows = []
    c_vals = []
    d_vals = []
    for c in compressors:
        cs = [
            per_dataset[d]["formats"][f]["compressors"][c]["t_compress_us"]
            for d in ds_list for f in formats
        ]
        ds_ = [
            per_dataset[d]["formats"][f]["compressors"][c]["t_decompress_us"]
            for d in ds_list for f in formats
        ]
        c_vals.append(statistics.median(cs))
        d_vals.append(statistics.median(ds_))

    c_cells = fmt_minmax(c_vals, "{:.1f}")
    d_cells = fmt_minmax(d_vals, "{:.1f}")
    headers = ["compressor", "compress (us)", "decompress (us)"]
    for c, cc, dc in zip(compressors, c_cells, d_cells):
        rows.append([c, cc, dc])
    out.append(make_table(headers, rows, [1, 2]))
    out.append("")

    # Ranking
    out.append("## Ranking (mediana global)\n")
    pairs = [
        (c, c_vals[i] + d_vals[i])
        for i, c in enumerate(compressors)
    ]
    pairs.sort(key=lambda x: x[1])
    out.append(
        "Ordenados por **soma de mediana compress + decompress** "
        "(ida e volta, menor = mais rapido)."
    )
    out.append("")
    headers = ["pos", "compressor", "compress + decompress (us)"]
    rows = []
    for i, (c, total) in enumerate(pairs, start=1):
        rows.append([str(i), f"`{c}`", f"{total:.1f}"])
    out.append(make_table(headers, rows, [0, 2]))
    out.append("")

    out.append("## Detalhe por dataset (compress sobre tcf)\n")
    headers = ["dataset"] + compressors
    rows = []
    for d in ds_list:
        vals = [
            per_dataset[d]["formats"]["tcf"]["compressors"][c]["t_compress_us"]
            for c in compressors
        ]
        cells = fmt_minmax(vals, "{:.1f}")
        rows.append([d] + cells)
    out.append(make_table(
        headers, rows, align_right_cols=list(range(1, len(headers))),
    ))

    path.write_text("\n".join(out), encoding="utf-8", newline="\n")


# ---- 04-roundtrip --------------------------------------------------------

def write_roundtrip(
    path: Path,
    per_dataset: dict,
    ds_list: list[str],
    formats: list[str],
    compressors: list[str],
) -> None:
    out: list[str] = []
    out.append("# 04 — Roundtrip\n")
    out.append(
        "Verificacao de identidade nas N combinacoes "
        "formato × compressor × dataset.\n"
    )

    # Format RT
    rt_fmt = {
        (d, f): per_dataset[d]["formats"][f]["rt"]
        for d in ds_list for f in formats
    }
    total = len(rt_fmt)
    ok = sum(1 for v in rt_fmt.values() if v)
    out.append("## RT formato\n")
    out.append(
        f"`parse(serialize(linhas)) == linhas` — **{ok}/{total}** OK."
    )
    if ok < total:
        out.append("\n**Falhas**:")
        for (d, f), v in rt_fmt.items():
            if not v:
                out.append(f"- `{d}` × `{f}` — FAIL")
    out.append("")

    # Compressor RT (bytes-level)
    rt_comp = {
        (d, f, c): per_dataset[d]["formats"][f]["compressors"][c]["rt_compressor"]
        for d in ds_list for f in formats for c in compressors
    }
    total = len(rt_comp)
    ok = sum(1 for v in rt_comp.values() if v)
    out.append("## RT compressor (bytes)\n")
    out.append(
        f"`decompress(compress(bytes)) == bytes` — **{ok}/{total}** OK."
    )
    if ok < total:
        out.append("\n**Falhas**:")
        for (d, f, c), v in rt_comp.items():
            if not v:
                out.append(f"- `{d}` × `{f}` × `{c}` — FAIL")
    out.append("")

    # Full RT
    rt_full = {
        (d, f, c): per_dataset[d]["formats"][f]["compressors"][c]["rt_full"]
        for d in ds_list for f in formats for c in compressors
    }
    total = len(rt_full)
    ok = sum(1 for v in rt_full.values() if v)
    out.append("## RT full (cadeia inteira)\n")
    out.append(
        f"`parse(decompress(compress(serialize(linhas)))) == linhas` "
        f"— **{ok}/{total}** OK."
    )
    if ok < total:
        out.append("\n**Falhas**:")
        for (d, f, c), v in rt_full.items():
            if not v:
                out.append(f"- `{d}` × `{f}` × `{c}` — FAIL")
    out.append("")

    # Matriz de RT full por dataset × formato (todos compressores OK)
    out.append("## Matriz por dataset × formato (todos compressores)\n")
    out.append(
        "Cada celula = OK se TODAS as decompressoes "
        f"({len(compressors)} compressores) recuperam os dados originais."
    )
    out.append("")
    headers = ["dataset"] + formats
    rows = []
    for d in ds_list:
        cells = [d]
        for f in formats:
            all_ok = all(
                per_dataset[d]["formats"][f]["compressors"][c]["rt_full"]
                for c in compressors
            )
            cells.append("**OK**" if all_ok else "**FAIL**")
        rows.append(cells)
    out.append(make_table(headers, rows))

    path.write_text("\n".join(out), encoding="utf-8", newline="\n")


# ---- 05-campeao-por-dataset ----------------------------------------------

def write_campeao(
    path: Path,
    per_dataset: dict,
    ds_list: list[str],
    formats: list[str],
    compressors: list[str],
) -> None:
    out: list[str] = []
    out.append("# 05 — Campeao por dataset\n")
    out.append(
        "Para cada dataset, qual (formato, compressor) produz **menor** "
        "bytes. Inclui tambem ranking dos 3 menores por dataset.\n"
    )

    # Top-3 per dataset
    out.append("## Top-3 menor por dataset\n")
    headers = ["dataset", "raw csv", "1o (menor)", "2o", "3o", "reducao 1o"]
    rows = []
    champ_counts: dict[str, int] = {}
    for d in ds_list:
        raw_csv = per_dataset[d]["formats"]["csv"]["bytes"]
        combos = []
        for f in formats:
            for c in compressors:
                b = per_dataset[d]["formats"][f]["compressors"][c]["bytes"]
                combos.append((f, c, b))
        combos.sort(key=lambda x: x[2])
        top = combos[:3]
        champ = f"{top[0][0]}/{top[0][1]}"
        champ_counts[champ] = champ_counts.get(champ, 0) + 1
        cells = [
            d,
            str(raw_csv),
            f"**{top[0][0]}/{top[0][1]}** = {top[0][2]}",
            f"_{top[1][0]}/{top[1][1]}_ = {top[1][2]}",
            f"{top[2][0]}/{top[2][1]} = {top[2][2]}",
            f"{top[0][2]/raw_csv*100:.0f}%",
        ]
        rows.append(cells)
    out.append(make_table(headers, rows, [1, 5]))
    out.append("")

    # Champion frequency
    out.append("## Frequencia do campeao\n")
    out.append("Quantas vezes cada combinacao `(formato, compressor)` foi a melhor.\n")
    rows = []
    for combo, n in sorted(champ_counts.items(), key=lambda x: -x[1]):
        rows.append([f"`{combo}`", f"{n}/{len(ds_list)}"])
    out.append(make_table(["combinacao", "vitorias"], rows, [1]))
    out.append("")

    # Best possible totals
    total_raw = sum(per_dataset[d]["formats"]["csv"]["bytes"] for d in ds_list)
    total_best = sum(
        min(
            per_dataset[d]["formats"][f]["compressors"][c]["bytes"]
            for f in formats for c in compressors
        )
        for d in ds_list
    )
    out.append("## Soma global do menor por dataset\n")
    out.append(
        f"- **Raw CSV total**: {total_raw} bytes"
    )
    out.append(
        f"- **Soma do menor por dataset**: {total_best} bytes "
        f"({total_best/total_raw*100:.1f}% do raw CSV)."
    )
    out.append(
        f"- Limite inferior empirico **sobre o conjunto medido** — "
        f"compressores adicionais (snappy, lz4, parquet com diferentes "
        f"engines) podem mover esse limite."
    )

    path.write_text("\n".join(out), encoding="utf-8", newline="\n")
