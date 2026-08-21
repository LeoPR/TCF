"""Baseline probatorio do `.8` — a leitura, e a VERIFICACAO da leitura de 22/07.

O QUE ESTE LAB E'
-----------------
A rodada probatoria de `bench_perf --plan nucleo` de 2026-08-20 (a que faltava
desde 22/07) foi gravada em `experiments/results/evidencia-0.8/perf-baseline/`.
Este lab nao MEDE — ele LE as duas rodadas e testa o que se pode afirmar delas.

Owner (2026-08-20), o que autoriza e o que obriga:
  *"faz sentido fazer mesmo com as otimizacoes que tem agora, elas serviriam
  como base para as otimizacoes futuras. so' precisamos lembrar de que temos
  que repeti-las. independente disso, ja' sabariamos como o ver .8 esta'."*

AS CINCO PERGUNTAS
------------------
  P0  CONTROLE       — a matriz, o plano e o DADO sao os mesmos nas duas rodadas?
  P1  CALIBRADOR     — o fator de normalizacao esta' certo? Os caminhos de
                       REFERENCIA (stdlib, codigo identico) sao o controle.
  P2  BYTE           — o `.8` de hoje emite o mesmo wire de 22/07? Onde nao emite,
                       o tempo a mais comprou byte a menos?
  P3  PENHASCO       — o `cantoRC-both` e' um penhasco (afirmacao vigente na
                       STATUS.md) ou so' 80x mais dado?
  P4  RAZAO INTERNA  — TCF / referencia DENTRO da mesma rodada: a unica medida
                       em que a maquina cancela por construcao.

GATE DE EVIDENCIA: toda tabela impressa e' gravada em `outputs/`, e o portao no
fim compara CONJUNTOS (nem faltando, nem orfa).
"""

from __future__ import annotations

import json
import math
import statistics as st
import sys
from pathlib import Path

AQUI = Path(__file__).parent
RAIZ = AQUI.parents[5]
IN = RAIZ / "experiments/results/evidencia-0.8/perf-baseline"
OUT = AQUI / "outputs"
OUT.mkdir(parents=True, exist_ok=True)

JUL, AGO = "perf-nucleo-2026-07-22", "perf-nucleo-2026-08-20"
REFS = {"json-ref-str", "json-ref-nested", "json-ref-typed", "csv-ref"}

_buf: list[str] = []
_arquivos: set[Path] = set()


def P(txt: str = "") -> None:
    print(txt)
    _buf.append(txt)


def grava(nome: str, texto: str) -> Path:
    p = OUT / nome
    p.write_text(texto, encoding="utf-8", newline="")
    _arquivos.add(p.resolve())
    return p


def carrega(tag: str):
    regs = [json.loads(l) for l in (IN / f"{tag}.jsonl").read_text(encoding="utf-8").splitlines()
            if l.strip()]
    resumo = json.loads((IN / f"{tag}.run.json").read_text(encoding="utf-8"))
    return {r["case_id"]: r for r in regs}, resumo


def comparaveis(A, B):
    """Pares que o protocolo permite comparar: mesmo tier E mesmo n (compare.py §_protocolo_igual)."""
    for cid in sorted(set(A) & set(B)):
        a, b = A[cid], B[cid]
        ea, eb = a.get("encode"), b.get("encode")
        if a.get("status") != "ok" or b.get("status") != "ok" or not ea or not eb:
            continue
        if ea.get("tier") != eb.get("tier") or ea.get("n") != eb.get("n"):
            continue
        yield cid, a, b, ea, eb


def nucleo(r):
    """Recorte homogeneo: tcf-flat, chamada inteira, cython, sem compressao, sem knob."""
    v = r["vectors"]
    return (r.get("status") == "ok" and r.get("encode") and v["caminho"] == "tcf-flat"
            and v["granularidade"] == "call" and v.get("accel") == "cython"
            and v.get("compressao") == "none" and not v.get("knobs"))


# ══════════════════════════════════════════════════════════════════════════
A, RA = carrega(JUL)
B, RB = carrega(AGO)

P("=" * 100)
P("BASELINE PROBATORIO DO .8 — 2026-07-22 (58f893eb)  ->  2026-08-20 (6f04f3ae)")
P("=" * 100)

