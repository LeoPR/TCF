"""M2.A — Alias de tupla de refs.

Tecnica: identifica subsequencias de refs (tuplas) que se repetem
entre linhas e substitui por alias `$N` declarado em preambulo.

Analise teorica (escala):

Para tupla de Lt chars usada em R linhas:
- Custo declaracao: `$N=<tupla>` ~ (1 + len(N) + 1 + Lt) chars
  (`$` + `N` + `=` + tupla)
- Economia por uso: Lt - (1 + len(N)) chars (alias substitui tupla)
- Net = R * (Lt - 1 - len(N)) - (Lt + 2 + len(N))

Para N=1 (1 digit), Lt=8: Net = R*6 - 11 → positivo se R >= 2

Combina com M1.E como base (range + escape escopo). Aplica aliases
**sobre a serializacao M1.E** — substitui sequencias de refs ja'
expressas como `a,b,c` ou `a..b` por aliases quando vale.

Sintaxe:
- Preambulo (apos `[` body open):
    `$1=3,11,5,6`
    `$2=3,12,6`
- Uso na linha: `$1` substitui tupla onde apareceria

Decoder le preambulo, monta tabela de aliases, expande `$N` antes
de processar refs normais.

Detector (encoder):
1. Aplica M1.E como base, gera linhas com refs
2. Coleta runs-de-refs de cada linha (sequencias consecutivas)
3. Identifica sufixos comuns entre runs (subsequencias finais)
4. Seleciona gulosamente aliases com net positivo
5. Reescreve linhas substituindo sufixos por aliases
6. Emite preambulo + linhas reescritas

Limitacoes:
- `$` vira reservado em literais. Para chars `$` em literal,
  precisaria escape (nao implementado — datasets D1-D4 nao tem `$`).
- Detector usa sufixos comuns (greedy). Nao otimo.
- Aliases so' substituem RUN COMPLETO ou SUFIXO da run, nao prefixo
  nem trecho central.
"""

import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from online import Token, TokLit, TokRefPref, TokRefSuf
from syntax_base import Syntax


