"""Decomposicao instrumentada por string. Mesma logica do exp 08
mas com logging.
"""

from patricia_instrumentado import (
    No,
    aplicar_patricia_debug,
    construir_inicial,
    texto_completo,
)


def construir_bidir_debug(linhas: list[str], min_prefixo: int = 3):
    log: list[str] = []

    log.append("==========================================================")
    log.append("FASE A — ARVORE FORWARD (sobre strings originais)")
    log.append("==========================================================")
    fwd_arvore, _, fwd_str_to_eid = construir_inicial(linhas)
    log.append(f"\nfolhas iniciais ({len(fwd_arvore)}):")
    for nid in sorted(fwd_arvore):
        log.append(f"  no{nid} = {fwd_arvore[nid].fragmento!r}")

    fwd_arvore, fwd_log = aplicar_patricia_debug(fwd_arvore, min_prefixo=min_prefixo)
    log.append(fwd_log)

    log.append("")
    log.append("==========================================================")
    log.append("FASE B — ARVORE REVERSE (sobre strings invertidas)")
    log.append("==========================================================")
    log.append("nota: o algoritmo trabalha sobre as strings invertidas, o que")
    log.append("equivale a detectar SUFIXOS comuns das strings originais.")
    log.append("")
    linhas_inv = [s[::-1] for s in linhas]
    log.append("strings invertidas:")
    for s, si in zip(linhas, linhas_inv):
        log.append(f"  {s!r} -> {si!r}")

    rev_arvore, _, rev_str_to_eid = construir_inicial(linhas_inv)
    rev_arvore, rev_log = aplicar_patricia_debug(rev_arvore, min_prefixo=min_prefixo)
    log.append(rev_log)

    return fwd_arvore, fwd_str_to_eid, rev_arvore, rev_str_to_eid, "\n".join(log)


def decompor_string_debug(s: str, fwd_arvore, fwd_str_to_eid,
                          rev_arvore, rev_str_to_eid,
                          min_prefixo: int = 3) -> tuple[tuple[str, str, str], str]:
    log: list[str] = []
    log.append(f"\n--- decompor {s!r} (len={len(s)}) ---")

    eid_fwd = fwd_str_to_eid[s]
    no_fwd = fwd_arvore[eid_fwd]
    if no_fwd.pai_id is None:
        prefix_text = ""
        log.append(f"  fwd: folha no{eid_fwd} eh top-level (sem pai) -> pref=''")
    else:
        prefix_text = texto_completo(no_fwd.pai_id, fwd_arvore)
        log.append(f"  fwd: folha no{eid_fwd}; pai imediato = no{no_fwd.pai_id} = "
                   f"{prefix_text!r} (len={len(prefix_text)})")

    s_inv = s[::-1]
    eid_rev = rev_str_to_eid[s_inv]
    no_rev = rev_arvore[eid_rev]
    if no_rev.pai_id is None:
        suffix_text = ""
        log.append(f"  rev: folha no{eid_rev} eh top-level -> suf=''")
    else:
        sufixo_inv = texto_completo(no_rev.pai_id, rev_arvore)
        suffix_text = sufixo_inv[::-1]
        log.append(f"  rev: folha no{eid_rev}; pai imediato = no{no_rev.pai_id} = "
                   f"{sufixo_inv!r} (invertido) = {suffix_text!r} (sufixo natural, "
                   f"len={len(suffix_text)})")

    if prefix_text and len(prefix_text) < min_prefixo:
        log.append(f"  pref descartado: len={len(prefix_text)} < min={min_prefixo}")
        prefix_text = ""
    if suffix_text and len(suffix_text) < min_prefixo:
        log.append(f"  suf descartado: len={len(suffix_text)} < min={min_prefixo}")
        suffix_text = ""

    if prefix_text and suffix_text:
        if len(prefix_text) + len(suffix_text) > len(s):
            log.append(f"  OVERLAP: len(p)={len(prefix_text)} + len(x)="
                       f"{len(suffix_text)} = {len(prefix_text)+len(suffix_text)} "
                       f"> len(s)={len(s)}")
            if len(prefix_text) >= len(suffix_text):
                log.append(f"  resolve: pref mais longo ou empate. Descarta suf.")
                suffix_text = ""
            else:
                log.append(f"  resolve: suf mais longo. Descarta pref.")
                prefix_text = ""
        else:
            log.append(f"  sem overlap: {len(prefix_text)} + {len(suffix_text)} = "
                       f"{len(prefix_text)+len(suffix_text)} <= {len(s)}")

    if suffix_text:
        middle = s[len(prefix_text): len(s) - len(suffix_text)]
    else:
        middle = s[len(prefix_text):]
    log.append(f"  FINAL: pref={prefix_text!r} mid={middle!r} suf={suffix_text!r}")
    return (prefix_text, middle, suffix_text), "\n".join(log)
