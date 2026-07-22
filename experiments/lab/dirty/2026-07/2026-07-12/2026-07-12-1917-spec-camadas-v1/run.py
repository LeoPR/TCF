"""Lab spec-camadas v1 — as 3 FORMAS / 6 CAMADAS do spec, MEDIDAS + RT-PROVADAS.

    data/hora : 2026-07-12 19:17
    versão    : v1
    nome      : spec-camadas
    ticket    : T-SPEC-DEEPDIVE-08 §4-ter
    owner-req : "eu quero VER os dados; só dizer que funciona não é evidência —
                registrar como contra-prova de experimentação. Artifacts com
                amostra do input, debug do fluxo/núcleo, output E a contra-prova
                de retorno ao dado original."

HIPÓTESE (owner 2026-07-12): o spec pode ser tratado em 3 formas —
  A) ENTRADA total  : transforma antes, o núcleo nem trabalha (= nature HOJE)
  B) PARALELA       : núcleo trabalha (dado limpo), depois troca base-94 nas REFERÊNCIAS
  C) MISTO          : limpa na entrada (o núcleo acha padrões) + troca na saída
6 camadas: limpeza(máscara) · derivação(DV) · pré-forma(ordem/delta) · núcleo ·
troca-refs · saída/header. Decode: "expande base-94 -> leva as chaves" (-> delta
-> zfill -> DV -> máscara).

MÉTODO: cada degrau S1-S5 é uma transformação de coluna. Medimos os bytes pelo
pipeline REAL (encode -> emitted_bytes) E PROVAMOS o round-trip end-to-end:
  original --transform--> col --tcf.encode--> blob --tcf.decode--> col'
           --untransform--> reconstruído  ==?  original   (assert, com amostras)
NENHUM byte é reportado sem o RT do degrau VERDE (§RT). Artefatos escritos em
artifacts/: input, flow-debug (SideOutputs núcleo), output-blobs, rt-counterproof.
§2.3: CPF efêmero (gerado, não salvo); amostras de CPF MASCARADAS no artefato.
"""
from __future__ import annotations

import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from dataset_reader import DatasetReader  # noqa: E402
from tcf import decode, encode  # noqa: E402
from tcf.side_outputs import SideOutputs  # noqa: E402

HERE = Path(__file__).parent
ART = HERE / "artifacts"
# Alfabeto MARKER-SAFE (base-62, sem chars estruturais do TCF) — a nature real usa
# BASE94 que INCLUI '^' (marcador de ref do HCC); um corpo base-94 começando com '^'
# QUEBRA o decode em modo tcf/dict (BUG-15, achado por ESTE lab via RT counter-proof).
# Pra medir o CONCEITO das camadas sem tropeçar no BUG-15, o lab usa base-62; a
# densidade quase não muda nas magnitudes aqui (12 díg -> 7 chars nos dois). A nature
# de produção precisa do BUG-15 corrigido pra usar o alfabeto cheio.
SAFE = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
B = len(SAFE)
_ALPHA_IDX = {c: i for i, c in enumerate(SAFE)}
DBG: list[str] = []


# --- base-94 variável (int <-> str), reversível ---
def b94(n: int) -> str:
    if n == 0:
        return SAFE[0]
    neg, n = n < 0, abs(n)
    out = []
    while n:
        n, r = divmod(n, B)
        out.append(SAFE[r])
    return ("-" if neg else "") + "".join(reversed(out))  # base-62 SAFE


def unb94(s: str) -> int:
    neg = s.startswith("-")
    if neg:
        s = s[1:]
    n = 0
    for c in s:
        n = n * B + _ALPHA_IDX[c]
    return -n if neg else n


# --- DV mod-11 (CPF/CNPJ) pra rederivar na contra-prova ---
def cpf_dv(body9: str) -> str:
    ds = [int(c) for c in body9]
    d1 = (sum(d * w for d, w in zip(ds, range(10, 1, -1))) * 10) % 11 % 10
    d2 = (sum(d * w for d, w in zip(ds + [d1], range(11, 1, -1))) * 10) % 11 % 10
    return f"{d1}{d2}"


def cnpj_dv(body12: str) -> str:
    d = [int(c) for c in body12]
    def dv(ds, ws):
        r = sum(x * w for x, w in zip(ds, ws)) % 11
        return 0 if r < 2 else 11 - r
    w1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    w2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    a = dv(d, w1)
    b = dv(d + [a], w2)
    return f"{a}{b}"


def cpf_mask(body9: str) -> str:
    return f"{body9[:3]}.{body9[3:6]}.{body9[6:9]}-{cpf_dv(body9)}"


def cnpj_mask(body12: str) -> str:
    return f"{body12[:2]}.{body12[2:5]}.{body12[5:8]}/{body12[8:12]}-{cnpj_dv(body12)}"


