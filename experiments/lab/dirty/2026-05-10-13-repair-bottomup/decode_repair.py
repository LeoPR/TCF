"""Decoder do formato Re-Pair (exp 13).

Parser recursivo manual.

Gramatica:
  linha       := decl_str | ref
  decl_str    := "no" INT ":" count_opc forma
  ref         := count_opc "ref:no" INT
  count_opc   := INT "x " | epsilon
  forma       := token (' + ' token)*
  token       := '"' STR '"' | "no" INT | '(no' INT '="' STR '")'
"""


class Parser:
    def __init__(self, text: str):
        self.text = text
        self.pos = 0

    def peek(self, n: int = 1) -> str:
        return self.text[self.pos:self.pos + n]

    def consume(self, s: str) -> None:
        if not self.text.startswith(s, self.pos):
            raise ValueError(
                f"esperava {s!r} em pos {self.pos}: "
                f"{self.text[self.pos:self.pos + 40]!r}"
            )
        self.pos += len(s)

    def consume_int(self) -> int:
        start = self.pos
        while self.pos < len(self.text) and self.text[self.pos].isdigit():
            self.pos += 1
        if self.pos == start:
            raise ValueError(f"esperava digito em pos {self.pos}")
        return int(self.text[start:self.pos])

    def consume_string(self) -> str:
        self.consume('"')
        end = self.text.index('"', self.pos)
        s = self.text[self.pos:end]
        self.pos = end + 1
        return s

    def try_count(self) -> int:
        if self.pos >= len(self.text) or not self.text[self.pos].isdigit():
            return 1
        start = self.pos
        while self.pos < len(self.text) and self.text[self.pos].isdigit():
            self.pos += 1
        if self.text[self.pos:self.pos + 2] == "x ":
            n = int(self.text[start:self.pos])
            self.pos += 2
            return n
        self.pos = start
        return 1

    def at_end(self) -> bool:
        return self.pos >= len(self.text)


def _parse_token(p: Parser, simbolos: dict[int, str]) -> tuple[str, object]:
    """Retorna ('literal', text) ou ('ref', eid)."""
    if p.peek(1) == '"':
        text = p.consume_string()
        return ('literal', text)
    if p.peek(1) == '(':
        p.consume('(')
        p.consume('no')
        eid = p.consume_int()
        p.consume('="')
        # consume_string ja consumiu o ", precisamos ler ate "
        end = p.text.index('"', p.pos)
        text = p.text[p.pos:end]
        p.pos = end + 1
        p.consume(')')
        simbolos[eid] = text
        return ('ref', eid)
    if p.peek(2) == 'no':
        p.consume('no')
        eid = p.consume_int()
        return ('ref', eid)
    raise ValueError(f"token desconhecido em pos {p.pos}: "
                     f"{p.text[p.pos:p.pos + 30]!r}")


def _parse_forma(p: Parser, simbolos: dict[int, str]
                  ) -> list[tuple[str, object]]:
    partes: list[tuple[str, object]] = []
    while True:
        partes.append(_parse_token(p, simbolos))
        if p.peek(3) == ' + ':
            p.consume(' + ')
        else:
            break
    return partes


def decode_repair(tcf_text: str) -> list[str]:
    simbolos: dict[int, str] = {}
    decls_str: dict[int, list[tuple[str, object]]] = {}
    body_seq: list[tuple[int, int]] = []
    estado = "init"

    for raw in tcf_text.splitlines():
        linha = raw.strip()
        if not linha:
            continue
        if linha == "<body>":
            estado = "body"
            continue
        if linha == "</body>":
            estado = "end"
            continue
        if estado != "body":
            continue

        p = Parser(linha)
        if linha.startswith("no"):
            p.consume("no")
            eid = p.consume_int()
            p.consume(": ")
            count = p.try_count()
            partes = _parse_forma(p, simbolos)
            decls_str[eid] = partes
            body_seq.append((eid, count))
        elif linha.startswith("ref:"):
            p.consume("ref:no")
            eid = p.consume_int()
            body_seq.append((eid, 1))
        else:
            count = p.consume_int()
            p.consume("x ref:no")
            eid = p.consume_int()
            body_seq.append((eid, count))
        if not p.at_end():
            raise ValueError(f"trailing em {linha!r} pos {p.pos}")

    # Reconstroi
    cache: dict[int, str] = {}

    def texto_decl(eid: int) -> str:
        if eid in cache:
            return cache[eid]
        partes = decls_str[eid]
        s = "".join(
            v if k == 'literal' else simbolos[v]
            for k, v in partes
        )
        cache[eid] = s
        return s

    saida: list[str] = []
    for eid, count in body_seq:
        s = texto_decl(eid)
        for _ in range(count):
            saida.append(s)
    return saida
