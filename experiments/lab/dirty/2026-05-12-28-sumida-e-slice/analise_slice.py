"""Analisador puro de potencial de slice arbitrario.

Identifica oportunidades de **slice arbitrario** — substring no
meio de um no anterior que aparece dentro de um literal misto
(letras + digitos juntos).

Hoje os tokens do exp 16 sao:
  TokLit(text)              literal
  TokRefPref(eid, K)        primeiros K de eid (slice [0:K])
  TokRefSuf(eid, K)         ultimos K de eid (slice [-K:])

A semantica **nao capturada**: TokRefSlice(eid, a, b) que pega
slice arbitrario [a:b] do meio de eid.

Este analisador procura, para cada literal misto (letras+
digitos), substrings que aparecem em algum no anterior. Se
encontradas, calcula o ganho teorico se slice arbitrario fosse
implementado.

Sem implementar encoder — apenas mede potencial.
"""

import csv
from collections import OrderedDict
from pathlib import Path

from online import processar, reconstroi, TokLit, TokRefPref, TokRefSuf

BASE = Path(__file__).parent

MIN_SLICE = 3  # tamanho minimo para slice valer a pena


def ler_csv(path):
    with path.open(encoding="utf-8") as f:
        r = csv.reader(f)
        next(r)  # header
        return [row[0] for row in r if row]


def coletar_quebras(unicas, tokens_por_string):
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


def fragmentos_literais(unicas, tokens_por_string, quebras):
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


def maior_substring_em(texto, fonte):
    """Maior substring contigua de texto que esta em fonte.
    Retorna (start_em_texto, length, start_em_fonte) ou None.
    """
    melhor = None
    for length in range(len(texto), MIN_SLICE - 1, -1):
        for i in range(len(texto) - length + 1):
            sub = texto[i:i + length]
            j = fonte.find(sub)
            if j >= 0:
                return (i, length, j)
        # so testa o maior comprimento que ainda tem chance
        if melhor:
            break
    return melhor


def analisar_slice(unicas, frags):
    """Para cada fragmento misto (letras+digitos), procura
    substring em qualquer no ANTERIOR (eid menor)."""
    oportunidades = []
    for eid, a, b, texto in frags:
        # Foco em literais mistos: tem letra E digito
        tem_letra = any(c.isalpha() for c in texto)
        tem_digito = any(c.isdigit() for c in texto)
        if not (tem_letra and tem_digito):
            continue
        # Buscar em nos anteriores
        for ref_eid in range(1, eid):
            fonte = unicas[ref_eid - 1]
            r = maior_substring_em(texto, fonte)
            if r is None:
                continue
            i_tex, length, i_src = r
            oportunidades.append({
                'eid': eid,
                'frag_range': (a, b),
                'texto': texto,
                'ref_eid': ref_eid,
                'i_em_texto': i_tex,
                'length': length,
                'i_em_fonte': i_src,
                'substring': fonte[i_src:i_src + length],
            })
            break  # so registra a primeira fonte que serve
    return oportunidades


def rodar_em(nome):
    linhas = ler_csv(BASE / "data" / f"{nome}.csv")
    seen = OrderedDict()
    for s in linhas:
        seen[s] = True
    unicas = list(seen.keys())
    tokens, _ = processar(unicas, min_len=3)
    for s, t in zip(unicas, tokens):
        assert reconstroi(t, unicas) == s

    quebras = coletar_quebras(unicas, tokens)
    frags = fragmentos_literais(unicas, tokens, quebras)

    print(f"\n{'=' * 70}")
    print(f"=== Dataset: {nome} ===")
    print(f"{'=' * 70}")
    print(f"Fragmentos literais: {len(frags)}")
    print(f"min_slice: {MIN_SLICE}")
    print()

    mistos = [f for f in frags
              if any(c.isalpha() for c in f[3])
              and any(c.isdigit() for c in f[3])]
    print(f"Fragmentos mistos (letras+digitos): {len(mistos)}")
    for f in mistos:
        print(f"  eid={f[0]} [{f[1]}:{f[2]}] {f[3]!r}")
    print()

    # Tambem analisa fragmentos puros que podem ter substring em outros
    # nos (pode revelar potencial alem dos mistos)
    oport = analisar_slice(unicas, frags)
    print(f"Oportunidades de slice (>= {MIN_SLICE} chars):")
    if not oport:
        print("  (nenhuma)")
    for o in oport:
        ganho_potencial = o['length'] - 1
        print(f"  eid={o['eid']} literal {o['texto']!r}:")
        print(f"    substring {o['substring']!r} ({o['length']}c) "
              f"em eid={o['ref_eid']} pos {o['i_em_fonte']}")
        print(f"    no literal, pos {o['i_em_texto']}..{o['i_em_texto']+o['length']}")
        print(f"    ganho potencial: {o['length']} chars -> 1 ref "
              f"(~{ganho_potencial} bytes brutos)")

    if oport:
        chars_substituiveis = sum(o['length'] for o in oport)
        print()
        print(f"  Total chars subst.: {chars_substituiveis}")
        print(f"  Refs novas: {len(oport)}")
        print(f"  Ganho bruto: {chars_substituiveis - len(oport)} chars")


def main():
    for nome in ["emails-quote-id", "stress-substring-meio"]:
        rodar_em(nome)


if __name__ == "__main__":
    main()
