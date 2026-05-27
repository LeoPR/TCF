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


def compare_for_seq(line_a: str, line_b: str) -> list[int] | None:
    """Retorna lista de deltas se par e' near-identical compactavel.

    ADR-0016 (Fase 1 sub-exp 14 Bug #2): retorna LISTA de deltas
    (1 por run de escape-digit). Permite multi-run com deltas mistos
    [0, 0, 0, 1] (3 runs invariantes + 1 incrementing) — caso comum
    em strings com prefix invariante + suffix cadenced (ex: IPs sem
    atom HCC).

    Aceita:
    - Single non-zero (todos runs com mesmo delta): [1, 1, 1] OR [5]
    - Mixed zero+nonzero (1 non-zero, resto zero): [0, 0, 0, 1]

    Rejeita:
    - Multiple non-zero diferentes: [1, 2] OR [3, 5]
    - All zero (lines identical): [0, 0, 0, 0]
    - Estruturas runs_a != runs_b
    """
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
        try:
            a_int = int(line_a[start:end])
            b_int = int(line_b[start:end])
        except ValueError:
            return None
        deltas.append(b_int - a_int)
    non_zero = [d for d in deltas if d != 0]
    if not non_zero:
        return None  # all zero (identical)
    if len(set(non_zero)) > 1:
        return None  # multiple different non-zero (Fase 2 reject)
    return deltas


def shift_escape_digits(template: str, delta) -> str:
    """Shifta runs de escape-digit por delta.

    `delta` aceita:
    - int (M10 compat): mesmo delta em TODOS runs
    - list[int] (ADR-0016): per-run delta
    """
    runs = find_escape_digit_runs(template)
    if not runs:
        return template

    # Normalize delta para list
    if isinstance(delta, int):
        deltas = [delta] * len(runs)
    else:
        deltas = list(delta)
        if len(deltas) != len(runs):
            return template  # mismatch, no-op safe fallback

    out = []
    cursor = 0
    for (start, end), d in zip(runs, deltas):
        out.append(template[cursor:start])
        old_val = int(template[start:end])
        new_val = old_val + d
        width = end - start
        new_str = str(new_val)
        if len(new_str) < width:
            new_str = new_str.zfill(width)
        out.append(new_str)
        cursor = end
    out.append(template[cursor:])
    return ''.join(out)


def detect_seq_runs(body_lines: list[str]) -> list[tuple[int, int, list[int]]]:
    """Retorna runs (start, end_exclusive, deltas) consecutivos near-identical.

    ADR-0016: deltas eh list[int] (per-run). Compat M10: quando todos
    deltas iguais e nao-zero, marker emit usa formato `*N+delta|` (single).
    """
    runs = []
    n = len(body_lines)
    i = 0
    while i < n - 1:
        deltas = compare_for_seq(body_lines[i], body_lines[i + 1])
        if deltas is None:
            i += 1
            continue
        run_end = i + 2
        while run_end < n:
            next_deltas = compare_for_seq(body_lines[run_end - 1],
                                           body_lines[run_end])
            if next_deltas != deltas:
                break
            run_end += 1
        runs.append((i, run_end, deltas))
        i = run_end
    return runs


def _is_uniform_delta(deltas: list[int]) -> int | None:
    """Se todos deltas sao iguais e nao-zero, retorna esse int. Senao None.

    Permite emit marker M10 compat `*N+delta|` em caso uniforme.
    """
    if all(d == deltas[0] and d != 0 for d in deltas):
        return deltas[0]
    return None


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
            start, end, deltas = runs[run_idx]
            count = end - start
            # M10 compat: se uniforme, emit `*N+delta|` single
            uniform = _is_uniform_delta(deltas)
            if uniform is not None:
                sign = '+' if uniform >= 0 else ''
                marker = f"*{count}{sign}{uniform}|{body_lines[start]}"
            else:
                # ADR-0016 multi-delta: `*N+d1,d2,...|template`
                # Primeiro delta: sinal explicit (parser usa '+' ou '-' como
                # separador count/deltas). Quando negativo, str() ja' inclui '-';
                # quando >= 0, prependa '+'.
                deltas_str = ','.join(str(d) for d in deltas)
                sign_prefix = '+' if deltas[0] >= 0 else ''
                marker = f"*{count}{sign_prefix}{deltas_str}|{body_lines[start]}"
            out.append(marker)
            info.append({
                'start_line': start + 1,
                'end_line': end,
                'count': count,
                'deltas': list(deltas),
                'uniform_delta': uniform,
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
    """Expande `*N+delta|template` (M10 compat) ou `*N+d1,d2,...|template` (ADR-0016).

    Distingue formato pela presenca de `,` no portion de delta.
    """
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
    except ValueError:
        return None
    delta_str = head[plus_pos:]

    # ADR-0016: multi-delta format `+d1,d2,d3,d4`
    if ',' in delta_str:
        try:
            deltas = [int(d) for d in delta_str.split(',')]
        except ValueError:
            return None
        delta_arg = deltas
    else:
        # M10 compat: single int
        try:
            delta_arg = int(delta_str)
        except ValueError:
            return None

    template = linha[bar + 1:]
    out = [template]
    curr = template
    for _ in range(1, count):
        curr = shift_escape_digits(curr, delta_arg)
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
