"""Data — as hipóteses que a rodada anterior NÃO cobriu. Esboço. `python run.py`

Reavaliação de 2026-08-09: cinco labs fecharam grafia, alvos, declaração, ambiguidade e o
spec lazy. Sondando o que sobrou, **sete hipóteses** apareceram — este lab é a triagem
sintética de controle delas. As que sobreviverem vão para labs próprios e depois pro clean.

## As hipóteses

    H1  spec→bN         o candidato da nature NÃO consulta o bN sobre a coluna
                        transformada (sondado: 529 vs 449 B em k12 — mesma classe da
                        lacuna que consertamos no BASELINE, agora no lado do candidato)
    H2  dias-úteis      delta periódico [1,1,1,1,3]: o seq-RLE só come delta UNIFORME
                        (sondado: 1590 B onde o diário faz 32 — 50×). Um alvo DELTA
                        transformaria o período em texto repetitivo, que o core come
    H3  sentinelas      9999-12-31 / 1900-01-01 / 0000-00-00 no meio de coluna regular
                        (sondado: 1 sentinela = +24 B; e quantas até matar o ganho?)
    H4  quase-null      cancelled_at: 95% null (sondado: spec ainda ganha — confirmar
                        nos extremos 99% e 100%-menos-um)
    H5  resolução mista `2026-01` e `2026-01-15` na MESMA coluna (dado real faz isso)
    H6  delta-coluna    espalhado-ORDENADO: o alvo delta-dias faz 643 B onde o spec
                        soldado faz 3828 (lab 0235). O protocolo per-valor não expressa
                        delta — medir o teto pra decidir se um transform de COLUNA
                        merece design
    H7  colunas irmãs   created_at / updated_at / shipped_at correlacionadas: o delta
                        ENTRE colunas é pequeno mesmo quando a coluna é espalhada.
                        Multi-col trata colunas independentes — medir a oportunidade

H6 e H7 são medidas como H-naive (cálculo sobre os mesmos dados, não wire novo) — o piso
que um mecanismo teria de bater. H1-H5 são wire de verdade, RT conferido.

`src/tcf` NÃO é tocado.
"""
from __future__ import annotations

import datetime as _dt
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[4]
sys.path.insert(0, str(REPO / "src"))

from tcf import decode, encode  # noqa: E402
from tcf.natures import SPEC_DATA_ISO, encode_value  # noqa: E402

for x in ("inputs", "intermediates", "outputs"):
    (RAIZ / x).mkdir(exist_ok=True)

B = _dt.date(2026, 1, 1)
N = 600


def _escreve(p, t):
    p.write_text(t, encoding="utf-8", newline="")


def _lcg(n, mod, s=77):
    x, o = s, []
    for _ in range(n):
        x = (1103515245 * x + 12345) % (1 << 31)
        o.append(x % mod)
    return o


def dias_uteis(n, feriados=0):
    """Seg-sex; `feriados` pula 1 dia útil a cada 21 (≈ feriado mensal)."""
    out, d, uteis = [], B, 0
    while len(out) < n:
        if d.weekday() < 5:
            uteis += 1
            if not (feriados and uteis % 21 == 0):
                out.append(d)
        d += _dt.timedelta(days=1)
    return out


