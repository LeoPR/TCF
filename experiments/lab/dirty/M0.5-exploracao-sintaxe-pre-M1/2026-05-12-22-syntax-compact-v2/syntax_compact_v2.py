"""Sintaxe compacta v2 — fragmentos com idx automatico.

Conceito principal: a propria linha do no e fragmentada nas
positions que outros nos vao referenciar. Cada fragmento ganha
**idx global automatico** na ordem de aparicao no body.

Em vez de `noN[a:b]` (ou `@N<K`, `@N>K`), refs externas usam
diretamente o(s) `idx` dos fragmentos que cobrem o slice
desejado.

## Gramatica

Body:
  [
  <linha-do-no-1>
  <linha-do-no-2>
  ...
  ]

Cada linha contem uma sequencia de **elementos**:
  - `'X'`           literal, aloca proximo idx; texto X
  - `N` ou `N,M,...` lista de refs por idx (sem aspas)

Concatenacao entre elementos e implicita — o parser identifica
fronteira pelo char inicial (`'` ou digito).

## Exemplo D2-mini

Linha 1 — s1 com quebras em {10,12,13,17} (vindas das refs futuras
de s2, s3, s4):

    'maria.silv''a@''g''mail''.com'        idx 1, 2, 3, 4, 5

Linha 2 — s2 = pref(1,12) + 'hot' + suf(1,8). Pref(1,12) cobre
chars [0:12] de s1 = idx 1+2; suf(1,8) cobre [-8:] de s1 = idx 4+5;
'hot' aloca idx 6.

    1,2'hot'4,5

Linha 5 — s5 = pref(4,11) + suf(2,11). Cobre s4[0:11] e s2[-11:].
Cada cobertura traduzida em sequencia de idx.

    8,2,6,4,5

## Como sao computadas as quebras

Passada 1 sobre todos os tokens: para cada `RefPref(j, k)`,
position `k` em j vira quebra; para cada `RefSuf(j, k)`,
position `len(j) - k` vira quebra.

Garantia: cada slice referenciado coincide exatamente com 1+
fragmentos contiguos do no referenciado.

## Limitacoes

- Literais nao podem conter `'`. Em datasets atuais nao ocorre.
- Idx multi-digito sem ambiguidade via separador `,`.
- RLE adjacente nao implementado (datasets atuais sao todas unicas).
"""

from online import Token, TokLit, TokRefPref, TokRefSuf
from syntax_base import Syntax


