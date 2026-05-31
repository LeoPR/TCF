"""Analise: os pref/suf texts escolhidos pela decomposicao do exp 10
sao declarados como 'decl folha "X"' (folha simples) no encode atual.
Mas eles podem TER PAI na arvore Patricia. Esse pai e ignorado.

Exemplo (D4 do exp 10):
  no2 = decl folha "https://api.example.com/v1/users/"      # ignora pai
  no4 = decl folha "https://api.example.com/v1/orders/10"   # mesmo pai!
  no8 = decl folha "https://api.example.com/v1/products/5"  # mesmo pai!

Se a decl fosse hierarquica (estilo exp 05/06 para folhas):
  no_avo = decl folha "https://api.example.com/v1/"
  no2 = decl filho_de(no_avo) + "users/"
  no4 = decl filho_de(no_avo) + "orders/10"
  no8 = decl filho_de(no_avo) + "products/5"

Aqui medimos quantos pref/suf texts caem nessa situacao e estimamos
ganho/custo.
"""

from dataclasses import dataclass

from arvore_bidir import Decomposicao
from patricia import No, texto_completo


@dataclass
class TextoComPai:
    texto: str               # texto completo (do pref ou do suf, natural)
    pai_texto: str           # texto do pai imediato na arvore Patricia
    extra: str               # parte propria (texto sem o pai)
    eid_no_pai: int          # id do nó pai na arvore Patricia
    n_strings: int           # quantas strings usam este texto como pref/suf


def _cadeia_ancestrais_forward(eid: int, arvore: dict[int, No]) -> list[tuple[int, str]]:
    """[(pai_eid, pai_texto), ...] do pai imediato a raiz, em arvore forward."""
    no = arvore[eid]
    res = []
    while no.pai_id is not None:
        t = texto_completo(no.pai_id, arvore)
        res.append((no.pai_id, t))
        no = arvore[no.pai_id]
    return res


def _localizar_eid_por_texto_completo(texto: str,
                                       arvore: dict[int, No]) -> int | None:
    """Acha qual no na arvore reconstrutroi exatamente o texto dado.
    Retorna None se nenhum no satisfaz.
    """
    for eid in arvore:
        if texto_completo(eid, arvore) == texto:
            return eid
    return None


def analisar_prefs(decomps: dict[str, Decomposicao],
                    fwd_arvore: dict[int, No]) -> list[TextoComPai]:
    """Para cada pref_text unico nas decomposicoes, ve se ele tem pai
    na arvore forward.
    """
    contagem_prefs: dict[str, int] = {}
    for d in decomps.values():
        if d.prefix_text:
            contagem_prefs[d.prefix_text] = contagem_prefs.get(d.prefix_text, 0) + 1

    resultado = []
    for pref_text, n in contagem_prefs.items():
        eid = _localizar_eid_por_texto_completo(pref_text, fwd_arvore)
        if eid is None:
            continue
        no = fwd_arvore[eid]
        if no.pai_id is None:
            continue  # nao tem pai
        pai_texto = texto_completo(no.pai_id, fwd_arvore)
        extra = pref_text[len(pai_texto):]
        resultado.append(TextoComPai(
            texto=pref_text, pai_texto=pai_texto, extra=extra,
            eid_no_pai=no.pai_id, n_strings=n,
        ))
    return resultado


def analisar_sufs(decomps: dict[str, Decomposicao],
                   rev_arvore: dict[int, No]) -> list[TextoComPai]:
    """Para cada suf_text unico, ve se na arvore reverse (invertida) ele
    tem pai. Trabalha em texto natural (des-invertido).
    """
    contagem_sufs: dict[str, int] = {}
    for d in decomps.values():
        if d.suffix_text:
            contagem_sufs[d.suffix_text] = contagem_sufs.get(d.suffix_text, 0) + 1

    resultado = []
    for suf_text, n in contagem_sufs.items():
        suf_inv = suf_text[::-1]
        eid = _localizar_eid_por_texto_completo(suf_inv, rev_arvore)
        if eid is None:
            continue
        no = rev_arvore[eid]
        if no.pai_id is None:
            continue
        pai_inv = texto_completo(no.pai_id, rev_arvore)
        pai_texto = pai_inv[::-1]   # natural
        # No reverse, o "extra" (filho) vem ANTES do pai no texto natural:
        # filho_natural + pai_natural = suf_text
        extra = suf_text[:len(suf_text) - len(pai_texto)]
        resultado.append(TextoComPai(
            texto=suf_text, pai_texto=pai_texto, extra=extra,
            eid_no_pai=no.pai_id, n_strings=n,
        ))
    return resultado


# Estimativas de bytes — sintaxe do exp 10
def estimar_economia(items: list[TextoComPai], compartilhamento: bool) -> dict:
    """compartilhamento=True: assume que pais que aparecem em multiplos
    items podem ser declarados UMA VEZ e reusados. Mais realista.
    """
    # Por item: bytes antes (decl folha simples) vs depois (decl filho_de)
    bytes_antes_total = 0
    bytes_depois_total = 0

    # Pais unicos para calcular custo de decl (uma vez por pai unico
    # se compartilhamento=True, ou uma vez por item se False)
    pais_unicos: set[str] = set()
    custo_decl_pai_total = 0

    for item in items:
        # Antes: 'decl folha "TEXTO"'
        bytes_antes_total += len(f'decl folha "{item.texto}"')
        # Depois: 'decl filho_de(noPP) + "EXTRA"'
        # Assumindo eid do pai ~2 chars
        bytes_depois_total += len(f'decl filho_de(no99) + "{item.extra}"')

        if compartilhamento and item.pai_texto in pais_unicos:
            continue
        pais_unicos.add(item.pai_texto)
        # Decl do pai: precisa aparecer em algum lugar.
        # Se for top-level (sem pai do pai), eh 'decl folha "PAI"'
        # Custo: '  noPP: decl folha "PAI"\n' ~ 21 + len(pai)
        # Mas se for embutido na 1a ocorrencia, o overhead eh menor.
        # Aproximacao: custo da decl do pai = len(pai_texto) + 25
        custo_decl_pai_total += 25 + len(item.pai_texto)

    return {
        "bytes_antes_total": bytes_antes_total,
        "bytes_depois_total": bytes_depois_total,
        "custo_decl_pais": custo_decl_pai_total,
        "delta_liquido": (bytes_depois_total + custo_decl_pai_total) - bytes_antes_total,
        "n_items": len(items),
        "n_pais_unicos": len(pais_unicos),
    }
