"""Decoder bidir: le marcador <dir:NAME>, decodifica como aninhado,
e inverte de volta se direcao == 'reverse'.
"""

from decode_aninhado import decode_aninhado


def decode_bidir(tcf_text: str) -> list[str]:
    linhas = tcf_text.splitlines()
    direcao = None
    primeira_idx = 0
    for i, raw in enumerate(linhas):
        stripped = raw.strip()
        if not stripped:
            continue
        if stripped.startswith("<dir:") and stripped.endswith(">"):
            direcao = stripped[len("<dir:"):-1]
            primeira_idx = i + 1
            break
        raise ValueError(f"falta marcador <dir:...> no inicio: {stripped!r}")

    if direcao is None:
        raise ValueError("nenhum marcador de direcao encontrado")
    if direcao not in ("forward", "reverse"):
        raise ValueError(f"direcao invalida: {direcao!r}")

    inner = "\n".join(linhas[primeira_idx:])
    decoded = decode_aninhado(inner)

    if direcao == "reverse":
        decoded = [s[::-1] for s in decoded]

    return decoded
