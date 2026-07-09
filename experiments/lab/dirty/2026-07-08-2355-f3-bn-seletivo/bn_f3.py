"""bn_f3 — F3 (misto seletivo): roda o núcleo, ADICIONA bN como candidato do min() só em k<=16 (w<=4).

O byte-tileavel honesto: só w∈{1,2,4} empacotam >1 valor por byte (3/5/6/7 bits atravessam fronteira de
byte). Reusa o DOMÍNIO do v2b (mesma tabela afixo-comprimida via _v2b_encode) e troca SÓ o stream de
índices (base-94 → bits) — isola o radix. NOTA (aprox.): a referência v2b do bN usa min_len=None, enquanto
a produção pode escolher v2b com min_len auto; o delta de tabela é << delta de radix, então os números
ficam (se algo, conservadores). E o pb comparado é o min(tcf,raw,v2b,split) REAL, não necessariamente v2b.

Byte-safe por construção: F3_body = min(produção, bN). Para k>16 (w=8) bN=v2b no terminal (1 byte/índice
nos dois) → nenhum ganho de bit-packing; por isso o gate w<=4 do owner é o subconjunto honesto.

NÃO toca src/tcf. Roda com python3 (import de src + brotli no run).
"""
from __future__ import annotations
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[4]              # <lab>/bn_f3.py → repo root
sys.path.insert(0, str(_ROOT / "src"))
from tcf import encode                                   # noqa: E402
from tcf.multi.dict_v2b import _v2b_encode               # noqa: E402
from tcf.pipeline import PipelineConfig                  # noqa: E402

_CFG = PipelineConfig()


def width_f3(k):
    """Gate F3: só larguras que tile-de-byte (1/2/4 bits). None se k>16 (fora do F3)."""
    if k <= 2:
        return 1
    if k <= 4:
        return 2
    if k <= 16:
        return 4
    return None


def width_wide(k):
    """D3-style (até w=8): p/ decompor quanto do ganho vinha de k 17..256 (que F3 descarta)."""
    w = width_f3(k)
    if w is not None:
        return w
    if k <= 256:
        return 8
    return None


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


def bn_body(vals, k, wide=False):
    """bN reusando o DOMÍNIO do v2b + índices bit-packed. None se v2b não aplica ou k fora do gate.

    v2b format = <ntable>\\n + table + stream(base-94). bN = <ntable>\\n + table + packed(bits).
    Mesma `table` → a diferença medida é EXATAMENTE o radix do índice.

    Gate PRIMEIRO (por k), ANTES do _v2b_encode: encodar o domínio de K=257..8192 pra depois descartar
    (k fora do gate) era o gargalo. Agora só encoda quando a largura é válida."""
    w = width_wide(k) if wide else width_f3(k)
    if w is None:                                        # fora do gate (k>16 no F3; k>256 no wide) → sem encode
        return None
    v2b = _v2b_encode(vals, cfg=_CFG, min_len=None)
    if v2b is None:                                      # k<2, k>=N (sem repetição) → nem v2b nem bN
        return None
    nl = v2b.find(b"\n")
    ntable = int(v2b[:nl])
    start = nl + 1
    table = v2b[start:start + ntable]
    seen, idx = {}, []
    for v in vals:                                       # índice por ordem de aparição (== v2b)
        j = seen.get(v)
        if j is None:
            j = len(seen)
            seen[v] = j
        idx.append(j)
    return f"{ntable}\n".encode("utf-8") + table + _pack(idx, w)


def bn_decode(body, n, wide=False):
    from tcf.decoder import _decode_column
    nl = body.find(b"\n")
    ntable = int(body[:nl])
    start = nl + 1
    unicas = _decode_column(body[start:start + ntable].decode("utf-8"))
    w = width_wide(len(unicas)) if wide else width_f3(len(unicas))
    return [unicas[i] for i in _unpack(body[start + ntable:], w, n)]


_MODE = {"!": "raw", "@": "v2b", "%": "split", "": "tcf"}


def extract_table(cols):
    """Encoda a tabela UMA vez (produção real, fallback=True) e extrai (name, mode, body) por coluna do
    meta — idêntico ao D3. Retorna (total_bytes, [(name, mode, body_bytes)])."""
    blob = encode({k: [str(x) for x in v] for k, v in cols.items()}, fallback=True).encode()
    i1 = blob.index(b"\n")
    i2 = blob.index(b"\n", i1 + 1)
    meta = blob[i1 + 1:i2].decode()
    bodies = blob[i2 + 1:]
    out, off = [], 0
    for s in meta.split(","):
        pref = s[0] if s and s[0] in "!@%" else ""
        rest = s[1:] if pref else s
        if "=" in rest:
            size_str, name = rest.split("=", 1)
            size = int(size_str)
            body = bodies[off:off + size]
            off += size
        else:
            name = rest
            body = bodies[off:]
        out.append((name, _MODE[pref], body))
    assert off <= len(bodies), "parse de meta inconsistente"
    return len(blob), out
