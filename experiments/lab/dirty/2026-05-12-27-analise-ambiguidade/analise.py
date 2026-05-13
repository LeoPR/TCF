"""Analisador puro de ambiguidade — Etapa 1 do flow semantico.

Nao emite TCF. Apenas classifica cada char de cada literal
gerado pelo algoritmo do exp 16 em 3 categorias:

  A (livre)           — char nunca e' marcador em v3
  B (contexto resolve) — char e' marcador em alguma posicao,
                        mas no contexto atual nao aciona o parser
  C (conflito real)    — char aciona o parser no contexto atual,
                        precisa marcacao ou estrategia alternativa

A sintaxe-base de analise e' **v3** (sem aspas, sem escape), a
mais minimalista. Marcadores de v3 reconhecidos:

  0-9   refs (dispara modo refs no parser)
  *     separador entre literais consecutivos
  ,     separador entre refs (em sequencia de refs)
  ^     uso de no (so' no inicio absoluto da linha)
  |     RLE bar (so' apos `*K` no inicio)
  [, ]  macros body (so' em linhas isoladas)

A raiz dos tokens e o `online.py` do exp 16 — copiado para esta
pasta sem alteracao. Este experimento e' analise pura, nao
substitui o encoder.
"""

import csv
from collections import OrderedDict
from pathlib import Path

from online import processar, reconstroi, TokLit, TokRefPref, TokRefSuf

BASE = Path(__file__).parent


def classificar_char(c: str) -> tuple[str, str]:
    """Classificacao por char isolado (sem contexto de posicao).

    Casos B podem ser refinados com contexto na proxima passada.
    """
    if c.isdigit():
        return 'C', 'digito conflita com ref'
    if c == '*':
        return 'C', '* conflita com separador'
    if c == ',':
        return 'B', ', conflita so se cercado de refs'
    if c == '^':
        return 'B', '^ so e marcador no inicio absoluto da linha'
    if c == '|':
        return 'B', '| so em RLE prefix'
    if c in '[]':
        return 'B', f'`{c}` so em linha isolada como macro'
    return 'A', 'char livre em v3'


def coletar_quebras(unicas, tokens_por_string):
    """Reproduz a logica de quebras das sintaxes compactas — para
    obter o conjunto de fragmentos literais a analisar."""
    quebras = {eid: set() for eid in range(1, len(unicas) + 1)}
    for tokens in tokens_por_string:
        for tok in tokens:
            if isinstance(tok, TokRefPref):
                quebras[tok.string_id].add(tok.length)
            elif isinstance(tok, TokRefSuf):
                s_ref = unicas[tok.string_id - 1]
                quebras[tok.string_id].add(len(s_ref) - tok.length)
    # propagacao inversa
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


def fragmentos_literais(unicas, tokens_por_string, quebras):
    """Para cada eid, retorna lista de fragmentos literais como
    (eid, range_start, range_end, texto). Apenas o que vem de
    TokLit (nao herdados de refs).
    """
    out = []
    for eid, tokens in enumerate(tokens_por_string, start=1):
        s = unicas[eid - 1]
        qa = quebras[eid]
        pos = 0
        for tok in tokens:
            if isinstance(tok, TokLit):
                sl, el = pos, pos + len(tok.text)
                qs = sorted(q for q in qa if sl < q < el)
                pts = [sl] + qs + [el]
                for i in range(len(pts) - 1):
                    a, b = pts[i], pts[i + 1]
                    out.append((eid, a, b, s[a:b]))
                pos = el
            else:
                pos += tok.length
    return out


def ler_csv(path):
    with path.open(encoding="utf-8") as f:
        r = csv.reader(f)
        next(r)  # header
        return [row[0] for row in r if row]


def analisar(linhas):
    seen = OrderedDict()
    for s in linhas:
        seen[s] = True
    unicas = list(seen.keys())
    tokens, _ = processar(unicas, min_len=3)
    for s, t in zip(unicas, tokens):
        assert reconstroi(t, unicas) == s

    quebras = coletar_quebras(unicas, tokens)
    frags = fragmentos_literais(unicas, tokens, quebras)

    # Classificar cada char de cada fragmento
    detalhes = []
    contagem_global = {'A': 0, 'B': 0, 'C': 0}
    contagem_por_frag = []
    for eid, a, b, texto in frags:
        chars_class = []
        contagem_frag = {'A': 0, 'B': 0, 'C': 0}
        for c in texto:
            cat, motivo = classificar_char(c)
            chars_class.append((c, cat, motivo))
            contagem_frag[cat] += 1
            contagem_global[cat] += 1
        detalhes.append({
            'eid': eid,
            'range': (a, b),
            'texto': texto,
            'chars': chars_class,
            'contagem': contagem_frag,
        })
        contagem_por_frag.append(contagem_frag)

    return {
        'unicas': unicas,
        'tokens': tokens,
        'frags': frags,
        'detalhes': detalhes,
        'contagem_global': contagem_global,
        'contagem_por_frag': contagem_por_frag,
    }