# ── P0. CONTROLE ─────────────────────────────────────────────────────────
P("\n" + "=" * 100)
P("P0) CONTROLE — as duas rodadas sao comparaveis?")
P("=" * 100)
matriz = RA["manifest"]["cases_sha256"] == RB["manifest"]["cases_sha256"]
plano = RA["plano"]["sha"] == RB["plano"]["sha"]
wl_dif = [cid for cid in set(A) & set(B)
          if A[cid].get("workload") and B[cid].get("workload")
          and A[cid]["workload"] != B[cid]["workload"]]
rt_mau = [cid for cid in B if B[cid].get("rt_ok") is False]
for rot, val in [("matriz de casos (cases_sha256)", matriz),
                 ("plano (sha + intencao)", plano),
                 ("DADO gerado identico (workload)", not wl_dif),
                 ("roundtrip integro hoje", not rt_mau)]:
    P(f"  {rot:<38} {'OK' if val else 'DIVERGE'}")
P(f"  {'validade dos dados':<38} 22/07={RA['status']}  20/08={RB['status']}")
P(f"  {'estabilidade termica (so AVISA)':<38} 22/07={RA['runner_thermal_status']}  "
  f"20/08={RB['runner_thermal_status']}")
P(f"  {'celulas ok':<38} 22/07={RA['n_comparaveis_ok']}  20/08={RB['n_comparaveis_ok']}"
  f"   obrigatorio-falhou: {RA['n_obrig_falhou']}/{RB['n_obrig_falhou']}")
P("\n  RESSALVA (git): entre as rodadas o `src/tcf` mudou — 258 commits, 34 tocando o")
P("  core, +2576 linhas. Isto NAO e' uma repeticao do mesmo codigo: e' a MESMA VERSAO")
P("  DE WIRE (`.8`/0.8.0) com o core evoluido. E o `tcf-8h` mudou de ROTA (e855f1c0:")
P("  encode_hierarchical -> API unica `encode`), entao aquele caminho nem sequer mede")
P("  o mesmo codigo. O harness em si e' neutro: o unico parametro removido de")
P("  `probes.py` (`probe=`) nunca foi usado por ninguem, e o warmup segue identico.")
assert matriz and plano and not wl_dif and not rt_mau, "controle P0 falhou"

# ── P1. CALIBRADOR ───────────────────────────────────────────────────────
P("\n" + "=" * 100)
P("P1) O CALIBRADOR ESTA' CALIBRANDO? — a stdlib e' o controle")
P("=" * 100)
razoes_cal = [RB["calibradores"][k]["point_ns"] / RA["calibradores"][k]["point_ns"]
              for k in RA["calibradores"] if k in RB["calibradores"]]
FATOR = st.median(razoes_cal)
PISO = RA["drift"]["noise_floor_cv"]
P(f"  calibradores C1/C2/C3: {', '.join(f'{r:.3f}' for r in razoes_cal)}  ->  fator {FATOR:.3f}")
P(f"  piso de ruido da rodada baseline: {PISO*100:.2f}%")

por_cam: dict[str, list[float]] = {}
for cid, a, b, ea, eb in comparaveis(A, B):
    por_cam.setdefault(a["vectors"]["caminho"], []).append(eb["point_ns"] / ea["point_ns"] - 1)
P(f"\n  {'caminho':<16} {'codigo':<8} {'n':>4} {'BRUTO':>9} {'apos /fator':>12}")
ref_todas: list[float] = []
for cam, ds in sorted(por_cam.items()):
    bruto = st.median(ds)
    P(f"  {cam:<16} {'STDLIB' if cam in REFS else 'TCF':<8} {len(ds):>4} "
      f"{bruto*100:>+8.1f}% {((1+bruto)/FATOR-1)*100:>+11.1f}%")
    if cam in REFS:
        ref_todas += ds
