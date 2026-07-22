"""B2 prototype (read-only) — group-dict hibrido V2, formato &<G>, com ROUND-TRIP.

Vai ALEM do B1 (que so' modelou bytes): constroi o formato de verdade e PROVA RT.
src/tcf INTOCADO — reusa os internos V2-B (byte-fiel) como biblioteca. O weld e' B3.

Formato B2 (design-b2.md, pos-revisao A-D):
  #TCF.8M<meta>\n
  <n_grupos>\n <ntab_0>\n<tab_0> <ntab_1>\n<tab_1> ...     <- PRELUDIO length-prefixed (so' se ha grupo)
  <body col 0><body col 1>...                              <- colunas (fatiadas por size no meta)
  meta token: coluna grupada = &<gid>:<size>=<nome> (stream-only)
              coluna @dict avulsa = @<size>=<nome> (V2-B)
              coluna plana = <size>=<nome>
Particionamento: greedy custo-modelado (a dobradica; bytes(tab_G) MEDIDO encodando a uniao).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
from tcf.encoder import _encode_column                                   # noqa: E402
from tcf.decoder import _decode_column                                   # noqa: E402
from tcf.pipeline import PipelineConfig                                  # noqa: E402
from tcf.side_outputs import SideOutputs                                 # noqa: E402
from tcf.multi.dict_v2b import (                                         # noqa: E402
    _V2B_BASE, _v2b_width, _v2b_idx_chars, _v2b_encode, _decode_v2b)

CFG = PipelineConfig()
JACCARD = 0.5   # pre-corte de similaridade (so' ACELERA; o guard real e' o custo)


# ---------------- helpers byte-fieis (reuso V2-B) ----------------
def _uniques(values):
    seen, uni = {}, []
    for v in values:
        if v not in seen:
            seen[v] = len(uni)
            uni.append(v)
    return uni, seen


def _tab(unicas, want_side=False):
    """Serializa a tabela de unicos (mesma serializacao V2-B = _encode_column).
    Retorna (bytes, side|None). O side traz obat_log/hcc_trace do encode da tabela."""
    side = SideOutputs() if want_side else None
    txt = _encode_column(unicas, header="val", side=side, cfg=CFG, min_len=None)
    return txt.encode("utf-8"), side


def _stream(values, seen, width):
    return "".join(_v2b_idx_chars(seen[v], width) for v in values).encode("utf-8")


def _decode_stream(stream_bytes, unicas, width):
    out = []
    for j in range(0, len(stream_bytes), width):
        idx = 0
        for ch in stream_bytes[j:j + width]:
            idx = idx * _V2B_BASE + (ch - 0x21)
        out.append(unicas[idx])
    return out


def jaccard(a, b):
    sa, sb = set(a), set(b)
    u = sa | sb
    return len(sa & sb) / len(u) if u else 0.0


# ---------------- particionamento greedy custo-modelado ----------------
def partition(cols):
    """Greedy custo-modelado, decidindo por BYTES REAIS (nao formula analitica).

    V0 do grupo = soma dos bodies per-coluna REAIS (V2-B @dict p/ low-card OU OBAT/HCC
    plano p/ high-card — o que o pipeline de fato produz). B2 do grupo = tabela de uniao
    (1x) + streams (N_c * w(K_G)) + framing do preludio. Pool sse b2_body < v0_body.
    SEM cap K<=1024: o cross-dict paga JUSTAMENTE em same-domain de ALTA cardinalidade
    (nos de grafo), onde o per-column V2-B nem se aplica (baseline = OBAT/HCC).
    """
    names = list(cols)
    info, cand = {}, []
    for n in names:
        uni, seen = _uniques(cols[n])
        K, N = len(uni), len(cols[n])
        info[n] = dict(uni=uni, seen=seen, K=K, N=N)
        if 2 <= K < N:                      # ha' repeticao (SEM cap 1024)
            cand.append(n)

    # cluster por Jaccard (union-find) — pre-corte de similaridade (so' acelera)
    parent = {n: n for n in cand}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i in range(len(cand)):
        for j in range(i + 1, len(cand)):
            if jaccard(cols[cand[i]], cols[cand[j]]) >= JACCARD:
                parent[find(cand[i])] = find(cand[j])

    clusters = {}
    for n in cand:
        clusters.setdefault(find(n), []).append(n)

    groups, decisions = [], []
    for members in clusters.values():
        members = [n for n in names if n in members]   # preserva ordem do meta
        if len(members) < 2:
            continue
        # V0 REAL: soma dos bodies per-coluna (dict OU OBAT/HCC — o que o pipeline produz)
        v0_body = sum(len(_col_slot(cols[n])[1]) for n in members)
        # UNIAO (first-appearance na ordem do meta) — bytes MEDIDOS
        gseen, guni = {}, []
        for n in members:
            for v in cols[n]:
                if v not in gseen:
                    gseen[v] = len(guni)
                    guni.append(v)
        KG, wG = len(guni), _v2b_width(len(guni))
        tabG, _ = _tab(guni)
        prelude = len("1\n") + len(f"{len(tabG)}\n") + len(tabG)   # framing de 1 grupo
        streams = sum(info[n]["N"] * wG for n in members)
        b2_body = prelude + streams
        pooled = b2_body < v0_body
        decisions.append(dict(members=members, K_c={n: info[n]["K"] for n in members},
                              KG=KG, wG=wG, v0_body=v0_body, b2_body=b2_body,
                              net_group=100 * (b2_body - v0_body) / v0_body, pooled=pooled,
                              jac=(jaccard(cols[members[0]], cols[members[1]])
                                   if len(members) == 2 else None)))
        if pooled:
            groups.append(members)
    return groups, decisions


# ---------------- encode / decode ----------------
def _col_slot(values, name=None):
    """slot V0/avulso: (@dict V2-B) ou (plano). Retorna (mode_token_prefix, body)."""
    slot = _v2b_encode(values, cfg=CFG, min_len=None)
    if slot is not None:
        return "@", slot
    body = _encode_column(values, header="val", cfg=CFG, min_len=None).encode("utf-8")
    return "", body


def encode_v0(cols):
    """Baseline V0: cada coluna per-column (@dict V2-B ou plano)."""
    meta, bodies = [], []
    for n in cols:
        pre, body = _col_slot(cols[n], n)
        meta.append(f"{pre}{len(body)}={n}")
        bodies.append(body)
    return b"#TCF.8M" + ",".join(meta).encode() + b"\n" + b"".join(bodies)


def encode_b2(cols, groups):
    """B2: group-dict no PRELUDIO + colunas grupadas stream-only."""
    name_gid = {n: gi for gi, ms in enumerate(groups) for n in ms}
    gtab, gwidth, gseen = [], [], []
    for members in groups:
        s, u = {}, []
        for n in members:
            for v in cols[n]:
                if v not in s:
                    s[v] = len(u)
                    u.append(v)
        tb, _ = _tab(u)
        gtab.append(tb)
        gwidth.append(_v2b_width(len(u)))
        gseen.append(s)

    meta, bodies = [], []
    for n in cols:
        if n in name_gid:
            gi = name_gid[n]
            body = _stream(cols[n], gseen[gi], gwidth[gi])
            meta.append(f"&{gi}:{len(body)}={n}")
        else:
            pre, body = _col_slot(cols[n], n)
            meta.append(f"{pre}{len(body)}={n}")
        bodies.append(body)

    prelude = b""
    if groups:
        prelude = f"{len(groups)}\n".encode()
        for tb in gtab:
            prelude += f"{len(tb)}\n".encode() + tb
    return b"#TCF.8M" + ",".join(meta).encode() + b"\n" + prelude + b"".join(bodies)


def decode(blob):
    """Decoda blob V0 OU B2 (has_group deduzido do meta). Retorna dict name->list."""
    nl = blob.find(b"\n")
    meta = blob[:nl].decode("utf-8")
    assert meta.startswith("#TCF.8M"), meta[:20]
    tokens = meta[len("#TCF.8M"):].split(",") if len(meta) > len("#TCF.8M") else []
    parsed, has_group = [], False
    for t in tokens:
        if t.startswith("&"):
            has_group = True
            gid_s, rest = t[1:].split(":", 1)
            size_s, name = rest.split("=", 1)
            parsed.append(("&", int(gid_s), int(size_s), name))
        elif t.startswith("@"):
            size_s, name = t[1:].split("=", 1)
            parsed.append(("@", None, int(size_s), name))
        else:
            size_s, name = t.split("=", 1)
            parsed.append(("", None, int(size_s), name))

    cursor = nl + 1
    gtables = []
    if has_group:
        nl2 = blob.find(b"\n", cursor)
        ng = int(blob[cursor:nl2])
        cursor = nl2 + 1
        for _ in range(ng):
            nl3 = blob.find(b"\n", cursor)
            ntab = int(blob[cursor:nl3])
            cursor = nl3 + 1
            tab = blob[cursor:cursor + ntab]
            cursor += ntab
            unis = _decode_column(tab.decode("utf-8"))
            gtables.append((unis, _v2b_width(len(unis))))

    out = {}
    for mode, gid, size, name in parsed:
        body = blob[cursor:cursor + size]
        cursor += size
        if mode == "&":
            unis, width = gtables[gid]
            out[name] = _decode_stream(body, unis, width)
        elif mode == "@":
            out[name] = _decode_v2b(body)
        else:
            out[name] = _decode_column(body.decode("utf-8"))
    return out
