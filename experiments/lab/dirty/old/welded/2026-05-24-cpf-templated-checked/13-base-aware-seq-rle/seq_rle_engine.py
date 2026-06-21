"""SeqRLEEngine — engine generica que opera em qualquer BaseAlphabet.

Separacao de responsabilidades:
- Engine NAO sabe se eh decimal/hex/etc — recebe BaseAlphabet como param
- Logica uniforme; comportamento varia APENAS via alphabet
- Estilo Strategy pattern (engine = strategy holder)

Funcoes operacionais:
- find_runs(line): runs de chars no alphabet (apos escape `\\`)
- compare(a, b): retorna delta se a/b sao near-identical (diferem so' em runs)
- shift(template, delta): template -> template+delta usando alphabet

Engine eh state-less e thread-safe.

Versao compat com M10 quando alphabet=DECIMAL:
- find_escape_digit_runs (M10) -> find_runs(line, DECIMAL)
- shift_escape_digits (M10)    -> shift(template, delta, DECIMAL)
"""

from __future__ import annotations

from base_alphabet import BaseAlphabet, DECIMAL, BASE_MARKER


class SeqRLEEngine:
    """Engine de seq-RLE generico parametrizado por BaseAlphabet."""

    def __init__(self, alphabet: BaseAlphabet):
        self.alphabet = alphabet
        self._char_set = set(alphabet.chars)

    def is_alphabet_char(self, c: str) -> bool:
        return c in self._char_set

    def find_runs(self, line: str) -> list[tuple[int, int]]:
        """Retorna runs (start, end) de chars do alphabet apos `\\`."""
        runs = []
        i = 0
        n = len(line)
        while i < n:
            if line[i] == '\\':
                i += 1
                if i < n and self.is_alphabet_char(line[i]):
                    start = i
                    while i < n and self.is_alphabet_char(line[i]):
                        i += 1
                    runs.append((start, i))
            else:
                i += 1
        return runs

    def parse(self, run_str: str) -> int:
        """Converte run string -> int na base do alphabet."""
        return int(run_str, self.alphabet.base)

    def format(self, value: int, width: int) -> str:
        """Converte int -> string na base do alphabet, padded a width.

        Usa chars do alphabet (case-correct, ex: hex_lower vs hex_upper).
        """
        if value < 0:
            raise ValueError(f"negative value not supported: {value}")
        # Build digits
        digits = []
        n = value
        if n == 0:
            digits.append(self.alphabet.chars[0])
        else:
            while n > 0:
                digits.append(self.alphabet.chars[n % self.alphabet.base])
                n //= self.alphabet.base
        s = ''.join(reversed(digits))
        return s.rjust(width, self.alphabet.chars[0])

    def compare_for_seq(self, line_a: str, line_b: str) -> int | None:
        """Retorna delta se par (a,b) eh near-identical compactavel.

        Same as M10 compare_for_seq mas com alphabet generico.
        """
        if len(line_a) != len(line_b):
            return None
        diffs = [k for k in range(len(line_a)) if line_a[k] != line_b[k]]
        if not diffs:
            return None
        runs_a = self.find_runs(line_a)
        runs_b = self.find_runs(line_b)
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
                a_int = self.parse(line_a[start:end])
                b_int = self.parse(line_b[start:end])
            except ValueError:
                return None
            deltas.append(b_int - a_int)
        if len(set(deltas)) != 1:
            return None
        delta = deltas[0]
        if delta == 0:
            return None
        return delta

    def shift(self, template: str, delta: int) -> str:
        """Shifta template por delta usando alphabet (preserve width)."""
        runs = self.find_runs(template)
        if not runs:
            return template
        out = []
        cursor = 0
        for start, end in runs:
            out.append(template[cursor:start])
            old_val = self.parse(template[start:end])
            new_val = old_val + delta
            width = end - start
            out.append(self.format(new_val, width))
            cursor = end
        out.append(template[cursor:])
        return ''.join(out)