def col_bytes_side(values):
    side = SideOutputs()
    blob = encode({"c": list(values)}, side_outputs=side)
    return side.per_col["c"].emitted_bytes, side.per_col["c"].emitted_mode, blob, side


def degraus(bodies: list[str], mask_fn, blen: int):
    """bodies = corpos SÓ-dígitos (sem máscara/DV). Retorna masked + os 5 degraus,
    cada um com a fn que RECONSTRÓI o original a partir da coluna DECODADA."""
    ints = [int(b) for b in bodies]
    masked = [mask_fn(b) for b in bodies]

    def rc_masked(col):
        return list(col)

    def rc_clean(col):
        return [mask_fn(b.zfill(blen)) for b in col]

    def rc_delta(col):
        acc = int(col[0]); out = [mask_fn(str(acc).zfill(blen))]
        for d in col[1:]:
            acc += int(d); out.append(mask_fn(str(acc).zfill(blen)))
        return out

    def rc_b94(col):
        return [mask_fn(str(unb94(x)).zfill(blen)) for x in col]

    def rc_d94(col):
        acc = unb94(col[0]); out = [mask_fn(str(acc).zfill(blen))]
        for x in col[1:]:
            acc += unb94(x); out.append(mask_fn(str(acc).zfill(blen)))
        return out

    return masked, [
        ("S1 masked (baseline)",       masked,                                             rc_masked),
        ("S2 clean (mask+DV out)",     bodies,                                             rc_clean),
        ("S3 clean+delta",             [str(ints[0])] + [str(b - a) for a, b in zip(ints, ints[1:])], rc_delta),
        ("S4 base94 absoluto (=hoje)", [b94(i) for i in ints],                             rc_b94),
        ("S5 delta->base94 (misto)",   [b94(ints[0])] + [b94(b - a) for a, b in zip(ints, ints[1:])], rc_d94),
    ]


def run_regime(name, bodies, mask_fn, blen, rt_log, byte_log, blob_log,
               debug_for=("S3 clean+delta", "S5 delta->base94 (misto)")):
    masked, steps = degraus(bodies, mask_fn, blen)
    rt_log.append(f"\n## {name}  (n={len(bodies)})")
    byte_rows = []
    for label, col, reconstruct in steps:
        by, mode, blob, side = col_bytes_side(col)
        decoded = decode(blob)["c"]
        recon = reconstruct(decoded)
        ok = recon == masked
        rt_log.append(f"  {label:28} bytes={by:>6} ({mode:5}) RT={'OK' if ok else 'FAIL!!'}")
        if not ok:
            for i, (a, b) in enumerate(zip(masked, recon)):
                if a != b:
                    rt_log.append(f"      DIVERGE i={i}: orig={a!r} recon={b!r}")
                    break
        assert ok, f"{name}/{label}: RT FAIL — byte NAO reportado (§RT)"
        byte_rows.append((label, by, mode))
        blob_log.append(f"[{name} / {label}]  {by}B {mode}")
        blob_log.append("  input[:3] : " + " | ".join(repr(x) for x in col[:3]))
        blob_log.append("  blob head : " + repr(blob[:80]))
        blob_log.append("  decode[:3]: " + " | ".join(repr(x) for x in decoded[:3]))
        blob_log.append("  recon[:3] : " + " | ".join(repr(x) for x in recon[:3]) + "\n")
        if label in debug_for:
            pc = side.per_col["c"]
            DBG.append(f"[{name} / {label}]  modo={mode}  bytes={by}")
            DBG.append(f"  cadence_detected={pc.cadence_detected} obat_used_hint={pc.obat_used_hint}")
            runs = pc.seq_rle_runs or []
            DBG.append(f"  seq_rle_runs={len(runs)} :: {runs[:3]}")
            for tag, txt in (("obat_log", pc.obat_log), ("hcc_trace", pc.hcc_trace)):
                DBG.append(f"  {tag}[:4]:")
                for ln in (txt or "").splitlines()[:4]:
                    DBG.append(f"    {ln}")
            DBG.append("")
    byte_log[name] = byte_rows
    return masked


