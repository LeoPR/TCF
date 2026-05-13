"""Sintaxe compacta v1b — v1 sem prefixo `@N:` na declaracao.

Vs compact_v1:
- Linha de declaracao perde o cabecalho `@N:`. A ordem da linha
  define o id do no implicitamente.
- Referencias internas continuam usando `@N<K` e `@N>K`.
- Linha de ref completo a outro no: `=N` (igual v1).
- Linha com count: `Nx=K` (igual v1).
- Macros: `[` e `]` (igual v1).

Exemplo D2-mini:

  Verbose:        no2: no1[0:12] + "hot" + no1[-8:]
  Compact v1:     @2:@1<12'hot'@1>8
  Compact v1b:    @1<12'hot'@1>8

Economia: 3 chars por linha de decl em N=1-9 (`@N:`), 4 em N=10-99.
"""

import re
from online import Token, TokLit, TokRefPref, TokRefSuf
from syntax_base import Syntax


class CompactV1bSyntax(Syntax):

    name = "compact_v1b"

    _RE_LIT = re.compile(r"^'(.*)'$")
    _RE_REF_PREF = re.compile(r'^@(\d+)<(\d+)$')
    _RE_REF_SUF = re.compile(r'^@(\d+)>(\d+)$')
    _RE_USO = re.compile(r'^(?:(\d+)x)?=(\d+)$')

    def _render_token(self, tok: Token) -> str:
        if isinstance(tok, TokLit):
            return f"'{tok.text}'"
        if isinstance(tok, TokRefPref):
            return f'@{tok.string_id}<{tok.length}'
        return f'@{tok.string_id}>{tok.length}'

    def _rle_adjacente(self, linhas):
        out = []
        for s in linhas:
            if out and out[-1][0] == s:
                out[-1] = (s, out[-1][1] + 1)
            else:
                out.append((s, 1))
        return out

    def encode(self, linhas_originais, strings_unicas,
                tokens_por_string, header):
        str_to_tokens = dict(zip(strings_unicas, tokens_por_string))
        unica_to_eid = {s: i + 1 for i, s in enumerate(strings_unicas)}
        eid_emitido = set()

        out = ["["]
        for s_run, count in self._rle_adjacente(linhas_originais):
            eid = unica_to_eid[s_run]
            prefixo = f"{count}x" if count > 1 else ""

            if eid not in eid_emitido:
                forma = "".join(self._render_token(t)
                                 for t in str_to_tokens[s_run])
                if count > 1:
                    out.append(f"{prefixo}{forma}")
                else:
                    out.append(forma)
                eid_emitido.add(eid)
            else:
                out.append(f"{prefixo}={eid}")

        out.append("]")
        return "\n".join(out) + "\n"

    def _parse_forma(self, forma: str, strings: dict[int, str]) -> str:
        partes = []
        i = 0
        n = len(forma)
        while i < n:
            ch = forma[i]
            if ch == "'":
                fim = forma.find("'", i + 1)
                if fim < 0:
                    raise ValueError(f"aspa nao fechada: {forma!r}")
                partes.append(forma[i + 1:fim])
                i = fim + 1
            elif ch == "@":
                j = i + 1
                while j < n and forma[j].isdigit():
                    j += 1
                sid = int(forma[i + 1:j])
                if j >= n or forma[j] not in "<>":
                    raise ValueError(f"esperava < ou > em {forma!r}")
                tipo = forma[j]
                k_start = j + 1
                k_end = k_start
                while k_end < n and forma[k_end].isdigit():
                    k_end += 1
                length = int(forma[k_start:k_end])
                s = strings[sid]
                partes.append(s[:length] if tipo == "<" else s[-length:])
                i = k_end
            else:
                raise ValueError(f"char inesperado {ch!r} em {forma!r}")
        return "".join(partes)

    def decode(self, tcf_text):
        strings = {}  # eid -> texto reconstruido
        body_seq = []  # (eid, count)
        proximo_eid = 1
        in_body = False

        for raw in tcf_text.splitlines():
            linha = raw.strip()
            if not linha:
                continue
            if linha == "[":
                in_body = True
                continue
            if linha == "]":
                in_body = False
                continue
            if not in_body:
                continue

            # extrair count prefix se houver: "Nx..."
            m_count = re.match(r'^(\d+)x(.*)$', linha)
            if m_count:
                count = int(m_count.group(1))
                resto = m_count.group(2)
            else:
                count = 1
                resto = linha

            # uso de no: =N
            m_uso = re.match(r'^=(\d+)$', resto)
            if m_uso:
                eid = int(m_uso.group(1))
                body_seq.append((eid, count))
                continue

            # decl: parsear forma
            eid = proximo_eid
            proximo_eid += 1
            strings[eid] = self._parse_forma(resto, strings)
            body_seq.append((eid, count))

        saida = []
        for eid, count in body_seq:
            saida.extend([strings[eid]] * count)
        return saida
