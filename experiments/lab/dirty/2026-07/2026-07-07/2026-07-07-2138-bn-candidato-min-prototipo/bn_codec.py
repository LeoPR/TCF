"""bn_codec — PROTÓTIPO (dirty) do par _bN_encode/_decode_bN como 5º candidato do min() por-coluna.

Objetivo (owner): ver as possibilidades — o bN encaixa no mecanismo de marcador-de-modo por-coluna que o
multi-col já tem (char-PREFIXO + min(tcf,raw,v2b,split))? RT fecha? NÃO toca src/tcf — mimetiza o container.

Correções do design já aplicadas:
 - bN codifica DOMÍNIO + STREAM DE ÍNDICES (irmão bit-packed do dict/V2-B), NÃO os tcf_bytes serializados.
   Aqui os índices são re-derivados de vals; no Formato A viriam do ref-stream do HCC (`*N|^k`) — mesmo resultado.
 - Marcador = char-PREFIXO (`#`), como `!`/`@`/`%` — NÃO sufixo `:` (reservado ao :id de nature no multi-col).
"""
from __future__ import annotations
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[4]        # experiments/lab/dirty/<lab>/bn_codec.py → repo root
sys.path.insert(0, str(_ROOT / "src"))
from tcf import encode, decode                          # noqa: E402


def width_for(k: int):
    if k <= 1:
        return 0                                         # constante: 0 bits de índice
    if k <= 2:
        return 1
    if k <= 4:
        return 2
    if k <= 16:
        return 4
    if k <= 256:
        return 8
    return None                                          # >256: bN não se aplica (não é baixa-card)


def _pack(indices, w: int) -> bytes:
    if w == 0:
        return b""
    bits = "".join(format(i, f"0{w}b") for i in indices)
    bits += "0" * ((-len(bits)) % 8)
    return bytes(int(bits[i:i + 8], 2) for i in range(0, len(bits), 8))


def _unpack(data: bytes, w: int, n: int):
    if w == 0:
        return [0] * n
    allbits = "".join(format(b, "08b") for b in data)
    return [int(allbits[i * w:(i + 1) * w], 2) for i in range(n)]


# ---- o par que entraria no min() ----
def bn_encode(vals):
    """domínio + índices empacotados a w bits. None se k>256 (bN não se aplica).
    Body auto-descritivo: [w][domlen:2][domínio via tcf.encode][índices packed]."""
    dom = list(dict.fromkeys(vals))                      # 1ª aparição (= ordem dos ^k do HCC no Formato A)
    w = width_for(len(dom))
    if w is None:
        return None
    idx = {v: i for i, v in enumerate(dom)}
    indices = [idx[v] for v in vals]
    dom_bytes = encode(dom).encode()                     # referência embutida, afixo-comprimida
    packed = _pack(indices, w)
    return bytes([w]) + len(dom_bytes).to_bytes(2, "big") + dom_bytes + packed


def bn_decode(body: bytes, n: int):
    w = body[0]
    dl = int.from_bytes(body[1:3], "big")
    dom = decode(body[3:3 + dl].decode())
    indices = _unpack(body[3 + dl:], w, n)
    return [dom[i] for i in indices]


# ---- mini-container multi-col que roda o min() com bN como candidato ----
# marcadores de prefixo: '' = tcf(HCC) · '!' = raw · '#' = bN   (mimetiza multi/core.py)
def container_encode(cols: dict, allow_bn: bool = True):
    names = list(cols)
    n = len(cols[names[0]]) if names else 0
    parts, bodies, chosen = [], [], {}
    for name in names:
        vals = [str(v) for v in cols[name]]
        cands = {"": encode(vals).encode(), "!": "\n".join(vals).encode()}
        if allow_bn:
            bn = bn_encode(vals)
            if bn is not None:
                cands["#"] = bn
        pref = min(cands, key=lambda k: len(cands[k]))
        body = cands[pref]
        parts.append(f"{pref}{len(body)}={name}")
        bodies.append(body)
        chosen[name] = (pref or "tcf", len(body))
    meta = ",".join(parts)
    blob = f"#PROTO.BN {n} {meta}\n".encode() + b"".join(bodies)
    return blob, chosen


def container_decode(blob: bytes):
    head, rest = blob.split(b"\n", 1)
    _magic, ns, meta = head.decode().split(" ", 2)
    n = int(ns)
    cols, off = {}, 0
    for part in meta.split(","):
        spec, name = part.split("=", 1)
        pref = ""
        if spec and spec[0] in "!#":
            pref, spec = spec[0], spec[1:]
        size = int(spec)
        body = rest[off:off + size]; off += size
        if pref == "#":
            cols[name] = bn_decode(body, n)
        elif pref == "!":
            cols[name] = body.decode().split("\n")
        else:
            cols[name] = decode(body.decode())
    return cols
