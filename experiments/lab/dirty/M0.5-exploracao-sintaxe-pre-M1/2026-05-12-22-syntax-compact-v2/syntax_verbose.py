"""Sintaxe verbosa do exp 16, portada para o contrato `Syntax`.

Gramatica (didatica):

    <body>
      no1: "literal_da_primeira_string"
      no2: no1[0:K] + "lit_no_meio" + no1[-K:]
      no5: no4[0:K] + no2[-K:]
      ref:no1
      3x ref:no2
      no7: 5x no1[0:K] + "X"
    </body>

Marcadores explicitos:

| Marcador | Funcao |
|---|---|
| `noN`             | id do no pela ordem de aparicao |
| `noN[0:K]`        | prefixo de K chars de noN |
| `noN[-K:]`        | sufixo de K chars de noN |
| `"X"`             | literal entre aspas duplas |
| `+`               | concatenacao entre tokens (com espacos) |
| `:`               | separa decl-head da forma |
| `ref:noN`         | referencia a no declarado anteriormente |
| `Nx`              | RLE adjacente (linha repete N vezes) |
| `<body>` `</body>`| delimitadores macro |

Esta implementacao reproduz exatamente o output do exp 16 — TCFs
sao byte-identicos.
"""

import re
from online import Token, TokLit, TokRefPref, TokRefSuf
from syntax_base import Syntax


class VerboseSyntax(Syntax):

    name = "verbose"

    _RE_REF_PREF = re.compile(r'^no(\d+)\[0:(\d+)\]$')
    _RE_REF_SUF = re.compile(r'^no(\d+)\[-(\d+):\]$')
    _RE_LIT = re.compile(r'^"(.*)"$')
    _RE_DECL = re.compile(r'^no(\d+): (?:(\d+)x )?(.*)$')
    _RE_REF = re.compile(r'^(?:(\d+)x )?ref:no(\d+)$')

    # ---- encode ----

    def _render_token(self, tok: Token) -> str:
        if isinstance(tok, TokLit):
            return f'"{tok.text}"'
        if isinstance(tok, TokRefPref):
            return f'no{tok.string_id}[0:{tok.length}]'
        return f'no{tok.string_id}[-{tok.length}:]'  # TokRefSuf

    def _rle_adjacente(self, linhas: list[str]) -> list[tuple[str, int]]:
        out: list[tuple[str, int]] = []
        for s in linhas:
            if out and out[-1][0] == s:
                out[-1] = (s, out[-1][1] + 1)
            else:
                out.append((s, 1))
        return out

    def encode(self,
                linhas_originais: list[str],
                strings_unicas: list[str],
                tokens_por_string: list[list[Token]],
                header: str) -> str:
        str_to_tokens = dict(zip(strings_unicas, tokens_por_string))
        str_to_eid: dict[str, int] = {}
        decl_emitida: set[int] = set()
        proximo_eid = 1

        out: list[str] = ["<body>"]
        for s, count in self._rle_adjacente(linhas_originais):
            if s not in str_to_eid:
                str_to_eid[s] = proximo_eid
                proximo_eid += 1
            eid = str_to_eid[s]
            prefixo = f"{count}x " if count > 1 else ""

            if eid not in decl_emitida:
                forma = " + ".join(self._render_token(t)
                                    for t in str_to_tokens[s])
                out.append(f"  no{eid}: {prefixo}{forma}")
                decl_emitida.add(eid)
            else:
                out.append(f"  {prefixo}ref:no{eid}")

        out.append("</body>")
        return "\n".join(out) + "\n"

    # ---- decode ----

    def _parse_token(self, tok_str: str, strings: dict[int, str]) -> str:
        m = self._RE_LIT.match(tok_str)
        if m:
            return m.group(1)
        m = self._RE_REF_PREF.match(tok_str)
        if m:
            sid, k = int(m.group(1)), int(m.group(2))
            return strings[sid][:k]
        m = self._RE_REF_SUF.match(tok_str)
        if m:
            sid, k = int(m.group(1)), int(m.group(2))
            return strings[sid][-k:]
        raise ValueError(f"token desconhecido: {tok_str!r}")

    def decode(self, tcf_text: str) -> list[str]:
        strings: dict[int, str] = {}
        body_seq: list[tuple[int, int]] = []
        in_body = False

        for raw in tcf_text.splitlines():
            linha = raw.strip()
            if not linha:
                continue
            if linha == "<body>":
                in_body = True
                continue
            if linha == "</body>":
                in_body = False
                continue
            if not in_body:
                continue

            m = self._RE_DECL.match(linha)
            if m:
                eid = int(m.group(1))
                count = int(m.group(2)) if m.group(2) else 1
                forma = m.group(3)
                partes = [self._parse_token(p, strings)
                          for p in forma.split(' + ')]
                strings[eid] = "".join(partes)
                body_seq.append((eid, count))
                continue

            m = self._RE_REF.match(linha)
            if m:
                count = int(m.group(1)) if m.group(1) else 1
                eid = int(m.group(2))
                body_seq.append((eid, count))
                continue

            raise ValueError(f"linha mal formada: {linha!r}")

        saida: list[str] = []
        for eid, count in body_seq:
            saida.extend([strings[eid]] * count)
        return saida