def medida(vals, rotulo):
    """Encoda sem e com spec, confere RT dos dois, devolve o registro."""
    a = encode(vals)
    b = encode(vals, nature=SPEC_DATA_ISO)
    assert decode(a) == vals, f"{rotulo}: RT sem spec quebrou"
    assert decode(b) == vals, f"{rotulo}: RT com spec quebrou"
    return {"sem_spec": len(a.encode()), "com_spec": len(b.encode()),
            "spec_usou": b.startswith("#TCF.8 :"), "wire": b}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    R = {}

    # ── H1: spec→bN — o candidato da nature contra o encode() completo do ordinal ──
    h1 = []
    for rot, ds in [("k5", [B + _dt.timedelta(days=90 * (i % 5)) for i in range(N)]),
                    ("k12", [B + _dt.timedelta(days=30 * (i % 12)) for i in range(N)]),
                    ("k60", [B + _dt.timedelta(days=7 * (i % 60)) for i in range(N)])]:
        iso = [d.isoformat() for d in ds]
        m = medida(iso, f"H1/{rot}")
        ordinais = [encode_value(SPEC_DATA_ISO, v)[0] for v in iso]
        w_full = encode(ordinais)                  # o encode COMPLETO consulta o bN
        assert decode(w_full) == ordinais
        # +1 linha de header de nature que o caminho real pagaria
        estimado = len(w_full.encode()) + len("#TCF.8 :data-iso\n") - len("#TCF.8\n")
        h1.append({"caso": rot, **{k: v for k, v in m.items() if k != "wire"},
                   "ordinal_com_bn_estimado": estimado,
                   "lacuna_B": min(m["sem_spec"], m["com_spec"]) - estimado,
                   "rota_do_ordinal": w_full.split("\n")[0]})
    R["H1-spec-bn"] = h1

    # ── H2: dias úteis — e o alvo DELTA como hipótese naive por cima ─────────
    h2 = []
    for rot, ds in [("diario-controle", [B + _dt.timedelta(days=i) for i in range(N)]),
                    ("uteis", dias_uteis(N)),
                    ("uteis-feriados", dias_uteis(N, feriados=1))]:
        iso = [d.isoformat() for d in ds]
        m = medida(iso, f"H2/{rot}")
        # H-naive DELTA: 1ª data + diferenças como coluna (o mesmo cálculo do lab 2311)
        delta = [iso[0]] + [str((ds[i] - ds[i - 1]).days) for i in range(1, len(ds))]
        w_delta = encode(delta)
        assert decode(w_delta) == delta
        h2.append({"caso": rot, **{k: v for k, v in m.items() if k != "wire"},
                   "h_delta_naive": len(w_delta.encode())})
        if rot == "uteis":
            _escreve(RAIZ / "outputs" / "h2-uteis--com-spec.tcf", m["wire"])
            _escreve(RAIZ / "outputs" / "h2-uteis--h-delta.tcf", w_delta)
    R["H2-dias-uteis"] = h2

    # ── H3: sentinelas — quantas até matar o ganho ───────────────────────────
    h3 = []
    base = [(B + _dt.timedelta(days=i)).isoformat() for i in range(N)]
    for rot, muta in [("limpa", []),
                      ("1-sentinela", [(300, "9999-12-31")]),
                      ("3-sentinelas", [(150, "9999-12-31"), (300, "1900-01-01"),
                                        (450, "9999-12-31")]),
                      ("zero-date-mysql", [(300, "0000-00-00")]),
                      ("5pct-sentinela", [((i * 97) % N, "9999-12-31") for i in range(N // 20)])]:
        vals = base[:]
        for i, v in muta:
            vals[i] = v
        m = medida(vals, f"H3/{rot}")
        h3.append({"caso": rot, "n_sentinelas": len(muta),
                   **{k: v for k, v in m.items() if k != "wire"}})
    R["H3-sentinelas"] = h3

    # ── H4: quase-null nos extremos ──────────────────────────────────────────
    h4 = []
    for rot, pct in [("95pct-null", 95), ("99pct-null", 99)]:
        vals = [None] * N
        passo = 100 // (100 - pct)
        for i in range(0, N, passo):
            vals[i] = (B + _dt.timedelta(days=i)).isoformat()
        m = medida(vals, f"H4/{rot}")
        h4.append({"caso": rot, **{k: v for k, v in m.items() if k != "wire"}})
    vals = [None] * N
    vals[0] = "2026-01-01"
    m = medida(vals, "H4/um-so")
    h4.append({"caso": "um-so-valor", **{k: v for k, v in m.items() if k != "wire"}})
    R["H4-quase-null"] = h4

    # ── H5: resolução mista na mesma coluna ──────────────────────────────────
    h5 = []
    for rot, gera in [
        ("mes-e-dia", lambda i: (B + _dt.timedelta(days=i)).isoformat()
                      if i % 3 else (B + _dt.timedelta(days=i)).strftime("%Y-%m")),
        ("so-ano-mes", lambda i: (B + _dt.timedelta(days=30 * i)).strftime("%Y-%m")),
    ]:
        vals = [gera(i) for i in range(N)]
        m = medida(vals, f"H5/{rot}")
        h5.append({"caso": rot, **{k: v for k, v in m.items() if k != "wire"}})
    R["H5-resolucao-mista"] = h5

    # ── H6: delta-coluna no espalhado-ordenado (o teto, naive) ───────────────
    esp = sorted(B + _dt.timedelta(days=x) for x in _lcg(N, 3650))
    iso = [d.isoformat() for d in esp]
    m = medida(iso, "H6")
    delta = [iso[0]] + [str((esp[i] - esp[i - 1]).days) for i in range(1, len(esp))]
    w_delta = encode(delta)
    assert decode(w_delta) == delta
    R["H6-delta-coluna"] = [{"caso": "espalhado-ordenado",
                             **{k: v for k, v in m.items() if k != "wire"},
                             "h_delta_naive": len(w_delta.encode()),
                             "teto_da_lacuna_B": min(m["sem_spec"], m["com_spec"])
                             - len(w_delta.encode())}]
    _escreve(RAIZ / "outputs" / "h6-espalhado-ord--h-delta.tcf", w_delta)

    # ── H7: colunas irmãs correlacionadas (multi-col, naive) ─────────────────
    created = sorted(B + _dt.timedelta(days=x) for x in _lcg(N, 365))
    updated = [c + _dt.timedelta(days=_lcg(1, 7, s=i)[0]) for i, c in enumerate(created)]
    shipped = [u + _dt.timedelta(days=1 + _lcg(1, 3, s=i * 3)[0]) for u, i in
               zip(updated, range(N))]
    tab = {"created": [d.isoformat() for d in created],
           "updated": [d.isoformat() for d in updated],
           "shipped": [d.isoformat() for d in shipped]}
    w_indep = encode(tab)
    assert decode(w_indep) == tab
    # H-naive: created como coluna + irmãs como DELTA-ENTRE-COLUNAS (dias, pequenos)
    d_upd = [str((u - c).days) for c, u in zip(created, updated)]
    d_shp = [str((s - u).days) for u, s in zip(updated, shipped)]
    naive = (len(encode(tab["created"], nature=SPEC_DATA_ISO).encode())
             + len(encode(d_upd).encode()) + len(encode(d_shp).encode()))
    R["H7-colunas-irmas"] = [{
        "caso": "created-updated-shipped",
        "multi_col_independente": len(w_indep.encode()),
        "h_delta_entre_colunas_naive": naive,
        "lacuna_B": len(w_indep.encode()) - naive,
        "nota": "naive soma 3 wires separados; o real pagaria o envelope multi-col",
    }]

    # ── inputs (com higiene) + medições + relatório ──────────────────────────
    for h, regs in R.items():
        for r in regs:
            r.pop("wire", None)
    _escreve(RAIZ / "intermediates" / "medicoes.json",
             json.dumps(R, ensure_ascii=False, indent=2) + "\n")
    _escreve(RAIZ / "inputs" / "geradores--json-lib-like.input.json", json.dumps({
        "_o_que_e": "as colunas são geradas em run.py (determinístico, LCG semente fixa); "
                    "este arquivo registra a higiene e uma amostra de cada família",
        "_higiene": {"sobrevive_json": True,
                     "como": "todas as colunas são list[str|None]; conferido por construção"},
        "amostras": {"uteis": [d.isoformat() for d in dias_uteis(8)],
                     "sentinela": ["2026-10-27", "9999-12-31", "2026-10-29"],
                     "resolucao-mista": ["2026-01", "2026-01-02", "2026-01-03"]},
    }, ensure_ascii=False, indent=1) + "\n")

    L = ["# Data — hipóteses restantes (esboço de triagem)", "",
         f"`n={N}`. `sem_spec`/`com_spec` são wire real com RT conferido; `h_*_naive` é "
         "cálculo sobre os mesmos dados (o piso a bater), não wire.", ""]
    for h, regs in R.items():
        L += [f"## {h}", ""]
        cols = [k for k in regs[0] if k != "caso"]
        L += ["| caso | " + " | ".join(cols) + " |",
              "|---|" + "---|" * len(cols)]
        for r in regs:
            L.append("| `" + str(r["caso"]) + "` | "
                     + " | ".join(str(r.get(c, "—")) for c in cols) + " |")
        L.append("")
    _escreve(RAIZ / "outputs" / "medicoes.md", "\n".join(L) + "\n")
    print("ok — medicoes em outputs/medicoes.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