mref = st.median(ref_todas)
P(f"\n  A stdlib nao mudou de codigo entre as rodadas. Ela diz que a maquina fez")
P(f"  {1+mref:.3f} do trabalho de 22/07 (n={len(ref_todas)} celulas). O calibrador diz {FATOR:.3f}.")
P(f"  ACHADO: o calibrador SUPER-CORRIGE em {((1+mref)/FATOR-1)*100:+.1f}% — ele fabrica essa")
P("  fracao de 'regressao' em cima de todo caso. Os calibradores sao lacos apertados de")
P("  aritmetica/hash/alloc; o workload real e' construcao de string e dicionario. As duas")
P("  coisas nao escalam juntas na mesma maquina.")

# ── P2. BYTE ─────────────────────────────────────────────────────────────
P("\n" + "=" * 100)
P("P2) BYTE — o `.8` de hoje emite o mesmo wire?")
P("=" * 100)
mudou, iguais = [], 0
for cid in sorted(set(A) & set(B)):
    ba, bb = A[cid].get("bytes"), B[cid].get("bytes")
    if ba is None or bb is None:
        continue
    if ba == bb:
        iguais += 1
    else:
        mudou.append((cid, ba, bb))
P(f"  byte-identico: {iguais}   ·   byte MUDOU: {len(mudou)}")
tempos = {cid: (eb["point_ns"] / ea["point_ns"] - 1) for cid, a, b, ea, eb in comparaveis(A, B)}
P(f"\n  {'d byte':>9} {'d tempo bruto':>15}  caso")
for cid, ba, bb in sorted(mudou, key=lambda x: (x[2] - x[1]) / x[1]):
    dt = tempos.get(cid)
    P(f"  {(bb-ba)/ba*100:>+8.2f}% {('--' if dt is None else f'{dt*100:+.1f}%'):>15}  {cid[:58]}")
P("\n  Os 8 casos que mudaram de byte sao os 8 de granularidade `column` (encode de UMA")
P("  coluna). O wire de hoje traz o discriminador `B` — o modo denso bN de dominio")
P("  (ADR-0036/37/38/39), que nao existia em 22/07. Verificacao direta em `outputs/`.")

# ── P3. PENHASCO ─────────────────────────────────────────────────────────
P("\n" + "=" * 100)
P("P3) O `cantoRC-both` e' PENHASCO ou so' 80x mais dado?")
P("=" * 100)
P("  Afirmacao vigente na STATUS.md (22/07): \"a super-linearidade esta' so' no canto RxC")
P("  extremo — cantoRC-both=44.6s vs base 595ms = ~75x, o penhasco do OBAT\".")
P("  Mas `base` tem 40.000 celulas e `cantoRC-both` tem 3.200.000. Custo UNITARIO:")
resumo_p3 = {}
for tag, R in ((JUL, A), (AGO, B)):
    ln = []
    for r in R.values():
        if not nucleo(r):
            continue
        w, e, v = r["workload"], r["vectors"]["escala"], r["vectors"]
        ln.append({"pid": e["point_id"], "forma": v["forma"], "C": e["C"], "R": e["R"],
                   "L": e["L"], "K": e["K"], "cels": w["n_cells"], "bin": w["bytes_utf8"],
                   "ns": r["encode"]["point_ns"],
                   "ns_cel": r["encode"]["point_ns"] / w["n_cells"]})
    mixed = [x for x in ln if x["forma"] == "flat-mixed"]
    canto = next(x for x in mixed if x["pid"] == "cantoRC-both")
    base = next(x for x in mixed if x["pid"] == "base")
    med = st.median([x["ns_cel"] for x in mixed if x["pid"] != "cantoRC-both"])
    P(f"\n  --- {tag} ---")
    P(f"    canto vs base: tempo {canto['ns']/base['ns']:.1f}x · celulas "
      f"{canto['cels']/base['cels']:.1f}x · bytes-in {canto['bin']/base['bin']:.1f}x")
    P(f"    ns/celula: canto {canto['ns_cel']:,.0f} · base {base['ns_cel']:,.0f} · "
      f"mediana dos demais {med:,.0f}  ->  canto = {canto['ns_cel']/med:.2f}x a mediana")
    P(f"    top-3 custo unitario: " + " · ".join(
        f"{x['pid']}({x['ns_cel']:,.0f})" for x in sorted(mixed, key=lambda z: -z["ns_cel"])[:3]))
    resumo_p3[tag] = {"canto_x_mediana": round(canto["ns_cel"] / med, 3),
                      "tempo_x": round(canto["ns"] / base["ns"], 2),
                      "celulas_x": round(canto["cels"] / base["cels"], 2),
                      "linhas": ln}
