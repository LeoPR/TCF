"""Decoder do formato aninhado.

Parser recursivo manual (regex nao serve por causa do aninhamento
de decls em decls).

Gramatica:
  linha    := decl_externa | ref_count1 | ref_countN
  decl_externa := "no" eid ":" SP forma
  ref_count1 := "ref:no" eid
  ref_countN := count "x" SP "ref:no" eid

  forma := folha | filho
  folha := 'folha "' string '"'
         | count "x" SP 'folha "' string '"'
  filho := 'filho_de(' pai_descritor ')' ' + "' string '"'
         | count "x" SP 'filho_de(' pai_descritor ')' ' + "' string '"'

  pai_descritor := "no" eid                       # ref a pai ja declarado
                 | "no" eid "=decl" SP forma_dentro  # decl aninhada

  forma_dentro := 'folha "' string '"'
                | 'filho_de(' pai_descritor ')' ' + "' string '"'
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
        """Se proximo for '<int>x ', consome e retorna. Senao retorna 1."""
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


def _parse_forma_dentro(p: Parser, nos: dict, eid_atual: int) -> None:
    """Parseia forma sem prefixo de count (dentro de decl aninhada).
    Registra nos[eid_atual] = (pai_eid_ou_None, frag).
    """
    if p.peek(6) == "folha ":
        p.consume("folha ")
        frag = p.consume_string()
        nos[eid_atual] = (None, frag)
    elif p.peek(9) == "filho_de(":
        p.consume("filho_de(")
        p.consume("no")
        eid_pai = p.consume_int()
        if p.peek(1) == "=":
            p.consume("=decl ")
            _parse_forma_dentro(p, nos, eid_pai)
        p.consume(")")
        p.consume(' + ')
        frag = p.consume_string()
        nos[eid_atual] = (eid_pai, frag)
    else:
        raise ValueError(f"forma desconhecida em pos {p.pos}: "
                         f"{p.text[p.pos:p.pos + 40]!r}")


def decode_aninhado(tcf_text: str) -> list[str]:
    nos: dict[int, tuple[int | None, str]] = {}
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
            # decl externa
            p.consume("no")
            eid = p.consume_int()
            p.consume(": ")
            count = p.try_consume_count()
            _parse_forma_dentro(p, nos, eid)
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
            raise ValueError(
                f"trailing chars em linha {linha!r}, pos {p.pos}"
            )

    cache: dict[int, str] = {}

    def texto(eid: int) -> str:
        if eid in cache:
            return cache[eid]
        if eid not in nos:
            raise ValueError(f"no{eid} nao declarado")
        pai_eid, frag = nos[eid]
        t = frag if pai_eid is None else texto(pai_eid) + frag
        cache[eid] = t
        return t

    saida: list[str] = []
    for eid, count in body_seq:
        s = texto(eid)
        for _ in range(count):
            saida.append(s)
    return saida
