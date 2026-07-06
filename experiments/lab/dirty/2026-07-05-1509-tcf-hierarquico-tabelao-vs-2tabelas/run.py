"""run.py — experimento auto-contido: JSON hierárquico → TCF (tabelão A vs duas tabelas B).

Rastreio em 4 estágios (a pedido do owner): ENTRADA → TRADUÇÃO (JSON→tabela) → TCF ADAPTADO (encode) →
DECODE (volta pra ver se funciona). Cada estágio vira artefato NUMERADO em artifacts/. Auto-contido:
usa só `hierlib.py` (local) + `tcf` (biblioteca; NÃO toca src). `python run.py` regenera tudo.

    python experiments/lab/dirty/2026-07-05-1509-tcf-hierarquico-tabelao-vs-2tabelas/run.py
"""
from __future__ import annotations
import csv
import io
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(HERE))
from tcf import encode, decode, SideOutputs      # noqa: E402
import brotli                                     # noqa: E402
import hierlib as H                               # noqa: E402

ART = HERE / "artifacts"
ART.mkdir(exist_ok=True)


def br(s): return len(brotli.compress(s.encode(), quality=11))
def write(name, text): (ART / name).write_text(text, encoding="utf-8", newline="\n")


def csv_text(table):
    buf = io.StringIO(); w = csv.writer(buf, lineterminator="\n"); cols = list(table)
    w.writerow(cols)
    for i in range(len(next(iter(table.values())))):
        w.writerow([table[c][i] for c in cols])
    return buf.getvalue()


def trace_block(label, table):
    side = SideOutputs(); tcf = encode(table, side_outputs=side)
    L = [f"# TRACE OBAT/HCC — {label} — por coluna", ""]
    per = side.per_col or {}
    for c in table:
        s = per.get(c); u = len(set(table[c]))
        if s is None:
            L.append(f"col({c}): {u} unicos :: (sem per_col)"); continue
        cad = (s.cadence_info or {}).get("rule_hit"); srle = len(s.seq_rle_runs or [])
        L.append(f"col({c}): {u} unicos -> {s.body_bytes} B  "
                 f"[cadence={s.cadence_detected}({cad}) min_len={s.min_len} hint={s.obat_used_hint} seq_rle_runs={srle}]")
        L.append(f"  --- OBAT log ---\n{(s.obat_log or '').rstrip()}")
        L.append(f"  --- HCC trace ---\n{(s.hcc_trace or '').rstrip()}\n")
    return tcf, "\n".join(L) + "\n"


