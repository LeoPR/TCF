"""Patricia com logging detalhado por iteracao.

Mesmo algoritmo do exp 02-08 (greedy, mais longo vence). A diferenca
e que cada iteracao registra:
  - Quais nos top-level existiam no inicio
  - Quais prefixos candidatos foram contados (top 15 por len + count)
  - Qual foi escolhido e por que
  - Quais folhas foram absorvidas

Retorna (nos_atualizado, log_textual).
"""

from collections import Counter
from dataclasses import dataclass
from typing import Optional

MIN_PREFIXO = 3
MIN_GRUPO = 2


@dataclass
class No:
    id: int
    pai_id: Optional[int]
    fragmento: str


def texto_completo(no_id: int, nos: dict[int, No]) -> str:
    n = nos[no_id]
    if n.pai_id is None:
        return n.fragmento
    return texto_completo(n.pai_id, nos) + n.fragmento


def construir_inicial(linhas: list[str]) -> tuple[dict[int, No], list[int], dict[str, int]]:
    valor_para_id: dict[str, int] = {}
    nos: dict[int, No] = {}
    body: list[int] = []
    proximo_id = 1
    for v in linhas:
        if v in valor_para_id:
            body.append(valor_para_id[v])
        else:
            nos[proximo_id] = No(proximo_id, None, v)
            valor_para_id[v] = proximo_id
            body.append(proximo_id)
            proximo_id += 1
    return nos, body, valor_para_id


def aplicar_patricia_debug(nos: dict[int, No],
                            min_prefixo: int = MIN_PREFIXO,
                            min_grupo: int = MIN_GRUPO,
                            top_candidatos_log: int = 15) -> tuple[dict[int, No], str]:
    log_linhas: list[str] = []
    proximo_id = max(nos.keys()) + 1 if nos else 1
    iter_n = 0

    while True:
        iter_n += 1
        log_linhas.append("")
        log_linhas.append(f"  ===== Iteracao {iter_n} =====")
        top_level = [n for n in nos.values() if n.pai_id is None]
        log_linhas.append(f"  top-level: {len(top_level)} nos")
        for t in top_level:
            log_linhas.append(f"    no{t.id} = {t.fragmento!r}")

        if len(top_level) < min_grupo:
            log_linhas.append(f"  STOP: {len(top_level)} < min_grupo={min_grupo}")
            break

        contagens: Counter = Counter()
        for n in top_level:
            v = n.fragmento
            for k in range(min_prefixo, len(v)):
                contagens[v[:k]] += 1

        candidatos = [(p, c) for p, c in contagens.items() if c >= min_grupo]
        log_linhas.append(f"  prefixos com count>={min_grupo} e len>={min_prefixo}: {len(candidatos)}")
        candidatos_sorted = sorted(candidatos, key=lambda x: (-len(x[0]), -x[1], x[0]))
        log_linhas.append(f"  top {min(top_candidatos_log, len(candidatos_sorted))} (por len desc, count desc, lex):")
        for p, c in candidatos_sorted[:top_candidatos_log]:
            log_linhas.append(f"    len={len(p):>2} count={c:>2}  {p!r}")
        if len(candidatos_sorted) > top_candidatos_log:
            log_linhas.append(f"    ... +{len(candidatos_sorted) - top_candidatos_log} outros")

        if not candidatos:
            log_linhas.append("  STOP: sem candidatos")
            break

        prefixo, count_escolhido = candidatos_sorted[0]
        log_linhas.append(f"  ESCOLHIDO: {prefixo!r} (len={len(prefixo)}, count={count_escolhido})")

        pai = No(proximo_id, None, prefixo)
        nos[proximo_id] = pai
        log_linhas.append(f"  novo pai: no{proximo_id} = {prefixo!r}")
        proximo_id += 1

        absorvidos: list[tuple[int, str, str]] = []
        for n in top_level:
            if n.fragmento.startswith(prefixo) and n.id != pai.id:
                old_frag = n.fragmento
                n.pai_id = pai.id
                n.fragmento = n.fragmento[len(prefixo):]
                absorvidos.append((n.id, old_frag, n.fragmento))

        log_linhas.append(f"  folhas absorvidas: {len(absorvidos)}")
        for nid, old, new in absorvidos:
            log_linhas.append(f"    no{nid}: {old!r} -> sufixo {new!r}")

    return nos, "\n".join(log_linhas)


def desenhar_arvore(nos: dict[int, No]) -> str:
    filhos_de: dict[Optional[int], list[int]] = {}
    for n in nos.values():
        filhos_de.setdefault(n.pai_id, []).append(n.id)
    for k in filhos_de:
        filhos_de[k].sort()

    linhas: list[str] = []

    def emite(no_id: int, prof: int):
        n = nos[no_id]
        if n.pai_id is None:
            rotulo = f'no{n.id} = "{n.fragmento}"'
        else:
            rotulo = (f'no{n.id} = pai(no{n.pai_id}) + "{n.fragmento}"  '
                      f'-> "{texto_completo(n.id, nos)}"')
        linhas.append("  " * prof + rotulo)
        for filho_id in filhos_de.get(no_id, []):
            emite(filho_id, prof + 1)

    for raiz in filhos_de.get(None, []):
        emite(raiz, 0)
    return "\n".join(linhas)
