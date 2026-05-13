"""Sintaxe compacta v6-sumida — Etapa 2 do flow semantico.

Comeca da v4-quote-fixed e adiciona **sumida**: dígitos no literal
nao recebem marcacao se a sequencia formar um numero N que NAO
corresponde a idx existente.

Exemplos:
  Literal "256" no eid=12 de um dataset com 12 nos: int("256")=256;
  idx 256 nunca foi declarado nem sera; pode sair raw.

  Literal "1" no eid=2 (idx 1 ja foi declarado): conflita; precisa
  marcacao (aspas).

Decoder stateful:
  - Mantem dict eid -> string
  - Em modo literal, ao ver sequencia de digitos: tenta como ref
  - Se idx N nao existe (ainda nao declarado): trata como literal
  - Se idx N existe: e ref

Encoder garante que cada sequencia de digitos no literal forma
um N que nao corresponde a idx declarado ate aquele ponto. Se
nao puder garantir, usa aspas como v4-q-fix.

Raiz: tokens do online.py (exp 16). Mesma estrutura de
fragmentacao e quebras.
"""

import re
from online import Token, TokLit, TokRefPref, TokRefSuf
from syntax_base import Syntax


class CompactV6SumidaSyntax(Syntax):

    name = "compact_v6_sumida"

    _RE_DIGITS = re.compile(r'\d+')

    def _coletar_quebras(self, unicas, tokens_por_string):
        quebras = {eid: set() for eid in range(1, len(unicas) + 1)}
        for tokens in tokens_por_string:
            for tok in tokens:
                if isinstance(tok, TokRefPref):
                    quebras[tok.string_id].add(tok.length)
                elif isinstance(tok, TokRefSuf):
                    s_ref = unicas[tok.string_id - 1]
                    quebras[tok.string_id].add(len(s_ref) - tok.length)
        for eid in range(len(unicas), 0, -1):
            tokens = tokens_por_string[eid - 1]
            pos = 0
            for tok in tokens:
                if isinstance(tok, TokLit):
                    pos += len(tok.text)
                elif isinstance(tok, TokRefPref):
                    re_eid = tok.string_id
                    cov = tok.length
                    for q in list(quebras[eid]):
                        if pos < q < pos + cov:
                            quebras[re_eid].add(q - pos)
                    pos += cov
                else:
                    re_eid = tok.string_id
                    cov = tok.length
                    rs = len(unicas[re_eid - 1]) - cov
                    for q in list(quebras[eid]):
                        if pos < q < pos + cov:
                            quebras[re_eid].add((q - pos) + rs)
                    pos += cov
        return quebras

    def _rle_adjacente(self, linhas):
        out = []
        for s in linhas:
            if out and out[-1][0] == s:
                out[-1] = (s, out[-1][1] + 1)
            else:
                out.append((s, 1))
        return out

    def _pode_sumir(self, text: str, max_eid_existente: int) -> bool:
        """Retorna True se o fragmento INTEIRAMENTE de digitos
        forma um N > max_eid_existente.

        Restricao: fragmento deve ser SO digitos. Letras+digitos
        no mesmo fragmento exigiriam sub-dividir o fragmento, o
        que muda a estrutura de idx (alocacao por fragmento).
        Isso fica para slice arbitrario (proxima etapa).
        """
        if not text:
            return False
        if not text.isdigit():
            return False  # letras misturadas - nao pode sumir
        n = int(text)
        return n > max_eid_existente

    def _emit_literal_com_aspas(self, text: str) -> str:
        """Emite literal com aspas + escape interno (igual v4-q-fix)."""
        esc = text.replace("\\", "\\\\").replace("'", "\\'")
        return f"'{esc}'"

    def encode(self, linhas_originais, strings_unicas,
                tokens_por_string, header):
        quebras = self._coletar_quebras(strings_unicas, tokens_por_string)
        unica_to_eid = {s: i + 1 for i, s in enumerate(strings_unicas)}

        frags_por_no = {}
        proximo_idx = 1
        eid_emitido = set()
        body_linhas = []

        # max_eid_existente cresce a medida que linhas sao emitidas
        # No decoder, idx N existe DEPOIS que linha eid=N foi
        # totalmente processada. Para sumida funcionar, encoder usa:
        #   max_idx_disponivel = max(idx no body ate aqui)
        # Mas idx em v6-sumida = eid (1 por no), entao corresponde
        # ao numero de nos declarados ate aqui.

        for s_run, count in self._rle_adjacente(linhas_originais):
            eid = unica_to_eid[s_run]

            if eid not in eid_emitido:
                s = strings_unicas[eid - 1]
                tokens = tokens_por_string[eid - 1]
                quebras_aqui = quebras[eid]
                frags_por_no[eid] = []
                elementos = []
                pos = 0

                # Captura idx MAXIMO existente ANTES desta linha. idx
                # alocado por fragmentos desta linha NAO conta para
                # "pode_sumir" (refs no online.py so apontam para eids
                # anteriores; idx local nunca e' referenciado de fora
                # desta linha pela proxima string).
                max_idx_existente = proximo_idx - 1

                for tok in tokens:
                    if isinstance(tok, TokLit):
                        sl, el = pos, pos + len(tok.text)
                        qs = sorted(q for q in quebras_aqui if sl < q < el)
                        pts = [sl] + qs + [el]
                        for i in range(len(pts) - 1):
                            a, b = pts[i], pts[i + 1]
                            idx = proximo_idx
                            proximo_idx += 1
                            frags_por_no[eid].append((a, b, idx))
                            elementos.append(('lit', s[a:b]))
                        pos = el
                    elif isinstance(tok, TokRefPref):
                        re_eid = tok.string_id
                        herdados = [(a, b, idx)
                                     for (a, b, idx) in frags_por_no[re_eid]
                                     if a < tok.length and b <= tok.length]
                        for (a, b, idx) in herdados:
                            frags_por_no[eid].append((pos + a, pos + b, idx))
                            elementos.append(('ref', idx))
                        pos += tok.length
                    else:
                        re_eid = tok.string_id
                        s_ref = strings_unicas[re_eid - 1]
                        rs = len(s_ref) - tok.length
                        herdados = [(a, b, idx)
                                     for (a, b, idx) in frags_por_no[re_eid]
                                     if a >= rs and b > rs]
                        for (a, b, idx) in herdados:
                            frags_por_no[eid].append(
                                (pos + (a - rs), pos + (b - rs), idx))
                            elementos.append(('ref', idx))
                        pos += tok.length

                # Para cada literal nos elementos, decidir:
                # - 'raw' se nao tem digitos/asterisco (sem ambig)
                # - 'sumir' se pode sumir E posicao permite economia
                # - 'quoted' caso contrario (aspas como v4-q-fix)
                literais_classificados = []
                for k, (tipo, val) in enumerate(elementos):
                    if tipo != 'lit':
                        literais_classificados.append(None)
                        continue
                    tem_ambig = any(c.isdigit() or c == '*' for c in val)
                    if not tem_ambig:
                        literais_classificados.append('raw')
                    elif self._pode_sumir(val, max_idx_existente):
                        # Sumida vale se elimina aspas SEM precisar
                        # de separador extra que custe mais.
                        # Regra simples: se o literal esta entre
                        # 2 elementos do mesmo tipo refs, sumida +
                        # 2 separadores = mesmo custo de aspas (2B).
                        # So' vale sumir se ha pelo menos um vizinho
                        # 'lit' ou se for borda da linha (ai 1 sep
                        # economizado).
                        vizinho_antes_e_ref = (
                            k > 0 and elementos[k - 1][0] == 'ref'
                        )
                        vizinho_depois_e_ref = (
                            k < len(elementos) - 1
                            and elementos[k + 1][0] == 'ref'
                        )
                        # Borda da linha → 1 separador economizado
                        if (not vizinho_antes_e_ref or
                                not vizinho_depois_e_ref):
                            literais_classificados.append('sumir')
                        else:
                            # entre 2 refs: empate; preferir quoted
                            # (mais legivel + parser robusto)
                            literais_classificados.append('quoted')
                    else:
                        literais_classificados.append('quoted')

                partes = []
                prev_tipo = None
                for k, (tipo, val) in enumerate(elementos):
                    if tipo == 'lit':
                        clase = literais_classificados[k]
                        if clase == 'quoted':
                            emitido = self._emit_literal_com_aspas(val)
                        else:
                            emitido = val  # raw ou sumir
                        # Separador entre 2 literais consecutivos
                        if prev_tipo == 'lit':
                            ultimo = partes[-1]
                            if not ultimo.endswith("'"):
                                partes.append('*')
                        # Se sumida vem depois de ref, precisa separar
                        elif prev_tipo == 'ref' and clase == 'sumir':
                            partes.append('*')
                        partes.append(emitido)
                    else:
                        if prev_tipo == 'ref':
                            partes.append(',')
                        # Se proximo elem e' lit sumir, sep vira depois
                        partes.append(str(val))
                    prev_tipo = tipo
                linha_resto = "".join(partes)
                eid_emitido.add(eid)
            else:
                linha_resto = f"^{eid}"

            if count > 1:
                body_linhas.append(f"*{count}|{linha_resto}")
            else:
                body_linhas.append(linha_resto)

        return "\n".join(["[", *body_linhas, "]"]) + "\n"

    def _parse_decl(self, resto, frags, proximo_idx_ref, nos_decl):
        """Parser stateful. Em modo literal sem aspas, ao ver
        sequencia de digitos: tenta como ref ao idx N. Se N <=
        max_idx_existente_antes_desta_linha, e' ref. Se N >, e'
        literal (sumida).

        idx max ANTES desta linha = proximo_idx_ref[0] - 1 capturado
        no inicio. Durante o parse, proximo_idx_ref cresce com
        novos literais, mas eles nao podem ser ref aqui porque
        online.py so emite refs para eids anteriores.
        """
        partes = []
        i = 0
        n = len(resto)
        max_idx_existente = proximo_idx_ref[0] - 1

        while i < n:
            ch = resto[i]
            if ch == '*':
                i += 1
            elif ch.isdigit():
                # Le sequencia de digitos
                j = i
                while j < n and (resto[j].isdigit() or resto[j] == ','):
                    j += 1
                seq_str = resto[i:j]
                # E uma lista de refs (com `,`) ou uma sequencia?
                if ',' in seq_str:
                    # tradicional: refs separadas por , (cada uma deve existir)
                    for r in seq_str.split(','):
                        if r:
                            n_val = int(r)
                            if 1 <= n_val <= max_idx_existente:
                                partes.append(frags[n_val])
                            else:
                                # idx nao existe; literal — aloca idx
                                frags[proximo_idx_ref[0]] = r
                                partes.append(r)
                                proximo_idx_ref[0] += 1
                else:
                    # sequencia unica de digitos
                    n_val = int(seq_str)
                    if 1 <= n_val <= max_idx_existente:
                        partes.append(frags[n_val])
                    else:
                        # idx nao existe; sumida — literal + aloca idx
                        # (encoder tambem alocou idx para esse fragmento)
                        frags[proximo_idx_ref[0]] = seq_str
                        partes.append(seq_str)
                        proximo_idx_ref[0] += 1
                i = j
            elif ch == "'":
                # literal com aspas (caso v4-q-fix esteja em uso)
                buf = []
                j = i + 1
                while j < n and resto[j] != "'":
                    if resto[j] == '\\':
                        j += 1
                        if j >= n:
                            raise ValueError("escape no fim de linha")
                        buf.append(resto[j])
                        j += 1
                    else:
                        buf.append(resto[j])
                        j += 1
                if j >= n:
                    raise ValueError(f"aspa nao fechada em {resto!r}")
                texto = ''.join(buf)
                frags[proximo_idx_ref[0]] = texto
                partes.append(texto)
                proximo_idx_ref[0] += 1
                i = j + 1
            else:
                # literal sem aspas
                buf = []
                while i < n:
                    c = resto[i]
                    if c.isdigit() or c == '*':
                        break
                    buf.append(c)
                    i += 1
                texto = ''.join(buf)
                frags[proximo_idx_ref[0]] = texto
                partes.append(texto)
                proximo_idx_ref[0] += 1
        return "".join(partes)

    def decode(self, tcf_text):
        frags = {}
        proximo_idx_ref = [1]
        nos_decl = []  # idx N corresponde a nos_decl[N-1]
        saida = []

        for raw in tcf_text.splitlines():
            linha = raw.strip()
            if not linha or linha in ("[", "]"):
                continue

            if linha.startswith("*") and "|" in linha:
                bar = linha.find("|")
                count = int(linha[1:bar])
                resto = linha[bar + 1:]
            else:
                count = 1
                resto = linha

            if resto.startswith("^"):
                no_id = int(resto[1:])
                s_no = nos_decl[no_id - 1]
            else:
                s_no = self._parse_decl(
                    resto, frags, proximo_idx_ref, nos_decl)
                nos_decl.append(s_no)

            saida.extend([s_no] * count)
        return saida
