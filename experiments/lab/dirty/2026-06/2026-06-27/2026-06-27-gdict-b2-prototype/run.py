"""Driver do B2 prototype — roda os casos e EMITE ARTEFATOS de rastreabilidade.

Fluxo por caso: input -> particionamento (decisao) -> encode V0 e B2 -> RT -> medida.
Artefatos completos (caso ilustrativo): artifacts/01..06 (input, decisao, OBAT/HCC da uniao,
blob V0, blob B2, RT+medida). Casos reais/bordas: linha de medida + RT (blobs grandes nao dumpados).
READ-ONLY. src/tcf intocado.
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parent
sys.path.insert(0, str(LAB))
import b2proto as B                                        # noqa: E402
from b2proto import partition, encode_v0, encode_b2, decode, _tab, _uniques, jaccard, _v2b_width  # noqa: E402

try:
    import brotli
    _bz = lambda b: len(brotli.compress(b)); CN = "brotli"     # noqa: E731
except ImportError:
    import gzip
    _bz = lambda b: len(gzip.compress(b, 9)); CN = "gzip"      # noqa: E731

ART = LAB / "artifacts"
ART.mkdir(exist_ok=True)


def _rt(cols, blob):
    got = decode(blob)
    return all(got.get(n) == cols[n] for n in cols) and set(got) == set(cols)


def _dict_slot_uncapped(values):
    """per-column dict SEM o cap K<=1024 (dict-mas-nao-compartilhado = V1)."""
    uni, seen = B._uniques(values)
    K, N = len(uni), len(values)
    if not (2 <= K < N):
        return None
    tb, _ = B._tab(uni)
    return f"{len(tb)}\n".encode() + tb + B._stream(values, seen, B._v2b_width(K))


def encode_v1(cols):
    """V1 = per-column dict UNCAPPED (isola dict-vs-OBAT/HCC de cross-dict)."""
    meta, bodies = [], []
    for n in cols:
        s = _dict_slot_uncapped(cols[n])
        if s is not None:
            bodies.append(s); meta.append(f"@{len(s)}={n}")
        else:
            pre, body = B._col_slot(cols[n]); meta.append(f"{pre}{len(body)}={n}"); bodies.append(body)
    return b"#TCF.8M" + ",".join(meta).encode() + b"\n" + b"".join(bodies)


def _body(blob):
    return len(blob) - (blob.find(b"\n") + 1)


def measure(label, cols):
    groups, decisions = partition(cols)
    b0, b1, bB = encode_v0(cols), encode_v1(cols), encode_b2(cols, groups)
    rt0, rt1, rtB = _rt(cols, b0), _rt(cols, b1), _rt(cols, bB)

    tot = 100 * (_body(bB) - _body(b0)) / _body(b0)          # B2 vs baseline REAL (dict-ou-OBAT/HCC)
    dictgain = 100 * (_body(b1) - _body(b0)) / _body(b0)     # (a) dict-vs-OBAT/HCC (per-col, sem cap)
    share = 100 * (_body(bB) - _body(b1)) / _body(b1)        # (b) CROSS-DICT sharing (B2 vs V1) = valor real
    br = 100 * (_bz(bB) - _bz(b0)) / _bz(b0)                 # controle total (B2 vs V0)
    br_share = 100 * (_bz(bB) - _bz(b1)) / _bz(b1)           # controle do SHARING (B2 vs V1)
    grouped = [n for g in groups for n in g]
    print(f"{label:48} RT[{'ok' if rt0 and rt1 and rtB else 'FALHA'}] grp={len(groups)}  "
          f"total={tot:+.1f}%  (dict={dictgain:+.1f}% + share={share:+.1f}%)  "
          f"{CN}[tot={br:+.1f}% share={br_share:+.1f}%]  dec {len(grouped)}->{len(groups)}")
    return dict(groups=groups, decisions=decisions, b0=b0, b1=b1, bB=bB,
                rt0=rt0, rt1=rt1, rtB=rtB, tot=tot, dictgain=dictgain, share=share,
                br=br, br_share=br_share,
                body0=_body(b0), body1=_body(b1), bodyB=_body(bB),
                full0=len(b0), fullB=len(bB), v0_dec=len(grouped), vB_dec=len(groups))


# ---------------- loaders reais (Z:) ----------------
EXT = Path("Z:/tcf-data/external")


def load_grqc():
    src, dst = [], []
    for line in (EXT / "snap-ca-grqc" / "ca-GrQc.txt").read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        a, b = line.split()
        src.append(a); dst.append(b)
    return {"from_node": src, "to_node": dst}


def load_openflights():
    rows = [ln.split(",") for ln in (EXT / "openflights" / "routes.dat")
            .read_text(encoding="utf-8", errors="replace").splitlines() if len(ln.split(",")) >= 6]
    return dict(source_airport=[r[2] for r in rows], dest_airport=[r[4] for r in rows],
                source_airport_id=[r[3] for r in rows], dest_airport_id=[r[5] for r in rows])


# ---------------- sinteticos ----------------
def synth_illustrative():
    """Par same-domain PEQUENO (transacoes de/para) — pra dump completo de artefatos."""
    de = ["ACC01", "ACC02", "ACC03", "ACC01", "ACC04", "ACC02", "ACC05", "ACC03", "ACC01", "ACC06"]
    para = ["ACC02", "ACC03", "ACC01", "ACC05", "ACC02", "ACC06", "ACC01", "ACC04", "ACC03", "ACC05"]
    return {"conta_de": de, "conta_para": para}


def synth_3col():
    import random
    rng = random.Random(7)
    codes = [f"AP{i:03d}" for i in range(300)]
    return {n: rng.choices(codes, k=2000) for n in ("origem", "conexao", "destino")}


def synth_bucket_cross():
    """2 cols same-domain (Jaccard alto) cuja UNIAO cruza 94 -> deve NAO poolar."""
    import random
    rng = random.Random(3)
    shared = [f"C{i:02d}" for i in range(85)]       # 85 compartilhados
    a = shared + [f"A{i}" for i in range(5)]         # +5 exclusivos -> K=90
    b = shared + [f"B{i}" for i in range(5)]         # +5 exclusivos -> K=90 ; uniao=95 (cruza 94)
    # N GRANDE: o custo de largura (∝N, w 1->2) domina o dedup (fixo) -> B2 deve PERDER
    return {"col_a": rng.choices(a, k=8000), "col_b": rng.choices(b, k=8000)}


def dump_illustrative(cols, res):
    """Artefatos 01..06 do caso ilustrativo — rastreabilidade de fluxo."""
    # 01 input
    o = io.open(ART / "01-input.txt", "w", encoding="utf-8")
    o.write("# ENTRADA (caso ilustrativo: transacoes de/para, same-domain)\n\n")
    N = len(next(iter(cols.values())))
    o.write("linha | " + " | ".join(f"{n:>10}" for n in cols) + "\n")
    for i in range(N):
        o.write(f"{i:5} | " + " | ".join(f"{cols[n][i]:>10}" for n in cols) + "\n")
    for n in cols:
        uni, _ = _uniques(cols[n])
        o.write(f"\n{n}: N={N} K={len(uni)} unicos={uni}\n")
    o.write(f"\nJaccard(conta_de, conta_para) = {jaccard(cols['conta_de'], cols['conta_para']):.3f}\n")
    o.close()

    # 02 particionamento (decisao)
    o = io.open(ART / "02-partition-decisao.txt", "w", encoding="utf-8")
    o.write("# PARTICIONAMENTO — greedy custo-modelado (decide por BYTES REAIS)\n")
    o.write("pool(G) sse b2_body < v0_body   (v0 = per-col real: @dict OU OBAT/HCC; b2 = uniao+streams)\n\n")
    for d in res["decisions"]:
        o.write(f"grupo candidato: {d['members']}\n")
        o.write(f"  K por coluna : {d['K_c']}\n")
        o.write(f"  K_uniao      : {d['KG']} (width {d['wG']})   Jaccard={d['jac']}\n")
        o.write(f"  v0_body (soma per-col real)         = {d['v0_body']} B\n")
        o.write(f"  b2_body (uniao 1x + streams + fram) = {d['b2_body']} B\n")
        o.write(f"  net_grupo = {d['net_group']:+.1f}%   -> POOL={d['pooled']}\n\n")
    o.close()

    # 03 OBAT/HCC da uniao (por que dedup e' nao-linear)
    members = res["decisions"][0]["members"]
    gseen, guni = {}, []
    for n in members:
        for v in cols[n]:
            if v not in guni:
                guni.append(v)
    o = io.open(ART / "03-obat-hcc-uniao.txt", "w", encoding="utf-8")
    o.write("# ARTEFATO OBAT/HCC — encode da TABELA DE UNIAO do grupo\n")
    o.write("(mostra por que o dedup e' NAO-linear: a uniao encoda perto do custo de UMA coluna)\n\n")
    for n in members:
        uni, _ = _uniques(cols[n])
        tb, _ = _tab(uni)
        o.write(f"tab({n}) : {len(uni)} unicos -> {len(tb)} B :: {tb.decode('utf-8')!r}\n")
    tabG, sideG = _tab(guni, want_side=True)
    o.write(f"tab(UNIAO): {len(guni)} unicos -> {len(tabG)} B :: {tabG.decode('utf-8')!r}\n\n")
    o.write("--- OBAT log (tokenizacao da uniao) ---\n")
    o.write(repr(sideG.obat_log) + "\n\n")
    o.write("--- HCC trace (detector composicional da uniao) ---\n")
    o.write(repr(sideG.hcc_trace) + "\n")
    o.close()

    # 04/05 blobs
    io.open(ART / "04-blob-v0.tcf.txt", "w", encoding="utf-8").write(
        "# BLOB V0 (per-column @dict) — repr byte-a-byte\n\n" + res["b0"].decode("utf-8") + "\n")
    io.open(ART / "05-blob-b2.tcf.txt", "w", encoding="utf-8").write(
        "# BLOB B2 (group-dict: meta &G + PRELUDIO + streams) — repr byte-a-byte\n\n"
        + res["bB"].decode("utf-8") + "\n")

    # 06 rt + medida
    o = io.open(ART / "06-roundtrip-medida.txt", "w", encoding="utf-8")
    o.write("# ROUND-TRIP + MEDIDA (caso ilustrativo) — decomposicao 3-vias\n\n")
    o.write(f"RT: V0={'ok' if res['rt0'] else 'FALHA'}  V1={'ok' if res['rt1'] else 'FALHA'}  "
            f"B2={'ok' if res['rtB'] else 'FALHA'}\n\n")
    o.write("baselines (body bytes):\n")
    o.write(f"  V0 (real: @dict low-card OU OBAT/HCC high-card) = {res['body0']} B\n")
    o.write(f"  V1 (per-col dict, sem cap = dict-nao-compartilhado) = {res['body1']} B\n")
    o.write(f"  B2 (group-dict compartilhado)                    = {res['bodyB']} B\n\n")
    o.write(f"  total  B2 vs V0 = {res['tot']:+.1f}%\n")
    o.write(f"  (a) dict vs OBAT/HCC (V1 vs V0)     = {res['dictgain']:+.1f}%  [ganho de USAR dict]\n")
    o.write(f"  (b) CROSS-DICT sharing (B2 vs V1)   = {res['share']:+.1f}%  [valor REAL do B2]\n")
    o.write(f"  {CN} (controle, B2 vs V0)           = {res['br']:+.1f}%\n")
    o.write(f"  lazy cross-col dict-decodes: V0={res['v0_dec']} -> B2={res['vB_dec']}\n")
    o.close()


if __name__ == "__main__":
    print(f"compressor de controle: {CN}\n")
    print("=== ILUSTRATIVO (artefatos completos em artifacts/) ===")
    ill = synth_illustrative()
    r = measure("ilustrativo de/para (N=10)", ill)
    dump_illustrative(ill, r)

    print("\n=== REAIS (Z:) ===")
    g = load_grqc()
    measure("SNAP ca-GrQc  from_node~to_node", g)
    of = load_openflights()
    measure("OpenFlights  source_airport~dest_airport",
            {"source_airport": of["source_airport"], "dest_airport": of["dest_airport"]})
    measure("OpenFlights  source_id~dest_id",
            {"source_airport_id": of["source_airport_id"], "dest_airport_id": of["dest_airport_id"]})

    print("\n=== SINTETICOS (escala / borda) ===")
    measure(">=3 col same-domain (origem/conexao/destino N=2000)", synth_3col())
    rb = measure("BORDA: uniao cruza bucket 94 (w 1->2)", synth_bucket_cross())
    print(f"     -> grupos={len(rb['groups'])}; olhar 'share' (B2 vs V1 dict): "
          f"{rb['share']:+.1f}% — se >0, o cross-dict PERDE vs dict-per-col (bucket cost).")