def main() -> int:
    ART.mkdir(exist_ok=True)
    rt_log = ["# 04 — CONTRA-PROVA de round-trip (decode -> reconstrói -> == original)", "",
              "Cada degrau: original --transform--> col --encode--> blob --decode--> col'",
              "--untransform--> reconstruído. RT=OK sse reconstruído == original.",
              "NENHUM byte foi reportado sem este RT verde (§RT)."]
    blob_log = ["# 03 — OUTPUT (amostras de blob) + input + decode + reconstrução", ""]
    input_log = ["# 01 — INPUT (amostras do dado que entrou)",
                 "§2.3: CPF efêmero; amostras de CPF MASCARADAS.", ""]
    byte_log: dict = {}

    r = DatasetReader("receita-cnpj")
    try:
        rows = r.rows("estabelecimentos", limit=5000)
    finally:
        r.close()
    cnpj = [x["cnpj"] for x in rows]
    cnpj_bodies = ["".join(c for c in v if c.isdigit())[:12] for v in cnpj]
    idx = list(range(len(cnpj))); random.Random(20260712).shuffle(idx)
    cnpj_shuf_bodies = [cnpj_bodies[i] for i in idx]

    input_log.append("## CNPJ real (receita, 5000, PK-sorted) — não-PII (registro público)")
    for v in cnpj[:5]:
        input_log.append(f"    {v}")
    fc = Counter(b[8:12] for b in cnpj_bodies)
    input_log.append(f"  filial '0001' = {100*fc['0001']/len(cnpj):.1f}%  (enum, não 4 díg livres)\n")

    run_regime("CNPJ ordenado", cnpj_bodies, cnpj_mask, 12, rt_log, byte_log, blob_log)
    run_regime("CNPJ embaralhado", cnpj_shuf_bodies, cnpj_mask, 12, rt_log, byte_log, blob_log)

    rng = random.Random(20260601)
    N = 500
    rand_bodies = [f"{rng.randint(0, 999999999):09d}" for _ in range(N)]
    start = rng.randint(0, 999000000)
    clust_bodies = [f"{start + i*3:09d}" for i in range(N)]
    input_log.append("## CPF sintético (efêmero §2.3, 500) — MASCARADO no display")
    input_log.append(f"  RANDOM    corpos aleatórios (ex. corpo termina …{rand_bodies[0][-2:]})")
    input_log.append(f"  CLUSTERED base sequencial +3, prefixo '{clust_bodies[0][:6]}' — corpo +3/linha")
    input_log.append("  (corpos completos NÃO gravados — §2.3)\n")
    run_regime("CPF random", rand_bodies, cpf_mask, 9, rt_log, byte_log, blob_log)
    run_regime("CPF clustered", clust_bodies, cpf_mask, 9, rt_log, byte_log, blob_log)

    (ART / "01-input-samples.txt").write_text("\n".join(input_log), encoding="utf-8", newline="\n")
    (ART / "02-flow-debug.txt").write_text(
        "# 02 — DEBUG do FLUXO / NÚCLEO (SideOutputs: modo, cadência, seq-RLE, OBAT, HCC)\n\n"
        + "\n".join(DBG), encoding="utf-8", newline="\n")
    (ART / "03-output-blobs.txt").write_text("\n".join(blob_log), encoding="utf-8", newline="\n")
    (ART / "04-rt-counterproof.txt").write_text("\n".join(rt_log), encoding="utf-8", newline="\n")

    def tbl():
        L = ["# 05 — LADDER de bytes (todos com RT verde)", "",
             "| degrau | CNPJ ord | CNPJ shuf | CPF rand | CPF clust |", "|---|---:|---:|---:|---:|"]
        for i in range(5):
            lab = byte_log["CNPJ ordenado"][i][0]
            cells = [byte_log[k][i][1] for k in
                     ("CNPJ ordenado", "CNPJ embaralhado", "CPF random", "CPF clustered")]
            L.append(f"| {lab} | " + " | ".join(str(c) for c in cells) + " |")
        return L
    (ART / "05-ladder-bytes.txt").write_text("\n".join(tbl()), encoding="utf-8", newline="\n")

    result = ["# spec-camadas v1 — result", "",
              "3 formas do owner (A entrada / B paralela-refs / C misto) em 5 degraus,",
              "**cada degrau com RT end-to-end PROVADO** (artifacts/04). Bytes = emitted_bytes real.",
              ""] + tbl() + ["",
              "## Achados (contra-prova em artifacts/)",
              "1. **S5 (forma C, misto) é a única sempre-boa**: CNPJ ord 14270 (−56%), shuf 32408",
              "   (−22%), CPF clust 14 (−98.7%); só perde por pouco no random (3207 vs S4 2971).",
              "2. **CPF clustered → 14B**: delta constante +3 vira RLE (ver seq_rle_runs, artifacts/02).",
              "3. **Máscara tem valor estrutural**: S2 (limpeza isolada) PIORA o CNPJ (+64%) — o split",
              "   usa a pontuação como separador. Camadas NÃO-monotônicas → escolha por-coluna, medida.",
              "4. **RT: 5 degraus × 4 regimes = 20/20 VERDE** (artifacts/04) — a contra-prova do dado.",
              "5. Máquina: S3/S5 exigem spec ESTATAL por coluna (delta usa a linha anterior) — o",
              "   encode_value per-value de hoje não expressa → capacidade nova 'column-wise nature'.",
              ""]
    (HERE / "result.md").write_text("\n".join(result), encoding="utf-8", newline="\n")
    print("RT: 20/20 verde (5 degraus x 4 regimes) — artifacts/04-rt-counterproof.txt")
    print(f"artefatos -> {ART}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
