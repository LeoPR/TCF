"""`decode_bn_fixed` — a proposta do T-BN-B64-VALIDATE, como módulo inspecionável do lab.

Cópia 1:1 de `src/tcf/composicional/dominio_bn.py::decode_bn` trocando APENAS:

1. **a linha do b64decode** — `validate=True` + wrap `ValueError` nível TCF
   (fraseologia `#TCF.8<disc>: payload bN nao e' base64 canonico: …`, alinhada ao
   `_decode_denso`/`_decode_lazy_bool` do `decoder.py`);
2. **opcional `tamanho_exato=True`** — a checagem `len(raw) == ceil(n*w/8)` que o
   `_decode_denso` já faz. Variante que o achado s06/s08 deste lab motivou: o
   `validate=True` puro NÃO pega dados extras *válidos* (payload longo, padding
   canônico a mais).

`src/tcf` INTOCADO — este módulo existe para o owner inspecionar a proposta linha a
linha antes de qualquer weld.
"""
import base64
import binascii
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[6] / "src"))

from tcf.composicional import dominio_bn as m  # noqa: E402
from tcf.composicional.dominio_bn import _b64_len  # noqa: E402


def decode_bn_fixed(tcf_text: str, disc: str, decode_col, tamanho_exato: bool = False):
    """Lê um wire `#TCF.8B…`/`#TCF.8C…` — igual ao `decode_bn`, mas com b64 validado."""
    cab, sep, resto = tcf_text.partition("\n")
    if not sep:
        raise ValueError(f"wire bN sem corpo: {cab[:24]!r}")
    campos = cab[len(m.MAGIC) + 1:]
    if len(campos) < 2 or campos[0] not in "12345678":
        raise ValueError(
            f"cabecalho bN nao-canonico: largura {campos[:1]!r} fora de 1..{m.MAX_W}"
        )
    w = int(campos[0])
    nhex = campos[1:]
    if any(c not in "0123456789abcdef" for c in nhex):
        raise ValueError(f"contagem bN nao-hexadecimal-canonica: {nhex!r}")
    n = int(nhex, 16)
    if f"{n:x}" != nhex:
        raise ValueError(
            f"contagem bN nao-canonica: {nhex!r} (canonico: {n:x}) — duas grafias para o "
            f"mesmo valor violariam a canonicidade do wire"
        )
    if disc == m.DISC_LOTE:
        nb = _b64_len(n, w)
        b64, bloco = resto[:nb], resto[nb + 1:]
    else:
        linhas = resto.split("\n")
        alvo = next((j for j, ln in enumerate(linhas) if ln.startswith(m.MARCADOR)), None)
        if alvo is None:
            raise ValueError(
                f"wire bN sem o marcador {m.MARCADOR!r} que separa dominio e bits "
                f"— corpo nao-canonico (truncado ou editado a mao)"
            )
        if any(ln for ln in linhas[alvo + 1:]):
            raise ValueError(
                f"conteudo apos o bloco de bits do bN: {linhas[alvo + 1:][:1]!r} "
                f"— corpo nao-canonico (wire concatenado ou editado a mao)"
            )
        b64 = linhas[alvo][1:]
        bloco = "\n".join(ln[1:] if ln.startswith(m.BS + m.MARCADOR) else ln
                          for ln in linhas[:alvo])
    dom = [m._le_grafia(s) for s in decode_col(bloco + "\n")]
    if not dom:
        raise ValueError("dominio bN vazio — corpo nao-canonico")
    if len(dom) > (1 << w):
        raise ValueError(f"dominio bN com {len(dom)} valores nao cabe em {w} bits")
    # --- MUDANCA 1 (a proposta do T-BN-B64-VALIDATE): validate + wrap TCF ---------
    try:
        raw = base64.b64decode(b64 + "=" * (-len(b64) % 4), validate=True)
    except (ValueError, binascii.Error) as e:
        raise ValueError(f"#TCF.8{disc}: payload bN nao e' base64 canonico: {e}") from e
    # ------------------------------------------------------------------------------
    # --- MUDANCA 2 (opcional; achado s06/s08 do lab): tamanho EXATO, como o denso --
    if tamanho_exato:
        esperado = -(-n * w // 8)                # ceil(n*w/8), mesma conta do _decode_denso
        if len(raw) != esperado:
            raise ValueError(
                f"#TCF.8{disc}: payload bN = {len(raw)} bytes, esperado {esperado} p/ "
                f"n={n} w={w} (wire truncado/adulterado)"
            )
    # ------------------------------------------------------------------------------
    saida = []
    for i in m.unpack_w(raw, w, n):
        if i >= len(dom):
            raise ValueError(
                f"indice {i} fora do dominio bN de {len(dom)} valores — corpo nao-canonico"
            )
        saida.append(dom[i])
    return saida
