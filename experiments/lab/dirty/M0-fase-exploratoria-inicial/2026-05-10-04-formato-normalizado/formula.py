"""Previsao simbolica do tamanho de cada serializacao por camada.

Decomposicao em 3 camadas (a 4a, comentarios, nao existe nestes formatos
normalizados):

    - macro   = bytes de marcadores de secao (<patricia>, <body>, ...)
    - ref     = bytes de marcadores de referencia (sintaxe + ids + counts
                + aspas + indentacao + newline)
    - dados   = bytes dentro das aspas (fragmento de cada no, contado 1x)

prever_*  -> reproduz o encoder simbolicamente, retorna (macro, ref, dados).
decompor  -> mede o texto real e devolve as 3 camadas.

Se prever == decompor, o modelo de camadas esta consistente com o encoder.
"""

from patricia import No


# --- Decomposicao por medicao direta no texto encodado ---

def decompor(tcf_text: str) -> tuple[int, int, int]:
    """Retorna (chars_macro, chars_ref, chars_dados).

    Macro = linhas <patricia>, </patricia>, <body>, </body> com newlines.
    Dados = caracteres dentro de aspas duplas.
    Ref = todo o resto.
    """
    macro_lines = {"<patricia>", "</patricia>", "<body>", "</body>"}
    chars_macro = 0
    chars_dados = 0
    chars_ref = 0

    for raw in tcf_text.splitlines(keepends=True):
        stripped = raw.strip()
        if stripped in macro_lines:
            chars_macro += len(raw)
            continue
        in_quotes = False
        for ch in raw:
            if ch == '"':
                chars_ref += 1
                in_quotes = not in_quotes
            elif in_quotes:
                chars_dados += 1
            else:
                chars_ref += 1
    return chars_macro, chars_ref, chars_dados


# --- Previsao simbolica (reimplementa encoder, contando chars) ---

NL = 1  # newline


def _len_decl_folha_sep(eid: int, frag: str) -> int:
    # f'  no{eid} = folha "{frag}"\n'
    return len(f'  no{eid} = folha ""') + len(frag) + NL


def _len_decl_filho_sep(eid: int, eid_pai: int, frag: str) -> int:
    return len(f'  no{eid} = filho_de(no{eid_pai}) + ""') + len(frag) + NL


def _len_ref(count: int, eid: int) -> int:
    if count == 1:
        return len(f"  ref:no{eid}") + NL
    return len(f"  {count}x ref:no{eid}") + NL


def _len_decl_folha_inl_occ(eid: int, count: int, frag: str) -> int:
    if count == 1:
        return len(f'  no{eid}: folha ""') + len(frag) + NL
    return len(f'  no{eid}: {count}x folha ""') + len(frag) + NL


def _len_decl_filho_inl_occ(eid: int, count: int, eid_pai: int, frag: str) -> int:
    if count == 1:
        return len(f'  no{eid}: filho_de(no{eid_pai}) + ""') + len(frag) + NL
    return (
        len(f'  no{eid}: {count}x filho_de(no{eid_pai}) + ""')
        + len(frag) + NL
    )


def _len_decl_folha_inl_tardia(eid: int, frag: str) -> int:
    return len(f'  no{eid}: decl folha ""') + len(frag) + NL


def _len_decl_filho_inl_tardia(eid: int, eid_pai: int, frag: str) -> int:
    return len(f'  no{eid}: decl filho_de(no{eid_pai}) + ""') + len(frag) + NL


def prever_separado(nos: dict[int, No],
                    body_rle: list[tuple[int, int]]) -> tuple[int, int, int]:
    macro = (len("<patricia>") + NL + len("</patricia>") + NL
             + len("<body>") + NL + len("</body>") + NL)

    ref = 0
    dados = 0
    for nid in sorted(nos):
        n = nos[nid]
        dados += len(n.fragmento)
        # +2 chars de aspas dentro do "ref" — como decompor conta aspas em ref,
        # nao aqui (esta dentro da string de marcador). Padrao consistente.
        if n.pai_id is None:
            ref += _len_decl_folha_sep(nid, n.fragmento) - len(n.fragmento)
        else:
            ref += _len_decl_filho_sep(nid, n.pai_id, n.fragmento) - len(n.fragmento)

    for no_id, count in body_rle:
        ref += _len_ref(count, no_id)

    return macro, ref, dados


def prever_inline(nos: dict[int, No],
                  body_rle: list[tuple[int, int]]) -> tuple[int, int, int]:
    macro = len("<body>") + NL + len("</body>") + NL

    proximo_emit = 1
    map_emit: dict[int, int] = {}
    declarado: set[int] = set()

    def get_eid(nid: int) -> int:
        nonlocal proximo_emit
        if nid not in map_emit:
            map_emit[nid] = proximo_emit
            proximo_emit += 1
        return map_emit[nid]

    ref = 0
    dados = 0

    for no_id, count in body_rle:
        eid = get_eid(no_id)
        if eid not in declarado:
            n = nos[no_id]
            dados += len(n.fragmento)
            if n.pai_id is None:
                ref += (_len_decl_folha_inl_occ(eid, count, n.fragmento)
                        - len(n.fragmento))
            else:
                eid_pai = get_eid(n.pai_id)
                ref += (_len_decl_filho_inl_occ(eid, count, eid_pai, n.fragmento)
                        - len(n.fragmento))
            declarado.add(eid)
        else:
            ref += _len_ref(count, eid)

    while True:
        pendentes = [(nid, eid) for nid, eid in map_emit.items()
                     if eid not in declarado]
        if not pendentes:
            break
        pendentes.sort(key=lambda x: x[1])
        for nid, eid in pendentes:
            n = nos[nid]
            dados += len(n.fragmento)
            if n.pai_id is None:
                ref += _len_decl_folha_inl_tardia(eid, n.fragmento) - len(n.fragmento)
            else:
                eid_pai = get_eid(n.pai_id)
                ref += (_len_decl_filho_inl_tardia(eid, eid_pai, n.fragmento)
                        - len(n.fragmento))
            declarado.add(eid)

    return macro, ref, dados
