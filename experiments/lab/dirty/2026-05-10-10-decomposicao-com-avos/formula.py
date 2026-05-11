"""Decomposicao em camadas (mesma convencao do exp 04, adaptada para a
sintaxe aninhada + marcador <dir:NAME>).

  macro = linhas estruturais (<body>, </body>, <dir:NAME>)
  dados = caracteres dentro de aspas duplas
  ref   = todo o resto (incluindo as aspas, sintaxe, ids, counts,
          indentacao, newlines de linhas nao-macro)
"""


def decompor(tcf_text: str) -> tuple[int, int, int]:
    chars_macro = 0
    chars_dados = 0
    chars_ref = 0

    for raw in tcf_text.splitlines(keepends=True):
        stripped = raw.strip()
        eh_macro = (
            stripped in ("<body>", "</body>")
            or (stripped.startswith("<dir:") and stripped.endswith(">"))
        )
        if eh_macro:
            chars_macro += len(raw)
            continue

        in_quotes = False
        for ch in raw:
            if ch == '"':
                chars_ref += 1
                in_quotes = not in_quotes
            elif in_quotes:
                chars_dados += 1
            else:
                chars_ref += 1

    return chars_macro, chars_ref, chars_dados
