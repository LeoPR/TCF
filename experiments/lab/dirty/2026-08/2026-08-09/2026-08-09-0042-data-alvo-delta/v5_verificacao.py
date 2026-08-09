"""Os 5 achados da caçada, testados contra a v5. `python v5_verificacao.py`

Cada bloco reproduz o achado com o mesmo método que os caçadores usaram, e afirma que a
v5 o fecha. Se algum voltar, este script falha alto.

Fonte dos achados: `outputs/cacada-achados-brutos.json` (12 brutos, 5 distintos).
"""
from __future__ import annotations

import csv
import datetime as _dt
import json
import pathlib
import sys
import time

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(RAIZ))

import detector_v5 as V5  # noqa: E402
from tcf import decode, encode  # noqa: E402
from tcf.side_outputs import SideOutputs  # noqa: E402

B = _dt.date(2026, 1, 1)
RES = []


def _ok(n, titulo, passou, detalhe=""):
    RES.append({"n": n, "titulo": titulo, "passou": bool(passou), "detalhe": detalhe})
    print(f"  #{n} {'OK  ' if passou else 'FALHOU'} {titulo}")
    if detalhe:
        for ln in detalhe.strip().split("\n"):
            print(f"        {ln}")


def uteis(n, feriados=0):
    out, d, u = [], B, 0
    while len(out) < n:
        if d.weekday() < 5:
            u += 1
            if not (feriados and u % 21 == 0):
                out.append(d)
        d += _dt.timedelta(days=1)
    return out


# ───────────────────────── #1 — teto de memória cobre o marcador novo ─────────────────────────
def achado_1():
    V5.liga()
    try:
        tempos = {}
        for rot, wire in (("antigo", "#TCF.8\n*2000000+1|\\7\n"),
                          ("novo", "#TCF.8\n*2000000~1,2|\\7\n")):
            t = time.perf_counter()
            try:
                decode(wire, max_length=10)
                tempos[rot] = None            # NAO protegeu
            except ValueError:
                tempos[rot] = time.perf_counter() - t
    finally:
        V5.desliga()
    passou = tempos["novo"] is not None and tempos["novo"] < 0.05
    _ok(1, "teto de memória cobre `*N~…|` (bomba rejeitada ANTES de materializar)", passou,
        f"antigo {tempos['antigo'] * 1e3:.2f} ms · novo {tempos['novo'] * 1e3:.2f} ms "
        f"(o passe separado do 1º protótipo levava 2473 ms)")


# ───────────────────────── #2 — detector não é O(n²) ─────────────────────────
def achado_2():
    import statistics
    tempos = {}
    for n in (600, 1200, 2400):
        vals = [str((B + _dt.timedelta(days=i)).toordinal()) for i in range(n)]
        xs_on, xs_off = [], []
        for _ in range(5):                       # rodadas INTERCALADAS, mediana
            V5.liga()
            try:
                t = time.perf_counter()
                encode(vals)
                xs_on.append(time.perf_counter() - t)
            finally:
                V5.desliga()
            t = time.perf_counter()
            encode(vals)
            xs_off.append(time.perf_counter() - t)
        tempos[n] = (statistics.median(xs_off) * 1e3, statistics.median(xs_on) * 1e3)
    cresc = tempos[2400][1] / tempos[1200][1]
    passou = cresc < 3.0 and tempos[2400][1] < 400
    _ok(2, "detector é O(n·P), não O(n²) — no dado que ele NÃO deve tocar", passou,
        "\n".join(f"n={n}: off {o:.1f} ms · v5 {v:.1f} ms ({(v / o - 1) * 100:+.0f}%)"
                  for n, (o, v) in tempos.items())
        + f"\ncrescimento 1200->2400: {cresc:.2f}x (quadrático seria ~4x; v1 fazia 13838 ms)")


# ───────────────────────── #3 — FLOOR preserva o desempate do core ─────────────────────────
def achado_3():
    casos = {
        "diario-600": [str((B + _dt.timedelta(days=i)).toordinal()) for i in range(600)],
        "texto-600": [f"cliente-{i % 37}@acme.com.br" for i in range(600)],
        "ruido-600": [str((i * 7919) % 999983) for i in range(600)],
        "ips-600": [f"10.0.{i // 256}.{i % 256}" for i in range(600)],
        "constante": ["x"] * 600,
        "unico": ["so-um"],
    }
    divergentes = []
    for rot, vals in casos.items():
        off = encode(vals)
        V5.liga()
        try:
            on = encode(vals)
        finally:
            V5.desliga()
        if off != on:
            divergentes.append(f"{rot}: {len(off.encode())} -> {len(on.encode())} B")
    _ok(3, "FLOOR não reescreve wire de dado SEM periodicidade (desempate preservado)",
        not divergentes, "\n".join(divergentes) if divergentes
        else f"{len(casos)} casos sem periodicidade: wire byte-idêntico ao de hoje")


