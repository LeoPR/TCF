"""bn_gate — helpers do GATE real-world do bN (D3, H-TYPE-02). NÃO toca src/tcf.

Mede bN vs a PRODUÇÃO REAL (min(tcf,raw,v2b,split) por coluna, fallback=True) — o baseline correto — em
>=5 fontes reais, no nível-TABELA (weighted), pré e pós-brotli. Responde o gate do CLAUDE.md ponto 5
(bytes absolutos >=5% weighted real-world) e a margem terminal (H-TYPE-03).

bN = dominio embutido + indices a w bits (irmao bit-packed do dict). Corrigido: recebe dominio+indices,
nao os tcf_bytes. Indices re-derivados de vals (no Formato A viriam do ref-stream do HCC).
"""
from __future__ import annotations
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[4]        # experiments/lab/dirty/<lab>/bn_gate.py → repo root
sys.path.insert(0, str(_ROOT / "src"))
from tcf import encode                              # noqa: E402


def width_for(k: int):
    if k <= 1:
        return 0
    if k <= 2:
        return 1
    if k <= 4:
        return 2
    if k <= 16:
        return 4
    if k <= 256:
        return 8
    return None                                     # >256: bN nao se aplica


def _pack(indices, w):
    if w == 0:
        return b""
    bits = "".join(format(i, f"0{w}b") for i in indices)
    bits += "0" * ((-len(bits)) % 8)
    return bytes(int(bits[i:i + 8], 2) for i in range(0, len(bits), 8))


def _unpack(data, w, n):
    if w == 0:
        return [0] * n
    allbits = "".join(format(b, "08b") for b in data)
    return [int(allbits[i * w:(i + 1) * w], 2) for i in range(n)]


def bn_encode(vals):
    """dominio (afixo-comprimido via tcf.encode) + indices packed. None se k>256."""
    dom = list(dict.fromkeys(vals))
    w = width_for(len(dom))
    if w is None:
        return None, None
    idx = {v: i for i, v in enumerate(dom)}
    packed = _pack([idx[v] for v in vals], w)
    dom_bytes = encode(dom).encode()
    body = bytes([w]) + len(dom_bytes).to_bytes(2, "big") + dom_bytes + packed
    return body, dom


def bn_decode(body, n):
    w = body[0]
    dl = int.from_bytes(body[1:3], "big")
    from tcf import decode
    dom = decode(body[3:3 + dl].decode())
    return [dom[i] for i in _unpack(body[3 + dl:], w, n)]


_MODE = {"!": "raw", "@": "v2b", "%": "split", "": "tcf"}


def extract_table(cols):
    """Encoda a tabela UMA vez (producao real, fallback=True) e EXTRAI (name, mode, body) por coluna do
    meta — sem re-encodar coluna a coluna. Retorna (total_bytes, [(name, mode, body_bytes)])."""
    blob = encode({k: [str(x) for x in v] for k, v in cols.items()}, fallback=True).encode()
    i1 = blob.index(b"\n"); i2 = blob.index(b"\n", i1 + 1)
    meta = blob[i1 + 1:i2].decode(); bodies = blob[i2 + 1:]
    out, off = [], 0
    specs = meta.split(",")
    for j, s in enumerate(specs):
        pref = s[0] if s and s[0] in "!@%" else ""
        rest = s[1:] if pref else s
        if "=" in rest:
            size_str, name = rest.split("=", 1)
            size = int(size_str)
            body = bodies[off:off + size]; off += size
        else:
            name = rest; body = bodies[off:]                # ultima coluna: body ate EOF
        out.append((name, _MODE[pref], body))
    assert off <= len(bodies), "parse de meta inconsistente"
    return len(blob), out
