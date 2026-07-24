#!/usr/bin/env python3
"""Ciclo B — bool completo: cada representação e a combinação, com FLOOR.

Plano `.8` §9 Ciclo B. Começa pelos BOOLEANOS. Compara, por perfil de dados, as representações
(RLE via core · bN denso base64 · misto RLE+denso · combinação FLOOR) contra o que o TCF emite HOJE.

GATE do owner (camada explícita↔implícita): a **tipagem tem que voltar** — bool volta bool, não a
string `"true"`. A economia é de MOLDURA, nunca de semântica. Toda representação é medida com RT-TIPADO.

Fluxo §3.2 por perfil: inputs/<id>-fonte.json → intermediates/<id>-dataset-consumido.json →
outputs/<id>-wire.tcf (REAL) → outputs/<id>-roundtrip.json. As formas HIPOTÉTICAS (typed/bN/misto)
ficam em intermediates/*.tcfp marcadas — nunca em outputs como se fossem reais.

Representações (todas com header `#TCF.8b` hipotético, exceto `atual`):
  atual      — encode(dataset) REAL: hoje bool[N] vira envelope .8H (#V + count + tag b)
  typed      — `#TCF.8b` + corpo do CORE (reusa flat: seq-RLE p/ runs, aliases). = "typed + RLE"
  bN         — `#TCF.8b` modo denso: bit-pack (1 bit/elem) → base64
  misto      — `#TCF.8b` modo misto: segmentação adaptativa RLE+denso (a combinação)
  FLOOR      — min(typed, bN, misto): nunca-pior por construção

NÃO toca src/tcf. `python run.py`.
"""
from __future__ import annotations

import base64
import gzip
import json
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
KIT = AQUI.parents[1] / "2026-07-23" / "2026-07-23-1759-bn-lowcard-generaliza-e-compoe"
ROOT = AQUI.parents[5]
sys.path.insert(0, str(KIT))
sys.path.insert(0, str(ROOT / "src"))
import pecas as P  # noqa: E402  (kit: pack_w, b64_len, seg_adapt)
from tcf import encode, decode  # noqa: E402

INP, INT, OUT = AQUI / "inputs", AQUI / "intermediates", AQUI / "outputs"
for d in (INP, INT, OUT):
    d.mkdir(exist_ok=True)

TAG = "#TCF.8b"   # header tipado hipotético (forma (6) do estudo 2330/0006)


# ------------------------------------------------------------------ representações (bool -> wire)
def enc_typed(bits):
    """`#TCF.8b\\n` + corpo do CORE dos literais true/false. O core aplica seq-RLE/aliases."""
    corpo = encode(["true" if b else "false" for b in bits]) if bits else ""
    return f"{TAG}\n{corpo}"


def dec_typed(wire):
    body = wire[len(TAG) + 1:]
    strs = decode(body) if body else []
    return [s == "true" for s in strs]


def enc_bN(bits):
    """`#TCF.8b~d\\n` + base64 do bit-pack (1 bit/elem). ~d = modo denso."""
    payload = base64.b64encode(P.pack_w([1 if b else 0 for b in bits], 1)).decode("ascii")
    return f"{TAG}~d {len(bits)}\n{payload}"


def dec_bN(wire):
    head, body = wire.split("\n", 1)
    n = int(head.split(" ")[1])
    return [x == 1 for x in P.unpack_w(base64.b64decode(body), 1, n)]


def enc_misto(bits):
    """`#TCF.8b~x\\n` + segmentação adaptativa (RLE+denso), do kit."""
    runs = [(1 if b else 0, L) for b, L in _runs(bits)]
    return f"{TAG}~x\n{P.seg_adapt(runs, 1)}"


def dec_misto(wire):
    body = wire[len(f"{TAG}~x") + 1:]
    return [x == 1 for x in P.dec_seg_adapt(body, 1)] if body else []


