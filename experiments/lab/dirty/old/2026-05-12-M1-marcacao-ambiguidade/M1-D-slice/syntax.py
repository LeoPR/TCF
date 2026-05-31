"""M1.D — Slice arbitrario (referencia trecho central de string ancestral).

Tecnica: declara o literal de cada no INTEIRO (sem fragmentar) e
referencia trechos via slice `e:a-b` (chars [a:b] da string original
do eid `e`).

Diferenca vs M1.A/B/E/C:
- Aqueles fragmentam literal do no fonte em N pedacos (por
  propagacao de quebras de descendentes), cada um com idx separado.
  Descendente referencia lista de idx-frags consecutivos.
- M1.D NAO fragmenta. Literal do no fonte vira 1 idx. Descendente
  usa slice(eid, a, b) direto.

Trade-off:
- Ganho: nao paga overhead `*` de separadores entre frags do no fonte
  (D3 eid=1: 7 frags = 6 `*` overhead).
- Custo: cada slice precisa 3 numeros (eid, a, b) em vez de 1
  idx-de-frag. Slice e' verboso para refs simples.

Sintaxe: `e:a-b` onde:
- `e` = eid (string-id, 1-indexed)
- `a` = offset inicial (incluso)
- `b` = offset final (excluso)

Casos especiais:
- `e:0-k` = prefixo k chars (= TokRefPref)
- `e:(n-k)-n` = sufixo k chars (= TokRefSuf)
- `e:a-b` (geral) = trecho central (NOVO — nao existia nas outras)

Decoder mantem `eids_decodados[e-1]` = string completa reconstruida
de cada eid. Slice retorna substring `[a:b]`.

Algoritmo: usa tokens raw de online.py (sem propagar quebras).
Literais ficam inteiros, refs viram slice.

Combina com escape escopo (M1.A') para chars ambiguos em literais.
NAO usa range (refs sao slices, nao listas de idx).

Implementado do zero (sem importar M1.A'/E/C).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from online import Token, TokLit, TokRefPref, TokRefSuf
from syntax_base import Syntax


class M1DSliceSyntax(Syntax):

    name = "M1-D-slice"

    def _rle_adjacente(self, linhas):
        out = []
        for s in linhas:
            if out and out[-1][0] == s:
                out[-1] = (s, out[-1][1] + 1)
            else:
                out.append((s, 1))
        return out

    # ---- escape escopo (igual M1.A') ----

    @staticmethod
    def _escape_e_termina_em_digito(text: str) -> tuple[str, bool]:
        out = []
        i = 0
        n = len(text)
        termina_seq_digito = False
        while i < n:
            c = text[i]
            if c.isdigit():
                j = i
                while j < n and text[j].isdigit():
                    j += 1
                out.append('\\')
                out.append(text[i:j])
                termina_seq_digito = (j == n)
                i = j
            elif c == '*' or c == '\\':
                out.append('\\')
                out.append(c)
                termina_seq_digito = False
                i += 1
            else:
                out.append(c)
                termina_seq_digito = False
                i += 1
        return ''.join(out), termina_seq_digito

    # ---- encode ----

    def encode(self, linhas_originais, strings_unicas,
                tokens_por_string, header):
        """Itera tokens raw (TokLit/RefPref/RefSuf) sem propagar
        quebras. Cada TokLit vira 1 frag inteiro; refs viram slice.
        """
        unica_to_eid = {s: i + 1 for i, s in enumerate(strings_unicas)}
        eid_emitido = set()
        body_linhas = []

        for s_run, count in self._rle_adjacente(linhas_originais):
            eid = unica_to_eid[s_run]

            if eid not in eid_emitido:
                tokens = tokens_por_string[eid - 1]

                # elementos: ('lit', text) ou ('slice', e, a, b)
                elementos = []
                for tok in tokens:
                    if isinstance(tok, TokLit):
                        elementos.append(('lit', tok.text))
                    elif isinstance(tok, TokRefPref):
                        elementos.append(('slice', tok.string_id, 0, tok.length))
                    else:  # TokRefSuf
                        e_ref = tok.string_id
                        n_ref = len(strings_unicas[e_ref - 1])
                        elementos.append(('slice', e_ref, n_ref - tok.length, n_ref))

                # Monta linha. Separadores `*`:
                # - lit-lit: sempre `*`
                # - slice-lit ou lit-slice: depende
                # - slice-slice: sempre `*` (caso contrario `1:5-104:0-2` ambiguo)
                partes = []
                prev_tipo = None
                prev_emit_termina_em_digito = False
                for elem in elementos:
                    tipo = elem[0]
                    if tipo == 'lit':
                        _, val = elem
                        if prev_tipo == 'lit':
                            partes.append('*')
                        elif prev_tipo == 'slice' and val and val[0].isdigit():
                            # slice termina em digit; lit comeca em digit
                            # → parser uniria. Mas escape escopo do lit
                            # vai inserir `\` antes do digit, separando.
                            # OK sem `*`.
                            pass
                        emitido, term_seq = self._escape_e_termina_em_digito(val)
                        partes.append(emitido)
                        prev_emit_termina_em_digito = term_seq
                        prev_tipo = 'lit'
                    else:  # slice
                        _, e, a, b = elem
                        slice_txt = f"{e}:{a}-{b}"
                        if prev_emit_termina_em_digito:
                            # lit anterior terminou em digit-seq; slice
                            # comeca com digit. Precisa `*`.
                            partes.append('*')
                            prev_emit_termina_em_digito = False
                        elif prev_tipo == 'slice':
                            # slice-slice: precisa `*` (slice anterior
                            # termina em digit, proximo comeca com digit)
                            partes.append('*')
                        partes.append(slice_txt)
                        prev_tipo = 'slice'
                        prev_emit_termina_em_digito = True  # `b` e' digit

                linha_resto = ''.join(partes)
                eid_emitido.add(eid)
            else:
                linha_resto = f"^{eid}"

            if count > 1:
                body_linhas.append(f"*{count}|{linha_resto}")
            else:
                body_linhas.append(linha_resto)

        return "\n".join(["[", *body_linhas, "]"]) + "\n"

    # ---- decode ----

    def _parse_decl(self, resto, eids_decodados):
        """Parser stateful que reconstroi a string da linha lendo
        literais e slices. `eids_decodados` e' a lista (em ordem) de
        strings ja' reconstruidas (1-indexed via [e-1])."""
        partes = []
        i = 0
        n = len(resto)
        while i < n:
            ch = resto[i]
            if ch == '*':
                i += 1
            elif ch.isdigit():
                # slice: e:a-b
                # le primeiro numero (eid)
                j = i
                while j < n and resto[j].isdigit():
                    j += 1
                if j >= n or resto[j] != ':':
                    raise ValueError(f"slice malformado em pos {i}: esperava ':'")
                e = int(resto[i:j])
                i = j + 1  # pula ':'
                # le 'a'
                j = i
                while j < n and resto[j].isdigit():
                    j += 1
                if j >= n or resto[j] != '-':
                    raise ValueError(f"slice malformado em pos {i}: esperava '-'")
                a = int(resto[i:j])
                i = j + 1  # pula '-'
                # le 'b'
                j = i
                while j < n and resto[j].isdigit():
                    j += 1
                b = int(resto[i:j])
                i = j
                partes.append(eids_decodados[e - 1][a:b])
            else:
                # literal com escape `\X` ou escape escopo `\<digits>`
                buf = []
                while i < n:
                    c = resto[i]
                    if c == '\\':
                        i += 1
                        if i >= n:
                            raise ValueError("escape no fim de linha")
                        next_c = resto[i]
                        if next_c.isdigit():
                            j = i
                            while j < n and resto[j].isdigit():
                                j += 1
                            buf.append(resto[i:j])
                            i = j
                        else:
                            buf.append(next_c)
                            i += 1
                    elif c.isdigit() or c == '*':
                        break
                    else:
                        buf.append(c)
                        i += 1
                partes.append(''.join(buf))
        return ''.join(partes)

    def decode(self, tcf_text):
        eids_decodados = []
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
                s_no = eids_decodados[no_id - 1]
            else:
                s_no = self._parse_decl(resto, eids_decodados)
                eids_decodados.append(s_no)

            saida.extend([s_no] * count)
        return saida