class M2AAliasTuplaSyntax(Syntax):

    name = "M2-A-alias-tupla"

    # ---- coleta de quebras + frags (igual M1.E) ----

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
                    cov = tok.length
                    for q in list(quebras[eid]):
                        if pos < q < pos + cov:
                            quebras[tok.string_id].add(q - pos)
                    pos += cov
                else:
                    cov = tok.length
                    rs = len(unicas[tok.string_id - 1]) - cov
                    for q in list(quebras[eid]):
                        if pos < q < pos + cov:
                            quebras[tok.string_id].add((q - pos) + rs)
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

    @staticmethod
    def _emit_refs_range(refs: list[int]) -> str:
        """Serializa refs com range (igual M1.E)."""
        if not refs:
            return ""
        runs = []
        cur = [refs[0]]
        for r in refs[1:]:
            if r == cur[-1] + 1:
                cur.append(r)
            else:
                runs.append(cur)
                cur = [r]
        runs.append(cur)
        partes = []
        for run in runs:
            if len(run) >= 3:
                partes.append(f"{run[0]}..{run[-1]}")
            else:
                partes.extend(str(r) for r in run)
        return ",".join(partes)

    # ---- detector de aliases ----

    def _detectar_aliases(self, runs_por_linha: list[list[list[int]]]
                            ) -> dict:
        """Encontra sufixos comuns entre runs-de-refs.

        Greedy correto:
        1. Coleta SUFIXOS contiguos (K>=3) de cada run
        2. Para cada sufixo candidato, calcula net considerando:
           - economia por uso: Lt_serial - (1 + len(str(N)))
           - custo decl: Lt_serial + (2 + len(str(N))) + 1 (newline)
        3. Seleciona o de maior net, REMOVE ocorrencias usadas das
           runs (marca como "consumido"), repete
        4. Para quando nenhum candidato tem net > 0

        Retorna: alias_para_tupla[tuple] = id (1, 2, ...)
        """
        # Coletar todas as runs com pelo menos 3 refs
        runs_flat = []  # lista de tuplas (uma por ocorrencia)
        for runs in runs_por_linha:
            for r in runs:
                if len(r) >= 3:
                    runs_flat.append(tuple(r))

        alias_para_tupla = {}
        proximo_id = 1

        while proximo_id <= 9:  # limitar a 9 (1-digit ids)
            # contar sufixos disponiveis
            sufixos = Counter()
            for tupla in runs_flat:
                for k in range(3, len(tupla) + 1):
                    sufixos[tupla[-k:]] += 1

            # selecionar melhor net
            melhor_net = 0
            melhor_tupla = None
            melhor_R = 0
            for tupla, R in sufixos.items():
                if R < 2:
                    continue
                Lt_serial = len(self._emit_refs_range(list(tupla)))
                n_tam = len(str(proximo_id))
                economia_uso = Lt_serial - 1 - n_tam
                custo_decl = Lt_serial + 2 + n_tam + 1  # +1 newline
                net = R * economia_uso - custo_decl
                if net > melhor_net:
                    melhor_net = net
                    melhor_tupla = tupla
                    melhor_R = R

            if melhor_tupla is None:
                break  # nenhum mais compensa

            alias_para_tupla[melhor_tupla] = proximo_id
            proximo_id += 1

            # remover esse sufixo das runs (consumido)
            # se a run terminava com esse sufixo, ela "vira" o que
            # sobra antes do sufixo (que pode ser vazio ou ter <3
            # refs, ai' nao gera mais candidato)
            nova_runs_flat = []
            k_sufixo = len(melhor_tupla)
            for tupla in runs_flat:
                if (len(tupla) >= k_sufixo
                        and tupla[-k_sufixo:] == melhor_tupla):
                    prefixo = tupla[:-k_sufixo]
                    if len(prefixo) >= 3:
                        nova_runs_flat.append(prefixo)
                    # senao descarta — prefixo curto demais
                else:
                    nova_runs_flat.append(tupla)
            runs_flat = nova_runs_flat

        return alias_para_tupla

    def _aplicar_alias(self, refs: list[int],
                        alias_para_tupla: dict) -> str:
        """Serializa refs aplicando alias quando ECONOMIZA bytes
        (compara custo com vs sem alias para cada candidato)."""
        # baseline: serializacao com range
        baseline = self._emit_refs_range(refs)
        melhor = baseline

        n = len(refs)
        # tenta cada sufixo candidato
        for k in range(n, 1, -1):
            sufixo = tuple(refs[-k:])
            if sufixo in alias_para_tupla:
                alias_id = alias_para_tupla[sufixo]
                prefixo_refs = refs[:n - k]
                if prefixo_refs:
                    pre = self._emit_refs_range(prefixo_refs)
                    candidato = f"{pre},${alias_id}"
                else:
                    candidato = f"${alias_id}"
                if len(candidato) < len(melhor):
                    melhor = candidato
        return melhor

    # ---- encode ----

    def encode(self, linhas_originais, strings_unicas,
                tokens_por_string, header):
        quebras = self._coletar_quebras(strings_unicas, tokens_por_string)
        unica_to_eid = {s: i + 1 for i, s in enumerate(strings_unicas)}

        # FASE 1: gerar linhas como M1.E faria, mas COLETAR runs de
        # refs por linha para depois detectar aliases
        frags_por_no = {}
        proximo_idx = 1
        eid_emitido = set()
        linhas_dados = []  # lista de (s_run, count, elementos)

        for s_run, count in self._rle_adjacente(linhas_originais):
            eid = unica_to_eid[s_run]
            if eid not in eid_emitido:
                s = strings_unicas[eid - 1]
                tokens = tokens_por_string[eid - 1]
                qa = quebras[eid]
                frags_por_no[eid] = []
                elementos = []
                pos = 0
                for tok in tokens:
                    if isinstance(tok, TokLit):
                        sl, el = pos, pos + len(tok.text)
                        qs = sorted(q for q in qa if sl < q < el)
                        pts = [sl] + qs + [el]
                        for i in range(len(pts) - 1):
                            a, b = pts[i], pts[i + 1]
                            idx = proximo_idx
                            proximo_idx += 1
                            frags_por_no[eid].append((a, b, idx))
                            elementos.append(('lit', s[a:b]))
                        pos = el
                    elif isinstance(tok, TokRefPref):
                        herdados = [(a, b, idx)
                                     for (a, b, idx) in frags_por_no[tok.string_id]
                                     if a < tok.length and b <= tok.length]
                        for (a, b, idx) in herdados:
                            frags_por_no[eid].append((pos + a, pos + b, idx))
                            elementos.append(('ref', idx))
                        pos += tok.length
                    else:
                        s_ref = strings_unicas[tok.string_id - 1]
                        rs = len(s_ref) - tok.length
                        herdados = [(a, b, idx)
                                     for (a, b, idx) in frags_por_no[tok.string_id]
                                     if a >= rs and b > rs]
                        for (a, b, idx) in herdados:
                            frags_por_no[eid].append(
                                (pos + (a - rs), pos + (b - rs), idx))
                            elementos.append(('ref', idx))
                        pos += tok.length
                eid_emitido.add(eid)
                linhas_dados.append((s_run, count, elementos, eid, False))
            else:
                linhas_dados.append((s_run, count, None, eid, True))

        # FASE 2: coletar runs de refs por linha (para detector)
        runs_por_linha = []
        for s_run, count, elementos, eid, is_rep in linhas_dados:
            if is_rep or elementos is None:
                continue
            runs = []
            cur = []
            for elem in elementos:
                if elem[0] == 'ref':
                    cur.append(elem[1])
                else:
                    if cur:
                        runs.append(cur)
                        cur = []
            if cur:
                runs.append(cur)
            runs_por_linha.append(runs)

        # FASE 3: detector de aliases
        alias_para_tupla = self._detectar_aliases(runs_por_linha)

        # FASE 4: serializar com aliases aplicados
        body_linhas = []
        for s_run, count, elementos, eid, is_rep in linhas_dados:
            if is_rep:
                linha_resto = f"^{eid}"
            else:
                partes = []
                prev_tipo = None
                prev_lit_termina_seq_digito = False
                i = 0
                n_elem = len(elementos)
                while i < n_elem:
                    tipo, val = elementos[i]
                    if tipo == 'lit':
                        if prev_tipo == 'lit':
                            partes.append('*')
                        emitido, term_seq = self._escape_e_termina_em_digito(val)
                        partes.append(emitido)
                        prev_lit_termina_seq_digito = term_seq
                        prev_tipo = 'lit'
                        i += 1
                    else:
                        refs = []
                        while i < n_elem and elementos[i][0] == 'ref':
                            refs.append(elementos[i][1])
                            i += 1
                        if prev_lit_termina_seq_digito:
                            partes.append('*')
                            prev_lit_termina_seq_digito = False
                        partes.append(self._aplicar_alias(refs, alias_para_tupla))
                        prev_tipo = 'ref'
                linha_resto = ''.join(partes)

            if count > 1:
                body_linhas.append(f"*{count}|{linha_resto}")
            else:
                body_linhas.append(linha_resto)

        # FASE 5: emitir preambulo de aliases + body
        # Preambulo entre `[` e primeiro elemento
        preambulo = []
        for tupla, alias_id in sorted(alias_para_tupla.items(),
                                        key=lambda x: x[1]):
            tupla_serial = self._emit_refs_range(list(tupla))
            preambulo.append(f"${alias_id}={tupla_serial}")

        if preambulo:
            return "\n".join(["[", *preambulo, *body_linhas, "]"]) + "\n"
        else:
            return "\n".join(["[", *body_linhas, "]"]) + "\n"

    # ---- decode ----

    def _expandir_alias_em_refs(self, refs_str, aliases):
        """Substitui `$N` por refs expandidas. Retorna lista de
        tokens de refs (ints) ou (a, b) para range."""
        # split por virgula, mas alias pode estar misturado
        partes = refs_str.split(',')
        resultado = []
        for p in partes:
            if not p:
                continue
            if p.startswith('$'):
                alias_id = int(p[1:])
                resultado.extend(aliases[alias_id])
            elif '..' in p:
                a_str, b_str = p.split('..')
                resultado.append((int(a_str), int(b_str)))  # range
            else:
                resultado.append(int(p))
        return resultado

    def _parse_decl(self, resto, frags, proximo_idx_ref, aliases):
        partes = []
        i = 0
        n = len(resto)
        while i < n:
            ch = resto[i]
            if ch == '*':
                i += 1
            elif ch == '$':
                # alias: le digitos apos `$`
                j = i + 1
                while j < n and resto[j].isdigit():
                    j += 1
                alias_id = int(resto[i + 1:j])
                # alias pode ser seguido de `,` + mais refs
                # Conta como inicio de seq de refs
                # Vou coletar a sequencia inteira aqui
                refs_str = resto[i:j]
                # continua se houver `,...` apos
                k = j
                while k < n:
                    c = resto[k]
                    if c == ',':
                        k += 1
                    elif c.isdigit() or c == '$':
                        if c == '$':
                            k += 1
                            while k < n and resto[k].isdigit():
                                k += 1
                        else:
                            while k < n and resto[k].isdigit():
                                k += 1
                            # range?
                            if k + 1 < n and resto[k] == '.' and resto[k+1] == '.':
                                k += 2
                                while k < n and resto[k].isdigit():
                                    k += 1
                    else:
                        break
                refs_str = resto[i:k]
                # expandir
                expandido = self._expandir_alias_em_refs(refs_str, aliases)
                for item in expandido:
                    if isinstance(item, tuple):
                        a, b = item
                        for v in range(a, b + 1):
                            partes.append(frags[v])
                    else:
                        partes.append(frags[item])
                i = k
            elif ch.isdigit():
                # refs: igual M1.E (range, `..`)
                j = i
                while j < n:
                    c = resto[j]
                    if c.isdigit() or c == ',':
                        j += 1
                    elif c == '.' and j + 1 < n and resto[j + 1] == '.':
                        j += 2
                    elif c == '$':
                        # parou em `$` — alias misturado em refs
                        j += 1
                        while j < n and resto[j].isdigit():
                            j += 1
                    else:
                        break
                refs_str = resto[i:j]
                # Pode conter aliases inline
                if '$' in refs_str:
                    expandido = self._expandir_alias_em_refs(refs_str, aliases)
                    for item in expandido:
                        if isinstance(item, tuple):
                            a, b = item
                            for v in range(a, b + 1):
                                partes.append(frags[v])
                        else:
                            partes.append(frags[item])
                else:
                    for r in refs_str.split(','):
                        if not r:
                            continue
                        if '..' in r:
                            a, b = r.split('..')
                            for v in range(int(a), int(b) + 1):
                                partes.append(frags[v])
                        else:
                            partes.append(frags[int(r)])
                i = j
            else:
                # literal com escape escopo
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
                    elif c.isdigit() or c == '*' or c == '$':
                        break
                    else:
                        buf.append(c)
                        i += 1
                texto = ''.join(buf)
                frags[proximo_idx_ref[0]] = texto
                partes.append(texto)
                proximo_idx_ref[0] += 1
        return ''.join(partes)

    def _parse_alias_decl(self, linha):
        """Parse `$N=<tupla>` → (N, lista de ints)."""
        eq = linha.find('=')
        n = int(linha[1:eq])
        resto = linha[eq + 1:]
        refs = []
        for p in resto.split(','):
            if '..' in p:
                a, b = p.split('..')
                for v in range(int(a), int(b) + 1):
                    refs.append(v)
            else:
                refs.append(int(p))
        return n, refs

    def decode(self, tcf_text):
        frags = {}
        proximo_idx_ref = [1]
        nos_decl = []
        saida = []
        aliases = {}  # id → list of ints

        for raw in tcf_text.splitlines():
            linha = raw.strip()
            if not linha or linha in ("[", "]"):
                continue

            # detectar declaracao de alias
            if linha.startswith('$') and '=' in linha and '|' not in linha[:linha.find('=')]:
                n, refs = self._parse_alias_decl(linha)
                aliases[n] = refs
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
                s_no = self._parse_decl(resto, frags, proximo_idx_ref, aliases)
                nos_decl.append(s_no)

            saida.extend([s_no] * count)
        return saida