class MultiBaseSeqRLE:
    """Detector que tenta multiplos engines, escolhe melhor por par.

    Estrategia: pra cada par consecutivo de linhas, tenta cada engine
    na ordem fornecida. Primeiro que retorna delta valido (nao None)
    eh usado. Marker resultante inclui base annotation se nao-default.

    Ordem default: [DECIMAL] -> tenta so' decimal (compat M10).
    Ordem extendida: [DECIMAL, HEX_LOWER] -> tenta decimal primeiro,
        fallback hex.
    """

    def __init__(self, alphabets: list[BaseAlphabet] | None = None):
        self.alphabets = alphabets or [DECIMAL]
        self.engines = {a: SeqRLEEngine(a) for a in self.alphabets}

    def detect_seq_runs(self, body_lines: list[str]) -> list[tuple[int, int, int, BaseAlphabet]]:
        """Retorna runs (start, end, delta, alphabet) consecutivos.

        Diferenca vs M10: cada run carrega tambem o alphabet usado.
        """
        runs = []
        n = len(body_lines)
        i = 0
        while i < n - 1:
            delta_alpha = self._compare_any(body_lines[i], body_lines[i + 1])
            if delta_alpha is None:
                i += 1
                continue
            delta, alphabet = delta_alpha
            run_end = i + 2
            while run_end < n:
                next_da = self._compare_any(body_lines[run_end - 1], body_lines[run_end])
                if next_da is None:
                    break
                next_delta, next_alpha = next_da
                # Run continua so' se mesmo delta E mesmo alphabet
                if next_delta != delta or next_alpha != alphabet:
                    break
                run_end += 1
            runs.append((i, run_end, delta, alphabet))
            i = run_end
        return runs

    def _compare_any(self, a: str, b: str) -> tuple[int, BaseAlphabet] | None:
        """Tenta cada engine; retorna (delta, alphabet) do primeiro que casa."""
        for alphabet in self.alphabets:
            engine = self.engines[alphabet]
            delta = engine.compare_for_seq(a, b)
            if delta is not None:
                return delta, alphabet
        return None

    def compact_body(self, body_lines: list[str]) -> tuple[list[str], list[dict]]:
        """Compacta body usando runs detectados.

        Markers:
        - DECIMAL: `*N+delta|template` (compat M10)
        - Outras: `*N+delta@<marker>|template` (ex: `*N+delta@h|template`)
        """
        runs = self.detect_seq_runs(body_lines)
        if not runs:
            return body_lines, []
        out = []
        info = []
        i = 0
        run_idx = 0
        while i < len(body_lines):
            if run_idx < len(runs) and runs[run_idx][0] == i:
                start, end, delta, alphabet = runs[run_idx]
                count = end - start
                sign = '+' if delta >= 0 else ''
                base_mark = BASE_MARKER[alphabet]
                base_suffix = f"@{base_mark}" if base_mark else ""
                marker = f"*{count}{sign}{delta}{base_suffix}|{body_lines[start]}"
                out.append(marker)
                info.append({
                    'start_line': start + 1,
                    'end_line': end,
                    'count': count,
                    'delta': delta,
                    'alphabet': alphabet.name,
                    'template': body_lines[start],
                })
                i = end
                run_idx += 1
            else:
                out.append(body_lines[i])
                i += 1
        return out, info

    def expand_marker(self, linha: str) -> list[str] | None:
        """Expande marker `*N+delta(@base)?|<template>` em N linhas."""
        if not linha.startswith("*"):
            return None
        bar = linha.find("|")
        if bar == -1:
            return None
        head = linha[1:bar]

        # Detect base annotation (`@<mark>`)
        alphabet = DECIMAL
        at_pos = head.find("@")
        if at_pos != -1:
            base_mark = head[at_pos + 1:]
            head = head[:at_pos]
            # Find alphabet by marker
            alphabet = None
            for a, m in BASE_MARKER.items():
                if m == base_mark:
                    alphabet = a
                    break
            if alphabet is None:
                return None  # marker desconhecido

        # Parse count + delta
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
        engine = self.engines.get(alphabet)
        if engine is None:
            engine = SeqRLEEngine(alphabet)  # fallback se alphabet nao registrada
        out = [template]
        curr = template
        for _ in range(1, count):
            curr = engine.shift(curr, delta)
            out.append(curr)
        return out