P("\n  VEREDITO: o canto custa 1,00-1,02x o custo unitario mediano, nas DUAS rodadas.")
P("  Fazer 80x de trabalho em 75x de tempo e' SUB-linear. Nao ha' penhasco ali.")
P("  Quem destoa e' L512 (~3,8x a mediana) e K1 (~2,9x): VALOR LONGO e VALOR UNICO.")
for tag in (JUL, AGO):
    assert resumo_p3[tag]["canto_x_mediana"] < 1.5, f"{tag}: canto seria penhasco"

# escala com R e o RESTO fixo (o slope agregado do relatorio mistura C no eixo R)
P("\n  Escala com R isolado (C/L/K fixos) — o slope agregado do relatorio e' artefato:")
P(f"  {'rodada':<10} {'caminho':<16} {'forma':<14} {'C':>4} {'slope':>7}  serie")
slopes = []
for tag, R in ((JUL, A), (AGO, B)):
    grupos: dict[tuple, list] = {}
    for r in R.values():
        if r.get("status") != "ok" or not r.get("encode"):
            continue
        v, e = r["vectors"], r["vectors"]["escala"]
        ch = (v["caminho"], v["forma"], v["granularidade"], e["C"], e["L"], e["K"],
              v.get("accel"), v.get("compressao"), json.dumps(v.get("knobs", {}), sort_keys=True),
              json.dumps(v.get("concorrencia", {}), sort_keys=True))
        grupos.setdefault(ch, []).append((e["R"], r["encode"]["point_ns"]))
    for ch, pts in sorted(grupos.items()):
        pts = sorted(set(pts))
        if len({p[0] for p in pts}) < 3:
            continue
        xs = [math.log10(p[0]) for p in pts]
        ys = [math.log10(p[1]) for p in pts]
        n = len(xs)
        mx, my = sum(xs) / n, sum(ys) / n
        den = sum((x - mx) ** 2 for x in xs)
        sl = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den
        serie = " ".join(f"{p[0]}:{p[1]/1e6:.0f}ms" for p in pts)
        P(f"  {tag[-5:]:<10} {ch[0]:<16} {ch[1]:<14} {ch[3]:>4} {sl:>7.2f}  {serie}")
        slopes.append({"rodada": tag, "caminho": ch[0], "forma": ch[1], "C": ch[3],
                       "slope": round(sl, 3)})
P("  `json-ref-str` E' `json.dumps` — O(n) por construcao — e da' ~1,03 aqui e ~1,47 no")
P("  slope agregado do relatorio. Logo o 1,47 do `tcf-flat` la' e' o MESMO artefato.")
P("  Super-linearidade real e reproduzida: `free-text` (~1,22 nas duas rodadas).")

# ── modelo de custo ──────────────────────────────────────────────────────
P("\n" + "=" * 100)
P("P3b) ENTAO ONDE ESTA' O CUSTO? — t = a*celulas + b*bytes_in + c*unicos")
P("=" * 100)


def resolve3(M3, v3):
    M = [row[:] + [v3[i]] for i, row in enumerate(M3)]
    for c in range(3):
        p = max(range(c, 3), key=lambda r: abs(M[r][c]))
        M[c], M[p] = M[p], M[c]
        for r in range(3):
            if r != c:
                f = M[r][c] / M[c][c]
                for k in range(c, 4):
                    M[r][k] -= f * M[c][k]
    return [M[i][3] / M[i][i] for i in range(3)]


