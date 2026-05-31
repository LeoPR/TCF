"""HCC fork — RLE de near-identical lines (tentativa 02).

Subclass de M8AVirtualRefsSyntax. Sem mexer em OBAT nem em src/tcf.

Encode:
  1. Chama super().encode -> body canonical
  2. Post-process: detecta runs de linhas consecutivas com mesmo
     esqueleto onde so' escape-digits variam em sequencia aritmetica
  3. Compacta cada run em `*N+delta|<template>`

Decode:
  1. Pre-process tcf_text: expande cada `*N+delta|<template>` em N
     linhas (incrementando escape-digits em cada uma)
  2. Chama super().decode com texto expandido

Restricoes:
- Run minimo: 2 linhas
- Linhas devem diferir APENAS em chars de escape-digit
- Todas as posicoes de escape-digit devem diferir (caso contrario
  o shift incrementaria literais que nao deveriam mudar)
- Delta consistente entre todos os pares consecutivos

Limitacao conhecida: nao trata transicao de cardinalidade (e.g.,
\\9 -> \\10) porque mudaria o tamanho da linha — detector simplesmente
nao detecta esse caso como run.
"""

from __future__ import annotations

from tcf.composicional.syntax import M8AVirtualRefsSyntax


def find_escape_digit_positions(line: str) -> list[int]:
    """Posicoes (0-based) de cada char digit que vem apos `\\`.

    Em `5\\27*4`, posicoes [2, 3] (os dois digits do escape `\\27`).
    """
    positions = []
    i = 0
    n = len(line)
    while i < n:
        c = line[i]
        if c == '\\':
            i += 1
            while i < n and line[i].isdigit():
                positions.append(i)
                i += 1
        else:
            i += 1
    return positions


def find_escape_digit_runs(line: str) -> list[tuple[int, int]]:
    """Retorna runs (start, end_exclusive) de chars digit apos escape.

    Em `5\\27*4`, [(2, 4)] (uma run cobrindo posicoes 2 e 3).
    """
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
    """Retorna delta se as duas linhas formam par near-identical.

    Criterios (corrigidos 2026-05-17 apos sub-exp 04):
    - mesmo length
    - escape-digit runs em mesmas posicoes (runs_a == runs_b)
    - diffs APENAS dentro de escape-digit runs (sem alterar separadores/refs)
    - mesmo delta inteiro (b_run - a_run) em todas as runs (uma so'
      delta — se algumas runs nao mudam, sao delta=0 e tem que coexistir
      com possiveis runs mudando, mas todos devem dar mesmo delta —
      pratica: ou todas mudam o mesmo, ou nenhuma muda)

    Bug fixado: versao anterior exigia que TODAS as posicoes
    dentro de runs estivessem em diffs. Quebrava casos onde lit
    multi-digit muda so' um char (ex: "10" -> "11" diff posicao 3
    so', mas run inteira interpretada como int 10 -> 11).
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
        return None  # sem escape-digit nao da' pra shift safely
    # Todas as diffs dentro de alguma run?
    run_positions = set()
    for s, e in runs_a:
        run_positions.update(range(s, e))
    if any(d not in run_positions for d in diffs):
        return None
    # Delta consistente em todas as runs (incluindo 0)?
    deltas = []
    for start, end in runs_a:
        a_int = int(line_a[start:end])
        b_int = int(line_b[start:end])
        deltas.append(b_int - a_int)
    if len(set(deltas)) != 1:
        return None
    delta = deltas[0]
    if delta == 0:
        return None  # sem diff real — RLE puro ja' deveria pegar
    return delta


def shift_escape_digits(template: str, delta: int) -> str:
    """Aplica delta a cada run de escape-digit. Mantem largura
    se possivel; expande se delta cruzar cardinalidade."""
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
    """Detecta runs (start, end_exclusive, delta) de linhas
    consecutivas near-identical (>= 2 linhas, delta consistente).
    """
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
    """Aplica seq-RLE. Retorna (linhas_compactadas, info_runs)."""
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
                'start_line': start + 1,  # 1-based pra report
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
    """Se linha e' `*N+delta|<template>`, expande em N linhas.
    Retorna None se nao for marker seq."""
    if not linha.startswith("*"):
        return None
    bar = linha.find("|")
    if bar == -1:
        return None
    head = linha[1:bar]  # ex: "8+1" ou "5-2"
    # Procura sinal + ou - apos o primeiro digito (skipping leading digits)
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


class HCCForkSeqRLE(M8AVirtualRefsSyntax):
    """HCC fork: adiciona seq-RLE no body via post-process."""

    name = "M8-A-fork-seq-rle"

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
