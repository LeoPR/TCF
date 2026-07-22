"""bypass_codec — F1: classificar low-card e PULAR o núcleo (OBAT+HCC). Play de LATÊNCIA.

Nomenclatura (owner 2026-07-08) — NÃO confundir largura física com código semântico:
 - **b1/b2/b4** (minúsculo) = LARGURA FÍSICA real do índice (1/2/4 bits), tile-de-byte (só 1,2,4 dividem 8).
   Reativo: domínio guardado na coluna.
 - **b3** = código reusado (3 não tem largura física válida) p/ "b2 + null" (trio, 2 bits, 4º slot livre).
 - **b5/b6/b7** = códigos reusados p/ tipos especiais (reservados).
 - **B** (MAIÚSCULO) = bool com nomenclatura INTERNA (dict congelado no formato): NÃO declara a referência
   no arquivo, usa a interna sempre.

Este lab mede a LATÊNCIA do bypass vs o núcleo. Não toca src/tcf.
"""
from __future__ import annotations


def width_for(k):
    if k <= 1:
        return 0
    if k <= 2:
        return 1
    if k <= 4:
        return 2
    if k <= 16:
        return 4
    return None                                        # k>16 → bail pro núcleo (bypass não se aplica)


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


# --- REATIVO (b1/b2/b4): 1 passada constrói domínio+índices, empacota. None se k>16 (bail) ---
def bypass_encode(vals, k_max=16):
    seen, dom, idx = {}, [], []
    for v in vals:
        j = seen.get(v)
        if j is None:
            if len(dom) >= k_max:
                return None                            # k>16 → NÃO é bypass; roda o núcleo
            j = len(dom); seen[v] = j; dom.append(v)
        idx.append(j)
    w = width_for(len(dom))
    return {"dom": dom, "w": w, "packed": _pack(idx, w), "n": len(vals)}


def bypass_decode(enc):
    return [enc["dom"][i] for i in _unpack(enc["packed"], enc["w"], enc["n"])]


# --- INTERNO (B): domínio CONGELADO no formato (não guarda) + overlay de exceções ---
INTERNAL = {
    "bool": ("false", "true"),               # 1 bit
    "bool3": ("false", "true", "null"),      # 2 bits (b3 = b2+null)
    "yesno": ("no", "yes"),                  # 1 bit
    "bit": ("0", "1"),                       # 1 bit
}


def internal_encode(vals, spec_id):
    dom = INTERNAL[spec_id]
    pos = {v: i for i, v in enumerate(dom)}
    w = width_for(len(dom))
    idx, exc = [], []
    for i, v in enumerate(vals):
        j = pos.get(v)
        if j is None:
            idx.append(0); exc.append((i, v))          # fora do dict congelado → overlay
        else:
            idx.append(j)
    return {"spec": spec_id, "w": w, "packed": _pack(idx, w), "exc": exc, "n": len(vals)}


def internal_decode(enc):
    dom = INTERNAL[enc["spec"]]
    out = [dom[i] for i in _unpack(enc["packed"], enc["w"], enc["n"])]
    for i, v in enc["exc"]:
        out[i] = v
    return out