modelo = {}
for tag, R in ((JUL, A), (AGO, B)):
    pts = []
    for r in R.values():
        if not nucleo(r):
            continue
        w, e = r["workload"], r["vectors"]["escala"]
        unicos = e["C"] * max(1, min(e["R"], round(e["R"] * e["K"])))
        pts.append(((w["n_cells"], w["bytes_utf8"], unicos), r["encode"]["point_ns"],
                    e["point_id"], r["vectors"]["forma"]))
    X = [p[0] for p in pts]
    Y = [p[1] for p in pts]
    M3 = [[sum(X[k][i] * X[k][j] for k in range(len(X))) for j in range(3)] for i in range(3)]
    v3 = [sum(X[k][i] * Y[k] for k in range(len(X))) for i in range(3)]
    co = resolve3(M3, v3)
    my = sum(Y) / len(Y)
    r2 = 1 - (sum((y - sum(c * x for c, x in zip(co, xx))) ** 2 for xx, y in zip(X, Y))
              / sum((y - my) ** 2 for y in Y))
    res_canto = next((y - sum(c * x for c, x in zip(co, xx))) / y
                     for xx, y, pid, _ in pts if pid == "cantoRC-both")
    P(f"  {tag}:  a={co[0]:,.0f} ns/celula · b={co[1]:,.1f} ns/byte · "
      f"c={co[2]:,.0f} ns/UNICO  ·  R2={r2:.4f}")
    P(f"     residuo do cantoRC-both = {res_canto*100:+.1f}%  "
      f"(o modelo linear PREVE o canto — mais uma vez, nao e' penhasco)")
    modelo[tag] = {"a_ns_por_celula": round(co[0]), "b_ns_por_byte": round(co[1], 2),
                   "c_ns_por_unico": round(co[2]), "R2": round(r2, 5),
                   "residuo_canto_pct": round(res_canto * 100, 2), "n": len(pts)}
    assert abs(res_canto) < 0.05, f"{tag}: canto nao previsto pelo modelo"
P("\n  O termo por UNICO e' ~3,7x o termo por celula. Com K=1 (tudo unico) ele responde")
P("  por ~4/5 do tempo. O eixo quente do `.8` e' CARDINALIDADE (e comprimento), nao RxC.")
P("  Isso mantem o MECANISMO que a STATUS.md nomeia (indice do OBAT) e corrige o GATILHO.")

# ── P4. RAZAO INTERNA ────────────────────────────────────────────────────
P("\n" + "=" * 100)
P("P4) TCF / stdlib DENTRO da rodada — a maquina cancela por construcao")
P("=" * 100)


def indexa(R):
    out: dict[tuple, dict] = {}
    for r in R.values():
        if r.get("status") != "ok" or not r.get("encode"):
            continue
        v, e = r["vectors"], r["vectors"]["escala"]
        ch = (v["forma"], v["granularidade"], e["point_id"], e["R"], e["C"], e["L"], e["K"],
              v.get("compressao"))
        out.setdefault(ch, {})[v["caminho"]] = r
    return out


IA, IB = indexa(A), indexa(B)
P(f"  {'workload':<40} {'22/07':>8} {'20/08':>8} {'variacao':>10} {'byte tcf/json':>14}")
rz, tab4 = [], []
for ch in sorted(set(IA) & set(IB)):
    if not all("tcf-flat" in d and "json-ref-str" in d for d in (IA[ch], IB[ch])):
        continue
    ra = IA[ch]["tcf-flat"]["encode"]["point_ns"] / IA[ch]["json-ref-str"]["encode"]["point_ns"]
    rb = IB[ch]["tcf-flat"]["encode"]["point_ns"] / IB[ch]["json-ref-str"]["encode"]["point_ns"]
    by = IB[ch]["tcf-flat"]["bytes"] / IB[ch]["json-ref-str"]["bytes"]
    rot = f"{ch[0]}/{ch[2]} R={ch[3]} C={ch[4]} L={ch[5]} K={ch[6]}"
    P(f"  {rot:<40} {ra:>7.1f}x {rb:>7.1f}x {(rb/ra-1)*100:>+9.1f}% {by:>13.3f}")
    rz.append(rb / ra - 1)
    tab4.append({"workload": rot, "razao_2207": round(ra, 2), "razao_2008": round(rb, 2),
                 "variacao_pct": round((rb / ra - 1) * 100, 2), "byte_tcf_sobre_json": round(by, 4)})
P(f"\n  n={len(rz)} · mediana {st.median(rz)*100:+.1f}% · piorou em "
  f"{sum(1 for x in rz if x > 0)}/{len(rz)} workloads")