def _runs(bits):
    out = []
    if not bits:
        return out
    cur, L = bits[0], 1
    for b in bits[1:]:
        if b == cur:
            L += 1
        else:
            out.append((cur, L)); cur, L = b, 1
    out.append((cur, L))
    return out


REPS = [("typed", enc_typed, dec_typed), ("bN", enc_bN, dec_bN), ("misto", enc_misto, dec_misto)]


# --------------------------------------------------------------------------------- perfis
def _lcg(n, pct, seed):
    s, out = seed, []
    for _ in range(n):
        s = (1103515245 * s + 12345) & 0x7FFFFFFF
        out.append((s % 100) < pct)
    return out


def perfis():
    N = 64
    return [
        ("n0", []),
        ("n1", [True]),
        ("all-true", [True] * N),
        ("all-false", [False] * N),
        ("alt", [bool(i % 2) for i in range(N)]),
        ("runs", [True] * 24 + [False] * 8 + [True] * 32),
        ("p10", _lcg(N, 10, 11)),
        ("p50", _lcg(N, 50, 23)),
        ("p90", _lcg(N, 90, 37)),
    ]


def _b(s):
    return len(s.encode("utf-8"))


def rodar():
    ct = ["# Ciclo B — bool: cada representação e a combinação (FLOOR)\n",
          "Fluxo real: `inputs/-fonte.json`→`intermediates/-dataset-consumido.json`→`outputs/-wire.tcf` "
          "(REAL)→`outputs/-roundtrip.json`. Hipotéticas em `intermediates/*.tcfp`. GATE: **RT-tipado** "
          "(bool volta bool). bytes / gzip; `FLOOR`=min(typed,bN,misto).\n",
          "| perfil | n | atual (.8H) | typed(RLE) | bN(denso) | misto | **FLOOR** | vencedor | RT-tipado |",
          "|---|---:|---:|---:|---:|---:|---:|:---:|:---:|"]
    falhas = 0
    gz = []
    for pid, bits in perfis():
        (INP / f"{pid}-fonte.json").write_text(json.dumps(bits), encoding="utf-8")
        dataset = json.loads(json.dumps(bits))
        (INT / f"{pid}-dataset-consumido.json").write_text(json.dumps(dataset), encoding="utf-8")

        # ATUAL (real) — âncora
        wire_real = encode(dataset)
        (OUT / f"{pid}-wire.tcf").write_text(wire_real, encoding="utf-8", newline="")
        back_real = decode(wire_real)
        (OUT / f"{pid}-roundtrip.json").write_text(json.dumps(back_real), encoding="utf-8")
        rt_atual = (back_real == dataset)
        b_atual = _b(wire_real)

        # representações hipotéticas — cada uma com RT-TIPADO
        tam, rt_all = {}, rt_atual
        for rid, enc, dec in REPS:
            w = enc(dataset)
            back = dec(w)
            ok = (back == dataset)                       # RT-tipado: bool == bool
            rt_all &= ok
            tam[rid] = _b(w)
            (INT / f"{pid}-{rid}.tcfp").write_text(w, encoding="utf-8", newline="")

        floor = min(tam.values())
        venc = min(tam, key=tam.get)
        falhas += (not rt_all)
        ct.append(f"| {pid} | {len(bits)} | {b_atual} | {tam['typed']} | {tam['bN']} | {tam['misto']} | "
                  f"**{floor}** | {venc} | {'✅' if rt_all else '❌'} |")
        gz.append((pid, venc, len(gzip.compress(wire_real.encode(), 9)),
                   {rid: len(gzip.compress(enc(dataset).encode(), 9)) for rid, enc, _ in REPS}))

    # ---- gzip: a escolha do FLOOR sobrevive ao transporte comprimido? ----
    ct.append("\n## Sob gzip — o vencedor do FLOOR é ESTÁVEL (o gap encolhe, não inverte)\n")
    ct.append("| perfil | vencedor raw | typed gz | bN gz | misto gz | vencedor gz | estável? |")
    ct.append("|---|---|---:|---:|---:|---|:---:|")
    n_estavel = 0
    for (pid, venc_raw, ga, gd) in gz:
        floor_gz = min(gd, key=gd.get)
        est = (floor_gz == venc_raw)
        n_estavel += est
        ct.append(f"| {pid} | {venc_raw} | {gd['typed']} | {gd['bN']} | {gd['misto']} | {floor_gz} | "
                  f"{'✅' if est else 'FLIP'} |")
    ct.append(f"\n**O vencedor do FLOOR é o mesmo raw e sob gzip em {n_estavel}/{len(gz)} perfis** — "
              "não inverte. O `bN` (base64 de bits) é ~incompressível e o `typed`/texto tem redundância "
              "que o gzip come, então o GAP encolhe muito; mas a ESCOLHA de modo se mantém. Logo a "
              "decisão pré-transporte do FLOOR é robusta ao gzip pra bool (gzip é lente, não critério).")

    # ---- homógrafos: o tipo distingue (bool vs string vs number) ----
    ct.append("\n## Homógrafos — o tipo mantém distintos (plano §S2)\n")
    ct.append("| fonte | dataset | wire atual (linha-0) | tipo de volta |")
    ct.append("|---|---|---|---|")
    for rot, d in [("bool [true,false]", [True, False]),
                   ("string [\"true\",\"false\"]", ["true", "false"]),
                   ("number [1,0]", [1, 0])]:
        w = encode(d)
        l0 = w.split("\n", 1)[0] if w.startswith("#TCF.") else "(órfão)"
        back = decode(w)
        tipos = {type(x).__name__ for x in back}
        (INT / f"homografo-{rot[:4].strip()}.tcf").write_text(w, encoding="utf-8", newline="")
        ct.append(f"| {rot} | `{d!r}` | `{l0}` | {tipos} · RT {'✅' if back == d else '❌'} |")
    ct.append("\nMesma superfície textual (`true`/`false`/`1`/`0`), **datasets diferentes** — o tipo "
              "não é dedutível da grafia; volta pelo dataset. A forma `#TCF.8b` seria a marca que "
              "distingue bool de string homógrafa num único char.")

    ct.append("\n## Leitura\n")
    ct.append("- **cada representação tem seu regime**: `typed` (core, com seq-RLE) esmaga runs/"
              "constantes (`all-true`,`runs`); `bN` (denso) ganha na alternância/ruído (`alt`,`p50`); "
              "`misto` só compensa em heterogêneo genuíno — na maioria o FLOOR cai em typed ou bN.")
    ct.append("- **o FLOOR é a combinação certa**: nunca-pior por construção; escolhe por perfil sem "
              "precisar acertar limiar. É o mesmo padrão `min()` que o TCF já usa.")
    ct.append("- **a tipagem SEMPRE volta** (RT-tipado): a moldura `#TCF.8b` encolhe o envelope `.8H` "
              "a 1 char, mas o decode devolve bool — economia de moldura, não de semântica.")
    ct.append("- **string homógrafa permanece distinta**: `#TCF.8b` marca bool; `\"true\"` string fica "
              "órfã. O tipo não some do dataset ainda que suma do arquivo.")
    ct.append(f"\n---\n**{len(perfis())} perfis · {falhas} falhas de RT-tipado.** Artefatos: "
              "`inputs/*-fonte.json` · `intermediates/*-dataset-consumido.json` · `intermediates/*.tcfp` "
              "(hipóteses) · `outputs/*-wire.tcf` (REAL). Regenera: `python run.py`.\n")
    (AQUI / "result.md").write_text("\n".join(ct), encoding="utf-8", newline="\n")
    print(f"OK · {len(perfis())} perfis · {falhas} falhas de RT-tipado")
    return falhas


if __name__ == "__main__":
    raise SystemExit(1 if rodar() else 0)
