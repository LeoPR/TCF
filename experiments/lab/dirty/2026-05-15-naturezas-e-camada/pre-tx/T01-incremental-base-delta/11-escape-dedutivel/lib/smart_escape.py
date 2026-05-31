r"""smart_escape.py — TCF v2 (escape dedutivel).

Principio: na materializacao do .tcf, digit-run `\N` so' precisa
do escape se `N <= current_node_count` (ambiguidade com ref `^N`).
Onde `N > count`, ref `^N` e' invalido (nao existe), entao digit-run
e' literal-sem-ambiguidade — escape redundante.

Implementacao limitada a T01 (cada body line tem 0 ou 1 lit piece).
Para compositions complexas (multi-lit, refs intra-body), parser
completo seria necessario — fora do escopo desta iteracao.

Funcoes:
- smart_encode(v1_text) -> v2_text: remove escapes desnecessarios
- smart_decode(v2_text) -> list[str]: decodifica v2 direto (sem
  passar pelo canonical decoder)
"""

from __future__ import annotations

import re


def smart_encode(v1_text: str) -> str:
    """Remove escapes desnecessarios de TCF v1 canonical -> v2 smart.

    Cada linha:
    - `*N|<body>`: RLE wrapper; processa body
    - `^N`: ref pura, sem mudancas
    - `<body>`: composicao com lit (T01: 1 lit por linha)

    Pra cada `\\digits` em lit context: se digit_value > count_before_line,
    remove o `\\`.
    """
    out_lines = []
    count = 0

    for line in v1_text.splitlines():
        body = line
        prefix = ""
        if body.startswith("*") and "|" in body:
            bar = body.find("|")
            prefix = body[:bar + 1]
            body = body[bar + 1:]

        if body.startswith("^"):
            # Pure ref; sem alteracao
            out_lines.append(line)
            continue

        # Body e' lit (T01 assumption: 1 lit per body line)
        # Pra cada \digits: remove \ se valor estah fora do range valido de ref [1, count]
        # - valor 0: ref ^0 e' invalido (refs comecam em 1) -> literal
        # - valor > count: ref correspondente nao existe -> literal
        new_body = re.sub(
            r'\\(\d+)',
            lambda m: (
                m.group(1) if (
                    int(m.group(1)) == 0 or int(m.group(1)) > count
                ) else '\\' + m.group(1)
            ),
            body,
        )
        out_lines.append(prefix + new_body)
        count += 1  # this line declares 1 node

    return '\n'.join(out_lines) + '\n'


def smart_decode(v2_text: str) -> list[str]:
    """Decode TCF v2 (smart escape) direto pra lista de strings.

    Pra T01 (lit-only body), o parse e' simples:
    - `*N|<body>`: emite N copias do <body> parseado
    - `^N`: emite copia do node N
    - `<body>`: parse como lit (handle escape pairs `\\X` -> `X`)
    """
    nos_decl: list[str] = []
    saida: list[str] = []

    for raw in v2_text.splitlines():
        line = raw.strip()
        if not line:
            continue

        # RLE wrapper
        count = 1
        if line.startswith("*") and "|" in line:
            bar = line.find("|")
            count = int(line[1:bar])
            line = line[bar + 1:]

        # Ref shortcut
        if line.startswith("^"):
            s_no = nos_decl[int(line[1:]) - 1]
        else:
            # Lit body — parse char by char, handling escape pairs
            s_no = _parse_lit_body(line)
            nos_decl.append(s_no)

        saida.extend([s_no] * count)

    return saida


def _parse_lit_body(body: str) -> str:
    """Parse lit body: escape pairs `\\X` -> `X`; bare chars literais."""
    out = []
    i = 0
    n = len(body)
    while i < n:
        c = body[i]
        if c == '\\' and i + 1 < n:
            out.append(body[i + 1])
            i += 2
        else:
            out.append(c)
            i += 1
    return ''.join(out)


def count_escapes(text: str) -> int:
    """Conta numero de `\\digits` no texto (uteis pra metrica)."""
    return len(re.findall(r'\\\d+', text))