# ───────────────────────── #4 — telemetria descreve o corpo emitido ─────────────────────────
def achado_4():
    casos = {
        "seq-uniforme": [str(1000 + i) for i in range(600)],
        "passo-7": [str(1000 + 7 * i) for i in range(600)],
        "diario-ISO": [(B + _dt.timedelta(days=i)).isoformat() for i in range(600)],
        "ips": [f"10.0.{i // 256}.{i % 256}" for i in range(600)],
        "uteis-PERIODICO": [str(d.toordinal()) for d in uteis(600)],
        "texto-sem-runs": [f"cliente-{i}@acme.com.br" for i in range(600)],
    }
    linhas, ruim = [], []
    for rot, vals in casos.items():
        so_off = SideOutputs()
        w_off = encode(vals, side_outputs=so_off)
        n_off = len(so_off.seq_rle_runs or [])
        V5.liga()
        try:
            so_on = SideOutputs()
            w_on = encode(vals, side_outputs=so_on)
        finally:
            V5.desliga()
        runs_on = so_on.seq_rle_runs or []
        n_on = len(runs_on)
        marcs = sum(1 for ln in w_on.split("\n") if ln.startswith("*"))
        # invariante: se ha marcador no corpo, a telemetria NAO pode estar vazia;
        # e se o wire e' identico ao de hoje, a telemetria tem de ser a de hoje.
        if marcs and not n_on:
            ruim.append(f"{rot}: {marcs} marcadores no wire e telemetria VAZIA")
        if w_off == w_on and n_off != n_on:
            ruim.append(f"{rot}: wire idêntico mas runs {n_off} -> {n_on}")
        # e as linhas reportadas tem de existir no corpo
        for r in runs_on:
            if not (1 <= r["start_line"] <= r["end_line"] <= len(vals) + 5):
                ruim.append(f"{rot}: run fora de faixa {r['start_line']}..{r['end_line']}")
        per = [r for r in runs_on if r.get("periodo")]
        linhas.append(f"{rot:<16} marcadores={marcs:<3} runs {n_off} -> {n_on}"
                      f"{'  (periódicos: ' + str(len(per)) + ')' if per else ''}")
    _ok(4, "telemetria `seq_rle_runs` descreve o corpo emitido (não zera calada)",
        not ruim, "\n".join(linhas) + ("\nRUIM: " + "; ".join(ruim) if ruim else ""))


# ───────────────────────── #5 — pad sem cauda morta (injetividade) ─────────────────────────
def achado_5():
    V5.liga()
    try:
        # canônico E emissível: p=2 com 2 ciclos completos (count-1 = 4 >= 2*2)
        canonico = "#TCF.8\n*5~1,4|\\120\n"
        base = decode(canonico)
        recusar = [
            # (a) NÃO-INJETIVAS: outra grafia produz o MESMO dado
            ("*5~1,4,1,4|\\120", "repetição exata do período"),
            ("*5~1,4,1|\\120", "extensão parcial ([1,4,1] gera o mesmo que [1,4])"),
            ("*5~1,4,9|\\120", "cauda morta (9 nunca é lido)"),
            ("*5~1,4,9,9,9|\\120", "cauda morta longa"),
            ("*5~1,4,-777|\\120", "cauda morta negativa"),
            ("*600~1,1|\\7", "pad uniforme = `*N+d|` disfarçado"),
            # (b) INJETIVAS mas NÃO-EMISSÍVEIS: menos de 2 ciclos completos — o guard
            #     de re-emissão (mesma classe do `d.isoformat() != v` do spec de data)
            ("*3~1,4|\\120", "1,5 ciclos — o detector emitiria `*5~1,4|`"),
            ("*4~1,3|\\120", "1,5 ciclos"),
            ("*7~1,3,1,3,1|\\120", "1,2 ciclos (period. mínimo 5, mas L=6 < 10)"),
        ]
        aceitas = []
        for wire, porque in recusar:
            try:
                decode(f"#TCF.8\n{wire}\n")
                aceitas.append(f"{wire}  ({porque})")
            except ValueError:
                pass
        vivo = base == ["120", "121", "125", "126", "130"]
    finally:
        V5.desliga()
    _ok(5, "só a grafia canônica E emissível decodifica (injetividade + re-emissão)",
        not aceitas and vivo,
        f"canônico `*5~1,4|` -> {base} (ok={vivo})\n"
        + (("AINDA ACEITAS:\n  " + "\n  ".join(aceitas)) if aceitas
           else f"{len(recusar)} grafias recusadas: 6 não-injetivas + 3 não-emissíveis"))


