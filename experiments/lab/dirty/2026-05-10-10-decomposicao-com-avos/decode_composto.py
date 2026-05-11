"""Decoder do formato composto.

Gramatica:
  linha       := decl_externa | ref
  decl_externa := "no" INT ":" count_opc forma
  ref         := count_opc "ref:no" INT
  count_opc   := INT "x " | ε

  forma       := folha | composto
  folha       := 'folha "' STR '"'
  composto    := parte (' + ' parte)*
  parte       := 'pref:' pref_ref | 'suf:' suf_ref | '"' STR '"'

  pref_ref    := 'no' INT | '(no' INT '=decl folha "' STR '")'
  suf_ref     := 'no' INT | '(no' INT '=decl folha "' STR '")'
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

    def try_consume_count(self) -> int:
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


def _parse_pref_ou_suf_ref(p: Parser, nos: dict, tipo: str) -> int:
    if p.peek(1) == "(":
        p.consume("(")
        p.consume("no")
        eid = p.consume_int()
        p.consume("=decl folha ")
        text = p.consume_string()
        p.consume(")")
        nos[eid] = (tipo, text)
        return eid
    else:
        p.consume("no")
        eid = p.consume_int()
        return eid


def _parse_decl_externa(p: Parser, eid: int, nos: dict) -> None:
    if p.peek(6) == "folha ":
        p.consume("folha ")
        text = p.consume_string()
        nos[eid] = ("folha", text)
        return

    partes: list[tuple[str, object]] = []
    while True:
        if p.peek(5) == "pref:":
            p.consume("pref:")
            pref_eid = _parse_pref_ou_suf_ref(p, nos, "pref")
            partes.append(("pref", pref_eid))
        elif p.peek(4) == "suf:":
            p.consume("suf:")
            suf_eid = _parse_pref_ou_suf_ref(p, nos, "suf")
            partes.append(("suf", suf_eid))
        elif p.peek(1) == '"':
            text = p.consume_string()
            partes.append(("mid", text))
        else:
            break
        if p.peek(3) == " + ":
            p.consume(" + ")
        else:
            break
    nos[eid] = ("composto", partes)


def decode_composto(tcf_text: str) -> list[str]:
    nos: dict[int, tuple] = {}
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
            count = p.try_consume_count()
            _parse_decl_externa(p, eid, nos)
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
            raise ValueError(f"trailing chars em {linha!r} pos {p.pos}")

    cache: dict[int, str] = {}

    def texto(eid: int) -> str:
        if eid in cache:
            return cache[eid]
        info = nos[eid]
        tag = info[0]
        if tag in ("folha", "pref", "suf"):
            t = info[1]
        elif tag == "composto":
            partes = info[1]
            parts: list[str] = []
            for parte_tag, val in partes:
                if parte_tag == "mid":
                    parts.append(val)
                elif parte_tag in ("pref", "suf"):
                    parts.append(texto(val))
            t = "".join(parts)
        else:
            raise ValueError(f"tag desconhecida: {tag}")
        cache[eid] = t
        return t

    saida: list[str] = []
    for eid, count in body_seq:
        s = texto(eid)
        for _ in range(count):
            saida.append(s)
    return saida