P("  Esta e' a unica afirmacao de ganho que nao depende de estimar fator nenhum.")
P(f"  POSICAO DO .8 hoje: encode {min(t['razao_2008'] for t in tab4):.0f}x a "
  f"{max(t['razao_2008'] for t in tab4):.0f}x o tempo do `json.dumps`, emitindo "
  f"{st.median([t['byte_tcf_sobre_json'] for t in tab4])*100:.0f}% dos bytes dele (mediana).")
pior_b = max(tab4, key=lambda t: t["byte_tcf_sobre_json"])
P(f"  O pior dos dois lados e' o MESMO caso: {pior_b['workload']} — "
  f"{pior_b['razao_2008']:.0f}x de tempo por apenas "
  f"{(1-pior_b['byte_tcf_sobre_json'])*100:.0f}% de byte economizado.")

# ── evidencia ────────────────────────────────────────────────────────────
grava("relatorio.txt", "\n".join(_buf) + "\n")
grava("p1-calibrador.json", json.dumps({
    "fator_calibrador": round(FATOR, 4), "razoes_calibradores": [round(r, 4) for r in razoes_cal],
    "fator_referencia_stdlib": round(1 + mref, 4), "n_celulas_referencia": len(ref_todas),
    "super_correcao_pct": round(((1 + mref) / FATOR - 1) * 100, 2),
    "piso_de_ruido_pct": round(PISO * 100, 3),
    "delta_bruto_por_caminho": {k: round(st.median(v) * 100, 2) for k, v in por_cam.items()},
}, ensure_ascii=False, indent=1))
grava("p2-bytes.json", json.dumps(
    {"byte_identico": iguais,
     "mudou": [{"caso": c, "b_2207": x, "b_2008": y, "delta_pct": round((y - x) / x * 100, 2)}
               for c, x, y in mudou]}, ensure_ascii=False, indent=1))
grava("p3-penhasco.json", json.dumps(
    {t: {k: v for k, v in d.items() if k != "linhas"} for t, d in resumo_p3.items()}
    | {"custo_unitario": {t: resumo_p3[t]["linhas"] for t in resumo_p3}, "slopes_R_isolado": slopes},
    ensure_ascii=False, indent=1))
grava("p3b-modelo-de-custo.json", json.dumps(modelo, ensure_ascii=False, indent=1))
grava("p4-razao-interna.json", json.dumps(tab4, ensure_ascii=False, indent=1))

# a verificacao direta do `B`: o wire da coluna que mudou de byte
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "scripts"))
import bench_perf.synth as SY                                    # noqa: E402
from bench_perf.runner import SEED                               # noqa: E402
from tcf import encode, decode                                   # noqa: E402

col = SY.synth_pivot(2000, 8, 32, 0.1, "flat-mixed", seed=SEED)["col00"]
w = encode(col)
assert decode(w) == col, "RT do caso C8-col0 falhou"
grava("c8-col0.tcf", w)
grava("c8-col0.entrada.json", json.dumps(col[:40], ensure_ascii=False, indent=1))
grava("c8-col0.roundtrip.json", json.dumps(decode(w)[:40], ensure_ascii=False, indent=1))
P("\n" + "=" * 100)
P("VERIFICACAO DIRETA do caso que mudou de byte (C8-col0, R=2000, 200 unicos)")
P("=" * 100)
P(f"  22/07: 14.646 B   ·   hoje: {len(w.encode()):,} B   ·   cabecalho {w[:11]!r}")
P("  O discriminador `B` (denso bN de dominio) nao existia em 22/07 — o ganho de byte")
P("  esta' NO WIRE, verificavel, nao inferido do tempo.")
assert len(w.encode()) == 9313, "o caso C8-col0 nao reproduz o byte registrado na rodada"
grava("relatorio.txt", "\n".join(_buf) + "\n")

# ── portao anti-orfao ────────────────────────────────────────────────────
achados = {p.resolve() for p in OUT.rglob("*") if p.is_file()}
faltando, orfas = _arquivos - achados, achados - _arquivos
assert not faltando, f"EVIDENCIA FALTANDO: {faltando}"
assert not orfas, f"EVIDENCIA ORFA: {orfas}"
print(f"\n-> {len(achados)} arquivos em outputs/ (portao: nem faltando, nem orfao)")