# ───────────────────────── invariantes que não podem quebrar ─────────────────────────
def invariantes():
    print("\n--- invariantes (o que já estava provado e não pode regredir)")
    v, ciclo, ids = 700000, [10, 10, 10, 50], []
    for i in range(600):
        ids.append(str(v))
        v += ciclo[i % 4]
    from tcf.natures import SPEC_DATA_ISO
    # data ENTRA como grafia ISO e é comparada como o encoder REAL a trataria: com o
    # spec soldado (senão o número mede o baseline sem spec e o ganho some — foi o que
    # aconteceu na 1ª passada deste script).
    casos = {
        "uteis-600": ([d.isoformat() for d in uteis(600)], {"nature": SPEC_DATA_ISO}),
        "uteis-6000": ([d.isoformat() for d in uteis(6000)], {"nature": SPEC_DATA_ISO}),
        "uteis-feriado": ([d.isoformat() for d in uteis(600, feriados=1)], {"nature": SPEC_DATA_ISO}),
        "ids-turno": (ids, {}),
        "diario-600": ([(B + _dt.timedelta(days=i)).isoformat() for i in range(600)],
                       {"nature": SPEC_DATA_ISO}),
    }
    linhas, ruim = [], []
    for rot, (vals, kw) in casos.items():
        off = len(encode(vals, **kw).encode())
        V5.liga()
        try:
            w = encode(vals, **kw)
            rt = decode(w) == vals
        finally:
            V5.desliga()
        on = len(w.encode())
        if not rt:
            ruim.append(f"{rot}: RT QUEBROU")
        if on > off:
            ruim.append(f"{rot}: REGREDIU {off} -> {on}")
        linhas.append(f"{rot:<15} {off:>6} -> {on:<6} B  ({off / on:>5.1f}x)  RT={rt}")
    _ok("A", "ganho e RT preservados (nunca-pior)", not ruim, "\n".join(linhas))

    # adversariais de grafia: valores que IMITAM o marcador
    adv = [["*600~1,3,1,1,1|739617", "outro", "mais"], ["*3~1,2|z"] * 4,
           ["a|b", "*2~9,8|q", "c"], ["*5+1|abc", "x", "y"], ["*3~1,4,9|\\120", "z"]]
    V5.liga()
    try:
        falhas = [i for i, vals in enumerate(adv) if decode(encode(vals)) != vals]
    finally:
        V5.desliga()
    _ok("B", "valores que IMITAM o marcador fazem round-trip", not falhas,
        f"{len(adv)} conjuntos adversariais" if not falhas else f"falharam: {falhas}")

    # gates byte-canonical
    tot = 0
    for nome in ("D1-emails-simples", "D2-emails-quote-id", "D3-stress-substring",
                 "D4-caos-mix", "D5-padroes-multiplos", "D6-poucos-em-ruido",
                 "D7-aninhamento", "D8-cabeca-cauda", "D9-frequencia-alta"):
        with (REPO / "datasets" / "synthetic" / f"{nome}.csv").open(encoding="utf-8") as f:
            r = csv.reader(f)
            next(r)
            vals = [row[0] for row in r if row]
        V5.liga()
        try:
            tot += len(encode(vals).encode())
        finally:
            V5.desliga()
    trw = 0
    for rel in ("online-retail/description-2k.csv", "online-retail/stockcode-2k.csv",
                "tpch-sf001/lcomment-2k.csv"):
        with (REPO / "datasets" / "samples" / rel).open(encoding="utf-8", newline="") as f:
            r = csv.reader(f)
            next(r)
            vals = [row[0] for row in r]
        V5.liga()
        try:
            trw += len(encode(vals).encode())
        finally:
            V5.desliga()
    _ok("C", "gates byte-canonical intactos", tot == 1545 and trw == 89430,
        f"D1-D9 = {tot} (congelado 1545) · real-world = {trw} (congelado 89430)")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("=== os 5 achados da caçada, contra a v5 ===")
    achado_1()
    achado_2()
    achado_3()
    achado_4()
    achado_5()
    invariantes()
    (RAIZ / "outputs" / "v5-verificacao.json").write_text(
        json.dumps(RES, ensure_ascii=False, indent=1), encoding="utf-8", newline="")
    falhas = [r for r in RES if not r["passou"]]
    print(f"\n{len(RES) - len(falhas)}/{len(RES)} OK"
          + (f" — FALHAS: {[r['n'] for r in falhas]}" if falhas else " — nada pendente"))
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