def main():
    src = json.loads((HERE / "inputs" / "S3-equipment-with-day.json").read_text(encoding="utf-8"))
    equipment, day = src["equipment"], src["day"]

    # ===== ESTÁGIO 1 — ENTRADA =====
    write("01-entrada-S3.json", json.dumps(src, ensure_ascii=False, indent=2) + "\n")

    # ===== ESTÁGIO 2 — TRADUÇÃO (JSON aninhado → tabela(s)) =====
    tA, schemaA = H.to_tabelao(equipment, day)
    t0, t1, manifest = H.to_two(equipment, day)
    write("02-traducao-A-tabelao.csv", csv_text(tA))
    write("02-traducao-B-T0-equipment.csv", csv_text(t0))
    write("02-traducao-B-T1-day.csv", csv_text(t1))
    write("02-traducao-B-manifest.txt",
          json.dumps(manifest, ensure_ascii=False, indent=2) + "\n\ncompacto: " + H.manifest_text(manifest) + "\n")
    write("02-traducao-A-schema.txt",
          json.dumps(schemaA, ensure_ascii=False, indent=2) + "\n\ncompacto: " + H.schema_text(schemaA) + "\n")

    # ===== ESTÁGIO 3 — TCF ADAPTADO (encode) + trace de como foi construído =====
    tcfA, traceA = trace_block("A · tabelão", tA)
    tcfT0, traceT0 = trace_block("B · T0-equipment", t0)
    tcfT1, traceT1 = trace_block("B · T1-day", t1)
    write("03-tcf-adaptado-A.tcf.txt", tcfA)
    write("03-tcf-adaptado-B-T0.tcf.txt", tcfT0)
    write("03-tcf-adaptado-B-T1.tcf.txt", tcfT1)
    write("03-trace-A-obat-hcc.txt", traceA)
    write("03-trace-B-obat-hcc.txt", traceT0 + "\n" + ("=" * 70) + "\n" + traceT1)

    # ===== ESTÁGIO 4 — DECODE (volta pra ver se funciona) =====
    decA = decode(tcfA); reconA = H.from_tabelao(decA, schemaA)[0]
    decT0, decT1 = decode(tcfT0), decode(tcfT1)
    reconB = H.from_two(decT0, decT1, manifest)[0]
    tblA_ok = decA == {k: list(map(str, v)) for k, v in tA.items()}
    jsonA_ok = reconA == src
    jsonB_ok = reconB == src
    D = ["# DECODE — o caminho de volta (decode → reconstrução → comparação com a ENTRADA)", "",
         "## A · tabelão", f"decode(tcf) == tabela de strings ? {'OK' if tblA_ok else 'MISMATCH'}",
         f"from_tabelao(decode) == JSON de entrada ? {'OK' if jsonA_ok else 'MISMATCH'}",
         "--- JSON reconstruído a partir do decode de A (deve ser idêntico à entrada) ---",
         json.dumps(reconA, ensure_ascii=False, indent=2), "",
         "## B · duas tabelas",
         f"from_two(decode T0, decode T1) == JSON de entrada ? {'OK' if jsonB_ok else 'MISMATCH'}",
         "--- JSON reconstruído a partir do decode de B ---",
         json.dumps(reconB, ensure_ascii=False, indent=2), ""]
    if not (jsonA_ok and jsonB_ok):
        D.append("!! MISMATCH — entrada original p/ comparação:")
        D.append(json.dumps(src, ensure_ascii=False, indent=2))
    write("04-decode-roundtrip.txt", "\n".join(D) + "\n")

    # ===== ESTÁGIO 5 — BYTES (2 regimes, M=1/M=3) =====
    NL = "\n"; lines = ["# BYTES (brotli q11) — A (tabelão) vs B (duas tabelas)",
                        "PLANO = só a tabela.  RECONSTRUÇÃO = + schema/manifest p/ árvore JSON.", ""]
    for M in (1, 3):
        docs = H.synth_docs(day, M)
        A, schA = H.stack_tabelao(docs); b0, b1, man = H.stack_two(docs)
        A_tcf = encode(A); b1_nofk = {k: v for k, v in b1.items() if k != "eq_fk"}
        Bdata = encode(b0) + NL + encode(b1_nofk)
        Bfull = H.manifest_text(man) + NL + encode(b0) + NL + encode(b1_nofk)
        A_recon = H.schema_text(schA) + NL + A_tcf
        lines += [f"## M={M} × {len(day)} pontos = {M*len(day)} linhas",
                  f"  A (sem schema)              : {br(A_tcf):4d} br",
                  f"  B-dados (T0+T1, sem manifest): {br(Bdata):4d} br   [PLANO]",
                  f"  A + schema                  : {br(A_recon):4d} br",
                  f"  B + manifest                : {br(Bfull):4d} br   [RECONSTRUÇÃO]",
                  f"  -> plano: {'A' if br(A_tcf) < br(Bdata) else ('empate' if br(A_tcf) == br(Bdata) else 'B')}"
                  f"  | reconstrução: {'A' if br(A_recon) < br(Bfull) else 'B'}", ""]
    write("05-bytes-medida.txt", "\n".join(lines) + "\n")

    print("Artefatos (estágios) em", ART)
    for p in sorted(ART.iterdir()):
        print(f"  {p.name:34s} {p.stat().st_size:6d} B")
    print("\nDECODE:", "A e B reconstroem o JSON de entrada (OK)" if (jsonA_ok and jsonB_ok) else "!! ver 04-decode-roundtrip.txt")


if __name__ == "__main__":
    main()