def imprimir_relatorio(nome_dataset, ana):
    print("=" * 80)
    print(f"ANALISE DE AMBIGUIDADE — dataset: {nome_dataset}")
    print("=" * 80)
    print(f"Strings unicas: {len(ana['unicas'])}")
    print(f"Fragmentos literais: {len(ana['frags'])}")
    print()
    print("--- Marcadores de v3 reconhecidos ---")
    print("  0-9   refs")
    print("  *     separador entre literais")
    print("  ,     separador entre refs")
    print("  ^     uso de no (so' inicio linha)")
    print("  |     RLE bar (so' RLE prefix)")
    print("  [, ]  macros body (so' linha isolada)")
    print()

    print("--- Detalhes por fragmento ---")
    for d in ana['detalhes']:
        eid = d['eid']
        rng = d['range']
        txt = d['texto']
        cont = d['contagem']
        chars_str = ' '.join(
            f"{c!r}/{cat}" for c, cat, _ in d['chars']
        )
        flag = ''
        if cont['C'] > 0:
            flag = f"  *** {cont['C']} char(s) C ***"
        print(f"  eid={eid} [{rng[0]}:{rng[1]}] {txt!r:<25}  "
              f"A={cont['A']} B={cont['B']} C={cont['C']}{flag}")
        # Detalhe char por char so' se ha C
        if cont['C'] > 0:
            for c, cat, motivo in d['chars']:
                if cat == 'C':
                    print(f"      char {c!r}: {cat} — {motivo}")

    print()
    print("--- Contagem global ---")
    g = ana['contagem_global']
    total = sum(g.values())
    print(f"  Total de chars em literais: {total}")
    print(f"  A (livre):           {g['A']:>4}  ({g['A']/total*100:>5.1f}%)")
    print(f"  B (contexto resolve): {g['B']:>4}  ({g['B']/total*100:>5.1f}%)")
    print(f"  C (conflito real):    {g['C']:>4}  ({g['C']/total*100:>5.1f}%)")

    print()
    print("--- Distribuicao de C por fragmento ---")
    dist = {}
    for c in ana['contagem_por_frag']:
        k = c['C']
        dist[k] = dist.get(k, 0) + 1
    for k in sorted(dist):
        marca = " (raw, sem marcacao)" if k == 0 else ""
        print(f"  K={k} chars C: {dist[k]:>3} fragmento(s){marca}")

    print()
    print("--- Estimativa de custo de marcacao ---")
    n_C_total = g['C']
    n_frags_com_C = sum(1 for c in ana['contagem_por_frag'] if c['C'] > 0)
    custo_escape = n_C_total  # +1 byte por char C
    custo_aspas = n_frags_com_C * 2  # +2 bytes por fragmento ambiguo
    print(f"  Estrategia escape (\\X): +{n_C_total} bytes total")
    print(f"  Estrategia aspas ('X'):  +{custo_aspas} bytes total "
          f"({n_frags_com_C} fragmentos × 2)")
    if custo_escape < custo_aspas:
        print(f"  -> Escape vence por {custo_aspas - custo_escape} bytes")
    elif custo_aspas < custo_escape:
        print(f"  -> Aspas vence por {custo_escape - custo_aspas} bytes")
    else:
        print(f"  -> Empate")

    # Decisao otima por fragmento (escolha local)
    custo_otimo = 0
    for c in ana['contagem_por_frag']:
        k = c['C']
        if k == 0:
            custo_otimo += 0
        elif k == 1:
            # escape (+1) vs aspas (+2) — escape vence
            custo_otimo += 1
        else:
            # aspas (+2) vence ou empata
            custo_otimo += 2
    print(f"  Estrategia mista (otimo por frag): +{custo_otimo} bytes total")

    print()
    print("--- Lista de chars C distintos ---")
    chars_C_distintos = {}
    for d in ana['detalhes']:
        for c, cat, _ in d['chars']:
            if cat == 'C':
                chars_C_distintos[c] = chars_C_distintos.get(c, 0) + 1
    for c, n in sorted(chars_C_distintos.items()):
        print(f"  {c!r}: {n} ocorrencia(s)")


def main():
    nome = "emails-quote-id"
    linhas = ler_csv(BASE / "data" / f"{nome}.csv")
    ana = analisar(linhas)
    imprimir_relatorio(nome, ana)


if __name__ == "__main__":
    main()