class CompactV2Syntax(Syntax):

    name = "compact_v2"

    def _coletar_quebras(self,
                          unicas: list[str],
                          tokens_por_string: list[list[Token]]
                          ) -> dict[int, set[int]]:
        """Para cada eid, retorna o conjunto de positions que precisam
        ser quebras.

        Inclui:
        1. Quebras diretas: para cada ref `(eid_ref, K)` em qualquer
           token, position K (pref) ou len-K (suf) e quebra em eid_ref.
        2. Quebras propagadas: se eid tem quebra em pos Q dentro de um
           token RefPref/RefSuf, essa quebra propaga para o no
           referenciado na position correspondente.

        Propagacao em ordem inversa (do maior eid para o menor)
        garante que todas as propagacoes em cadeia sejam aplicadas
        em uma unica passada (tokens so referenciam eid menor — online).
        """
        quebras: dict[int, set[int]] = {
            eid: set() for eid in range(1, len(unicas) + 1)
        }

        # Quebras diretas
        for tokens in tokens_por_string:
            for tok in tokens:
                if isinstance(tok, TokRefPref):
                    quebras[tok.string_id].add(tok.length)
                elif isinstance(tok, TokRefSuf):
                    s_ref = unicas[tok.string_id - 1]
                    quebras[tok.string_id].add(len(s_ref) - tok.length)

        # Propagacao em ordem inversa
        for eid in range(len(unicas), 0, -1):
            tokens = tokens_por_string[eid - 1]
            pos = 0
            for tok in tokens:
                if isinstance(tok, TokLit):
                    pos += len(tok.text)
                elif isinstance(tok, TokRefPref):
                    ref_eid = tok.string_id
                    cobertura = tok.length
                    for q in list(quebras[eid]):
                        if pos < q < pos + cobertura:
                            quebras[ref_eid].add(q - pos)
                    pos += cobertura
                else:  # TokRefSuf
                    ref_eid = tok.string_id
                    cobertura = tok.length
                    ref_start = len(unicas[ref_eid - 1]) - cobertura
                    for q in list(quebras[eid]):
                        if pos < q < pos + cobertura:
                            quebras[ref_eid].add((q - pos) + ref_start)
                    pos += cobertura
        return quebras

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
        quebras = self._coletar_quebras(strings_unicas, tokens_por_string)
        unica_to_eid = {s: i + 1 for i, s in enumerate(strings_unicas)}

        frags_por_no: dict[int, list[tuple[int, int, int]]] = {}
        proximo_idx_frag = 1
        eid_emitido: set[int] = set()
        body_linhas: list[str] = []

        for s_run, count in self._rle_adjacente(linhas_originais):
            eid = unica_to_eid[s_run]

            if eid not in eid_emitido:
                # Declaracao de novo no
                s = strings_unicas[eid - 1]
                tokens = tokens_por_string[eid - 1]
                quebras_aqui = quebras[eid]
                frags_por_no[eid] = []

                elementos: list[tuple[str, object]] = []
                pos = 0
                for tok in tokens:
                    if isinstance(tok, TokLit):
                        start_lit = pos
                        end_lit = pos + len(tok.text)
                        qs = sorted(q for q in quebras_aqui
                                    if start_lit < q < end_lit)
                        pontos = [start_lit] + qs + [end_lit]
                        for i in range(len(pontos) - 1):
                            a, b = pontos[i], pontos[i + 1]
                            idx = proximo_idx_frag
                            proximo_idx_frag += 1
                            frags_por_no[eid].append((a, b, idx))
                            elementos.append(('lit', s[a:b]))
                        pos = end_lit
                    elif isinstance(tok, TokRefPref):
                        ref_eid = tok.string_id
                        ref_end = tok.length
                        herdados = [(a, b, idx)
                                    for (a, b, idx) in frags_por_no[ref_eid]
                                    if a < ref_end and b <= ref_end]
                        for (a, b, idx) in herdados:
                            frags_por_no[eid].append((pos + a, pos + b, idx))
                            elementos.append(('ref', idx))
                        pos += tok.length
                    else:  # TokRefSuf
                        ref_eid = tok.string_id
                        s_ref = strings_unicas[ref_eid - 1]
                        ref_start = len(s_ref) - tok.length
                        herdados = [(a, b, idx)
                                    for (a, b, idx) in frags_por_no[ref_eid]
                                    if a >= ref_start and b > ref_start]
                        for (a, b, idx) in herdados:
                            frags_por_no[eid].append(
                                (pos + (a - ref_start),
                                 pos + (b - ref_start), idx))
                            elementos.append(('ref', idx))
                        pos += tok.length

                # Construir string da linha
                partes_emit: list[str] = []
                ultimo_tipo = None
                for tipo, val in elementos:
                    if tipo == 'lit':
                        partes_emit.append(f"'{val}'")
                    else:
                        if ultimo_tipo == 'ref':
                            partes_emit.append(",")
                        partes_emit.append(str(val))
                    ultimo_tipo = tipo
                linha_resto = "".join(partes_emit)
                eid_emitido.add(eid)
            else:
                # Uso de no ja declarado
                linha_resto = f"^{eid}"

            if count > 1:
                body_linhas.append(f"*{count}|{linha_resto}")
            else:
                body_linhas.append(linha_resto)

        return "\n".join(["[", *body_linhas, "]"]) + "\n"

    # ---- decode ----

    def decode(self, tcf_text: str) -> list[str]:
        frags: dict[int, str] = {}
        proximo_idx = 1
        nos_decl: list[str] = []  # nos na ordem de declaracao
        saida: list[str] = []

        for raw in tcf_text.splitlines():
            linha = raw.strip()
            if not linha or linha in ("[", "]"):
                continue

            # Prefixo de repeticao *K|
            if linha.startswith("*"):
                bar = linha.find("|")
                if bar < 0:
                    raise ValueError(f"prefixo *K| mal formado: {linha!r}")
                count = int(linha[1:bar])
                resto = linha[bar + 1:]
            else:
                count = 1
                resto = linha

            if resto.startswith("^"):
                # Uso de no ja declarado
                no_id = int(resto[1:])
                s_no = nos_decl[no_id - 1]
            else:
                # Declaracao de novo no
                partes: list[str] = []
                i = 0
                n = len(resto)
                while i < n:
                    ch = resto[i]
                    if ch == "'":
                        fim = resto.find("'", i + 1)
                        if fim < 0:
                            raise ValueError(f"aspa nao fechada: {resto!r}")
                        texto = resto[i + 1:fim]
                        frags[proximo_idx] = texto
                        partes.append(texto)
                        proximo_idx += 1
                        i = fim + 1
                    elif ch.isdigit():
                        j = i
                        while j < n and (resto[j].isdigit() or resto[j] == ","):
                            j += 1
                        for r in resto[i:j].split(","):
                            if r:
                                partes.append(frags[int(r)])
                        i = j
                    else:
                        raise ValueError(
                            f"char inesperado {ch!r} em {resto!r} pos {i}")
                s_no = "".join(partes)
                nos_decl.append(s_no)

            saida.extend([s_no] * count)

        return saida
