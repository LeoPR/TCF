"""Sintaxe compacta v1 — marcadores explicitos de 1 char.

Mapeamento vs verbose:

| Marcador verbose      | Compact v1     | Reducao |
|-----------------------|----------------|--------:|
| `noN`                 | `@N`           | -1 char |
| `noN[0:K]`            | `@N<K`         | -4 chars |
| `noN[-K:]`            | `@N>K`         | -5 chars |
| `"X"`                 | `'X'`          | igual |
| `+` (entre tokens)    | (omitido)      | -3 chars (com espacos) |
| `noN: forma`          | `@N:forma`     | -1 char (sem espaco apos :) |
| `ref:noN`             | `=N`           | -4 chars |
| `Nx ref:noN`          | `Nx=N`         | -4 chars |
| `<body>` / `</body>`  | `[` / `]`      | -5 chars cada |

Exemplo:
    Verbose: no2: no1[0:12] + "hot" + no1[-8:]    (30 chars)
    Compact: @2:@1<12'hot'@1>8                    (17 chars)

Concatenacao entre tokens e implicita — cada token comeca com
char distintivo: `@` (ref), `'` (literal). Parser identifica
limite de token pelo char de inicio do proximo.

Limitacao: literais nao podem conter `'`. Em datasets atuais (emails,
URLs, UUIDs, datas, IPs, CPFs, codigos) isso nao ocorre. Em datasets
com aspas simples no conteudo, sintaxe quebraria — precisaria
escape (deferido).
"""

import re
from online import Token, TokLit, TokRefPref, TokRefSuf
from syntax_base import Syntax


class CompactV1Syntax(Syntax):

    name = "compact_v1"

    _RE_DECL_HEAD = re.compile(r'^@(\d+):(.*)$')
    _RE_REF = re.compile(r'^(?:(\d+)x)?=(\d+)$')
    _RE_COUNT_PREFIX = re.compile(r'^(\d+)x')

    # ---- encode ----

    def _render_token(self, tok: Token) -> str:
        if isinstance(tok, TokLit):
            return f"'{tok.text}'"
        if isinstance(tok, TokRefPref):
            return f'@{tok.string_id}<{tok.length}'
        return f'@{tok.string_id}>{tok.length}'  # TokRefSuf

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

        out: list[str] = ["["]
        for s, count in self._rle_adjacente(linhas_originais):
            if s not in str_to_eid:
                str_to_eid[s] = proximo_eid
                proximo_eid += 1
            eid = str_to_eid[s]
            prefixo = f"{count}x" if count > 1 else ""

            if eid not in decl_emitida:
                forma = "".join(self._render_token(t) for t in str_to_tokens[s])
                out.append(f"@{eid}:{prefixo}{forma}")
                decl_emitida.add(eid)
            else:
                out.append(f"{prefixo}={eid}")

        out.append("]")
        return "\n".join(out) + "\n"

    # ---- decode ----

    def _parse_forma(self, forma_str: str,
                      strings: dict[int, str]) -> str:
        """Parser sequencial: tokens contiguos com inicio distintivo.

        - `'X'` literal (ate proxima aspa)
        - `@N<K` prefixo K de @N
        - `@N>K` sufixo K de @N
        """
        partes: list[str] = []
        i = 0
        n = len(forma_str)
        while i < n:
            ch = forma_str[i]
            if ch == "'":
                fim = forma_str.find("'", i + 1)
                if fim < 0:
                    raise ValueError(f"aspa de fechamento ausente em {forma_str!r}")
                partes.append(forma_str[i + 1:fim])
                i = fim + 1
            elif ch == "@":
                # le @<id><<|>><length>
                j = i + 1
                while j < n and forma_str[j].isdigit():
                    j += 1
                if j == i + 1:
                    raise ValueError(f"@ sem id em {forma_str!r} pos {i}")
                sid = int(forma_str[i + 1:j])
                if j >= n or forma_str[j] not in "<>":
                    raise ValueError(f"esperava < ou > apos @{sid} em {forma_str!r}")
                tipo = forma_str[j]
                k_start = j + 1
                k_end = k_start
                while k_end < n and forma_str[k_end].isdigit():
                    k_end += 1
                if k_end == k_start:
                    raise ValueError(f"length ausente em @{sid}{tipo} em {forma_str!r}")
                length = int(forma_str[k_start:k_end])
                s = strings[sid]
                if tipo == "<":
                    partes.append(s[:length])
                else:
                    partes.append(s[-length:])
                i = k_end
            else:
                raise ValueError(f"char inesperado {ch!r} em {forma_str!r} pos {i}")
        return "".join(partes)

    def decode(self, tcf_text: str) -> list[str]:
        strings: dict[int, str] = {}
        body_seq: list[tuple[int, int]] = []
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

            m = self._RE_DECL_HEAD.match(linha)
            if m:
                eid = int(m.group(1))
                resto = m.group(2)
                m_count = self._RE_COUNT_PREFIX.match(resto)
                if m_count:
                    count = int(m_count.group(1))
                    forma = resto[m_count.end():]
                else:
                    count = 1
                    forma = resto
                strings[eid] = self._parse_forma(forma, strings)
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
