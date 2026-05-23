"""HCC com seq-RLE de linhas near-identical (canonical).

Welded canonical 2026-05-22 (T-CODE-PACOTE1-WELD-CANONICAL).
Origem: `experiments/lab/clean/EXP-010-tcf-delta-aware-prototype/hcc_seqrle.py`
(welded 2026-05-17 do dirty lab `02-hcc-sozinho-rle-near-identical/hcc_fork.py`
post bug-fix do detector descoberto em sub-exp 04).

Subclass de M8AVirtualRefsSyntax. Post-process body canonical pra
detectar runs near-identical e compactar em `*N+delta|<template>`.

Detector valido:
- mesmo length
- escape-digit runs em mesmas posicoes (runs_a == runs_b)
- diffs APENAS dentro de escape-digit runs
- delta integer consistente entre runs (a -> b)

Decoder espelho: expande `*N+delta|<template>` em N linhas via
shift_escape_digits.

Sintaxe: `*N+delta|<template>` (compativel com `*N|` RLE puro
existente em M8A — distincao pelo `+`).

`src/tcf/composicional/syntax.py` intocado — importa e estende.
"""

from __future__ import annotations

from tcf.composicional.syntax import M8AVirtualRefsSyntax


def find_escape_digit_positions(line: str) -> list[int]:
    """Posicoes (0-based) de cada char digit que vem apos `\\`."""
    positions = []
    i = 0
    n = len(line)
    while i < n:
        if line[i] == '\\':
            i += 1
            while i < n and line[i].isdigit():
                positions.append(i)
                i += 1
        else:
            i += 1
    return positions


def find_escape_digit_runs(line: str) -> list[tuple[int, int]]:
    """Retorna runs (start, end_exclusive) de chars digit apos escape."""
    runs = []
    i = 0
    n = len(line)
    while i < n:
        if line[i] == '\\':
            i += 1
            if i < n and line[i].isdigit():
                start = i
                while i < n and line[i].isdigit():
                    i += 1
                runs.append((start, i))
        else:
            i += 1
    return runs


def compare_for_seq(line_a: str, line_b: str) -> int | None:
    """Retorna delta se par e' near-identical compactavel."""
    if len(line_a) != len(line_b):
        return None
    diffs = [k for k in range(len(line_a)) if line_a[k] != line_b[k]]
    if not diffs:
        return None
    runs_a = find_escape_digit_runs(line_a)
    runs_b = find_escape_digit_runs(line_b)
    if runs_a != runs_b:
        return None
    if not runs_a:
        return None
    run_positions = set()
    for s, e in runs_a:
        run_positions.update(range(s, e))
    if any(d not in run_positions for d in diffs):
        return None
    deltas = []
    for start, end in runs_a:
        a_int = int(line_a[start:end])
        b_int = int(line_b[start:end])
        deltas.append(b_int - a_int)
    if len(set(deltas)) != 1:
        return None
    delta = deltas[0]
    if delta == 0:
        return None
    return delta


def shift_escape_digits(template: str, delta: int) -> str:
    """Shifta cada run de escape-digit por delta (preserva width quando possivel)."""
    runs = find_escape_digit_runs(template)
    if not runs:
        return template
    out = []
    cursor = 0
    for start, end in runs:
        out.append(template[cursor:start])
        old_val = int(template[start:end])
        new_val = old_val + delta
        width = end - start
        new_str = str(new_val)
        if len(new_str) < width:
            new_str = new_str.zfill(width)
        out.append(new_str)
        cursor = end
    out.append(template[cursor:])
    return ''.join(out)


def detect_seq_runs(body_lines: list[str]) -> list[tuple[int, int, int]]:
    """Retorna runs (start, end_exclusive, delta) consecutivos near-identical."""
    runs = []
    n = len(body_lines)
    i = 0
    while i < n - 1:
        delta = compare_for_seq(body_lines[i], body_lines[i + 1])
        if delta is None:
            i += 1
            continue
        run_end = i + 2
        while run_end < n:
            next_delta = compare_for_seq(body_lines[run_end - 1],
                                          body_lines[run_end])
            if next_delta != delta:
                break
            run_end += 1
        runs.append((i, run_end, delta))
        i = run_end
    return runs


def compact_body(body_lines: list[str]) -> tuple[list[str], list[dict]]:
    runs = detect_seq_runs(body_lines)
    if not runs:
        return body_lines, []
    out = []
    info = []
    i = 0
    run_idx = 0
    while i < len(body_lines):
        if run_idx < len(runs) and runs[run_idx][0] == i:
            start, end, delta = runs[run_idx]
            count = end - start
            sign = '+' if delta >= 0 else ''
            marker = f"*{count}{sign}{delta}|{body_lines[start]}"
            out.append(marker)
            info.append({
                'start_line': start + 1,
                'end_line': end,
                'count': count,
                'delta': delta,
                'template': body_lines[start],
                'savings': sum(len(body_lines[k]) + 1
                               for k in range(start, end)) - (len(marker) + 1),
            })
            i = end
            run_idx += 1
        else:
            out.append(body_lines[i])
            i += 1
    return out, info


def expand_seq_marker(linha: str) -> list[str] | None:
    """Se linha e' `*N+delta|<template>`, expande em N linhas."""
    if not linha.startswith("*"):
        return None
    bar = linha.find("|")
    if bar == -1:
        return None
    head = linha[1:bar]
    plus_pos = -1
    for k in range(len(head)):
        if head[k] in ('+', '-') and k > 0:
            plus_pos = k
            break
    if plus_pos == -1:
        return None
    try:
        count = int(head[:plus_pos])
        delta = int(head[plus_pos:])
    except ValueError:
        return None
    template = linha[bar + 1:]
    out = [template]
    curr = template
    for _ in range(1, count):
        curr = shift_escape_digits(curr, delta)
        out.append(curr)
    return out


class HCCSeqRLE(M8AVirtualRefsSyntax):
    """HCC com seq-RLE near-identical via post-process.

    Encode: super().encode → detect runs → compact em `*N+delta|template`
    Decode: expand `*N+delta|` → super().decode
    """

    name = "M8-A-seq-rle"

    def __init__(self):
        super().__init__()
        self._seq_info: list[dict] = []

    def get_seq_info(self) -> list[dict]:
        return self._seq_info

    def encode(self, linhas, unicas, tokens_por_string, header):
        body_text = super().encode(linhas, unicas, tokens_por_string, header)
        body_lines = body_text.rstrip('\n').split('\n')
        compacted, info = compact_body(body_lines)
        self._seq_info = info
        return '\n'.join(compacted) + '\n'

    def decode(self, tcf_text):
        expanded_lines = []
        for raw in tcf_text.splitlines():
            linha = raw.strip()
            if not linha:
                expanded_lines.append(raw)
                continue
            expanded = expand_seq_marker(linha)
            if expanded is not None:
                expanded_lines.extend(expanded)
            else:
                expanded_lines.append(raw)
        expanded_text = '\n'.join(expanded_lines) + '\n'
        return super().decode(expanded_text)
