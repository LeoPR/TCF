"""Revisão dos TIPOS do ciclo — de bool a date, cada um contra o esperado. `python run.py`

Pedido do owner: *"revise os tipos que fizemos até o momento, que vai desde bool e afins
até date, mexemos bastante. talvez um pequeno lab de teste de ambos pra ver comportamento
de cada um pra ver se está tudo certo"*.

O ciclo soldou, nesta ordem: bN de domínio (ADR-0036) · denso b1/b2 (ADR-0037) · índice
interno no core bool (ADR-0038) · lazytype bool (ADR-0039) · nB tipado numérico
(T-BN-TIPADO) + canonicidade da grafia numérica · SPEC_DATA_ISO (T-DATA-LAZY-ISO) + fix
do FLOOR-vê-bN + fix do None nas 4 natures · seq-RLE periódico (ADR-0040). O periódico
mexe no CORPO que todas as rotas usam — por isso a revisão é agora.

Três perguntas por caso:
    1. a ROTA é a esperada? (header pinado por prefixo)
    2. o RT fecha? (assert, sempre)
    3. o BYTE está na faixa esperada? (teto pinado — pega regressão grossa, não micro)

E uma seção de INTERAÇÃO: o que o periódico mudou nos números de cada tipo, contra os
"antes" gravados no lab `0042` (números commitados em result.md de lá).

`src/tcf` NÃO é tocado.
"""
from __future__ import annotations

import datetime as _dt
import decimal
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
sys.path.insert(0, str(REPO / "src"))

from tcf import decode, encode  # noqa: E402
from tcf.natures import SPEC_DATA_ISO, SPEC_REGISTRY  # noqa: E402
from tcf.side_outputs import SideOutputs  # noqa: E402

for x in ("inputs", "intermediates", "outputs"):
    (RAIZ / x).mkdir(parents=True, exist_ok=True)

B = _dt.date(2026, 1, 1)


def _escreve(p, t):
    p.write_text(t, encoding="utf-8", newline="")


def uteis(n, feriados=0):
    out, d, u = [], B, 0
    while len(out) < n:
        if d.weekday() < 5:
            u += 1
            if not (feriados and u % 21 == 0):
                out.append(d)
        d += _dt.timedelta(days=1)
    return out


def mensal_dia1(n):
    out, y, m = [], 2000, 1
    for _ in range(n):
        out.append(_dt.date(y, m, 1))
        m += 1
        if m == 13:
            m, y = 1, y + 1
    return out


def ids_turno(n):
    out, v, ciclo = [], 700000, [10, 10, 10, 50]
    for i in range(n):
        out.append(str(v))
        v += ciclo[i % 4]
    return out


# ─────────────────────────── a matriz esperado × observado ───────────────────────────
# (rotulo, familia, dados, kwargs, rota_esperada_PREFIXO, teto_bytes, nota do esperado)

CASOS = [
    # ── família BOOL (ADR-0036..0039) ──
    ("bool-puro", "bool", [True, False, True, True] * 50, {},
     "#TCF.8b1", 60, "denso b1: 1 bit/valor, dominio implicito"),
    ("bool-null", "bool", [True, False, None, True] * 50, {},
     "#TCF.8b2", 90, "denso b2 TERNARIO: null=0/false=1/true=2 congelado"),
    ("bool-all-true", "bool", [True] * 200, {},
     "#TCF.8b", 20, "core-com-slots (ADR-0038): RLE de linha vence o denso"),
    ("bool-lazy-extras", "bool", [True, False, "N/A", True] * 50, {},
     "#TCF.8bB", 95, "lazytype (ADR-0039): cabeca congelada + extra str declarado"),
    ("bool-so-null", "bool", [None] * 100, {},
     "#TCF.8", 25, "null puro: core, slot 0"),
    # ── família NUMÉRICA tipada (T-BN-TIPADO) ──
    ("int-01", "num", [0, 1, 1, 0] * 50, {},
     "#TCF.8nB1", 65, "nB tipado: dominio {0,1}, 1 bit"),
    ("int-0a3", "num", [0, 1, 2, 3] * 50, {},
     "#TCF.8nB2", 105, "nB tipado: 2 bits"),
    ("float-2vals", "num", [1.5, 2.5, 1.5, 2.5] * 50, {},
     "#TCF.8nB1", 70, "float low-card via nB; grafia canonica no _cast_tipo"),
    ("int-null", "num", [1, None, 0, 1] * 50, {},
     "#TCF.8nB2", 100, "null ocupa slot; dominio {0,1}+null"),
    ("int-sequencial", "num", list(range(700000, 700200)), {},
     "#TCF.8n", 30, "rota tipada usa o CORPO do core: `*200+1|` uniforme"),
    ("int-PERIODICO", "num", [700000 + sum(([10, 10, 10, 50] * 50)[:i]) for i in range(200)], {},
     "#TCF.8n", 40, "ADR-0040 na rota TIPADA: `*200~10,10,10,50|`"),
    ("int-grafia-canonica", "num", [1, 10, 100, 1000] * 25, {},
     "#TCF.8n", 999, "grafias 01/1.50/+1/1e3 nao existem na emissao"),
    # ── STRINGS (ADR-0036 + core) ──
    ("str-low-card", "str", ["ATIVA", "BAIXADA"] * 100, {},
     "#TCF.8B1", 70, "bN de dominio: k=2, 1 bit/linha"),
    ("str-true-false", "str", ["true", "false"] * 100, {},
     "#TCF.8B1", 70, "bool-em-string fica STRING (caixa preservada) — bN resolve"),
    ("str-high-card", "str", [f"c-{i}@x.br" for i in range(200)], {},
     "#TCF.8!", 70, "alta cardinalidade: OBAT/HCC + polaridade"),
    ("str-vazia-e-espaco", "str", ["", " ", "x", ""] * 25, {},
     "#TCF.8", 999, "vazio e whitespace sobrevivem (NAO strip)"),
    # ── NATURES per-valor (ADR-0015 + fixes do ciclo) ──
    ("cpf-2-distintos", "nature", ["000.000.000-00", "111.111.111-11"] * 30,
     {"nature": SPEC_REGISTRY["cpf"]},
     "#TCF.8B1", 70, "FLOOR-ve-bN (fix 2026-08-08): bN vence a nature aqui"),
    ("cnpj", "nature", ["00.000.000/0000-00"] * 40, {"nature": SPEC_REGISTRY["cnpj"]},
     "#TCF.8", 40, "constante: RLE de linha vence; nature recusa"),
    ("ip-sequencial", "nature", [f"10.0.0.{i}" for i in range(100)],
     {"nature": SPEC_REGISTRY["ip"]},
     "#TCF.8!", 45, "multi-delta per-run (ADR-0016) come o IP; nature recusa"),
    ("cpf-com-null", "nature", ["000.000.000-00", None] * 30, {"nature": SPEC_REGISTRY["cpf"]},
     "#TCF.8", 999, "fix None nas 4 natures: nao estoura TypeError"),
    # ── DATA (SPEC_DATA_ISO + ADR-0040) ──
    ("data-diaria", "data", [(B + _dt.timedelta(days=i)).isoformat() for i in range(600)],
     {"nature": SPEC_DATA_ISO},
     "#TCF.8 :data-iso", 35, "ordinal + `*600+1|` uniforme"),
    ("data-uteis", "data", [d.isoformat() for d in uteis(600)], {"nature": SPEC_DATA_ISO},
     "#TCF.8 :data-iso", 45, "ADR-0040: `*600~1,3,1,1,1|` — era 1590 B"),
    ("data-uteis-feriado", "data", [d.isoformat() for d in uteis(600, feriados=1)],
     {"nature": SPEC_DATA_ISO},
     "#TCF.8", 999, "periodo quebrado a cada ~21: runs menores"),
    ("data-mensal", "data", [d.isoformat() for d in mensal_dia1(600)], {"nature": SPEC_DATA_ISO},
     "#TCF.8", 1100, "antes o spec RECUSAVA (1085); periodico p=12 pode inverter"),
    ("data-com-ruido", "data", None, {"nature": SPEC_DATA_ISO},
     "#TCF.8", 999, "valvula lazy: lixo vira _literal, resto comprime"),
    ("data-com-null", "data", None, {"nature": SPEC_DATA_ISO},
     "#TCF.8", 999, "None passa pelo slot 0, fora da nature"),
    ("data-grafia-suja", "data", ["2026-1-5", "2026/01/05", "20260105"] * 20,
     {"nature": SPEC_DATA_ISO},
     "#TCF.8", 999, "nenhuma parseia canonica -> spec recusa a coluna"),
    # ── IDS periódicos (a generalidade do ADR-0040, sem nature) ──
    ("ids-turno", "num-str", ids_turno(600), {},
     "#TCF.8", 40, "`*600~10,10,10,50|` no nivel do CORE — era 1959 B"),
]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    # dados que dependem de construcao
    ruido = [d.isoformat() for d in uteis(600)]
    for pos in (37, 141, 300, 468):
        ruido[pos] = "s/d"
    com_null = [d.isoformat() for d in uteis(600)]
    for pos in (10, 200, 590):
        com_null[pos] = None
    CASOS[[c[0] for c in CASOS].index("data-com-ruido")] = (
        "data-com-ruido", "data", ruido, {"nature": SPEC_DATA_ISO}, "#TCF.8", 999,
        "valvula lazy: lixo vira _literal, resto comprime")
    CASOS[[c[0] for c in CASOS].index("data-com-null")] = (
        "data-com-null", "data", com_null, {"nature": SPEC_DATA_ISO}, "#TCF.8", 999,
        "None passa pelo slot 0, fora da nature")

    R, problemas = [], []
    for rotulo, familia, vals, kw, rota_esp, teto, nota in CASOS:
        vals = json.loads(json.dumps(vals))  # higiene json-lib-like
        _escreve(RAIZ / "inputs" / f"{rotulo}--json-lib-like.json",
                 json.dumps(vals, ensure_ascii=False)[:4000])
        so = SideOutputs()
        w = encode(vals, side_outputs=so, **kw)
        rt = decode(w) == vals
        hdr = w.split("\n")[0]
        n = len(w.encode("utf-8"))
        rota_ok = hdr.startswith(rota_esp)
        teto_ok = n <= teto if teto != 999 else True
        reg = {"caso": rotulo, "familia": familia, "n": len(vals), "bytes": n,
               "rota": hdr, "rota_esperada": rota_esp, "rota_ok": rota_ok,
               "teto": teto if teto != 999 else None, "teto_ok": teto_ok,
               "rt": rt, "nota": nota,
               "seq_runs": len(so.seq_rle_runs or []),
               "periodicos": sum(1 for r in (so.seq_rle_runs or []) if r.get("periodo"))}
        R.append(reg)
        if not rt:
            problemas.append(f"{rotulo}: RT QUEBROU")
        if not rota_ok:
            problemas.append(f"{rotulo}: rota {hdr!r} != esperada {rota_esp!r}")
        if not teto_ok:
            problemas.append(f"{rotulo}: {n} B estourou o teto {teto}")
        if familia in ("bool", "num", "data") or rotulo in ("ids-turno", "str-low-card"):
            _escreve(RAIZ / "outputs" / f"{rotulo}.tcf", w)
        _escreve(RAIZ / "intermediates" / f"{rotulo}--trilha.json", json.dumps(
            {"rota": hdr, "seq_rle_runs": so.seq_rle_runs}, ensure_ascii=False, indent=1))

    # ── fail-louds ESPERADOS (comportamento registrado, nao bug) ──
    FAIL = [("date-nativo", [_dt.date(2026, 1, 5)], "date"),
            ("decimal", [decimal.Decimal("1.50")], "Decimal"),
            ("datetime", [_dt.datetime(2026, 1, 5, 12, 0)], "datetime"),
            ("int-e-str-misto", [1, "x", 2], "MISTOS")]
    for rotulo, vals, frag in FAIL:
        try:
            encode(vals)
            R.append({"caso": rotulo, "familia": "fail-loud", "rt": None,
                      "rota": "ACEITOU (inesperado)", "rota_ok": False})
            problemas.append(f"{rotulo}: deveria falhar alto e ACEITOU")
        except Exception as e:
            ok = frag in str(e) or frag in type(e).__name__
            R.append({"caso": rotulo, "familia": "fail-loud", "rt": None,
                      "rota": f"{type(e).__name__}: {str(e)[:58]}", "rota_ok": ok})
            if not ok:
                problemas.append(f"{rotulo}: erro nao menciona {frag!r}")

    # ── interação: o que o periódico mudou (antes = lab 0042, commitado) ──
    ANTES = {"data-uteis": 1590, "data-mensal": 1085, "ids-turno": 1959,
             "data-diaria": 32, "data-uteis-feriado": 1889}
    inter = []
    for r in R:
        if r["caso"] in ANTES:
            a, d = ANTES[r["caso"]], r["bytes"]
            inter.append({"caso": r["caso"], "antes_lab0042": a, "agora": d,
                          "fator": round(a / d, 1)})

    _escreve(RAIZ / "outputs" / "medicoes.json",
             json.dumps({"matriz": R, "interacao_periodico": inter},
                        ensure_ascii=False, indent=1))

    linhas = ["| caso | família | rota | B | RT | rota ok | nota |",
              "|---|---|---|---:|---|---|---|"]
    for r in R:
        linhas.append(f"| {r['caso']} | {r['familia']} | `{r['rota'][:24]}` "
                      f"| {r.get('bytes', '—')} | {'✓' if r['rt'] else ('—' if r['rt'] is None else 'X')} "
                      f"| {'✓' if r['rota_ok'] else 'X'} | {r.get('nota', '')[:58]} |")
    tabela = "\n".join(linhas)
    inter_md = "\n".join(f"- `{i['caso']}`: {i['antes_lab0042']} → **{i['agora']} B** ({i['fator']}×)"
                         for i in inter)
    _escreve(RAIZ / "outputs" / "matriz.md",
             "# Matriz de conformidade — tipos do ciclo (bool → date)\n\n" + tabela
             + "\n\n## Interação do periódico (antes = lab 0042)\n\n" + inter_md + "\n")
    print(tabela)
    print("\nInteração do periódico:\n" + inter_md)
    if problemas:
        print("\nPROBLEMAS:")
        for p in problemas:
            print("  -", p)
    else:
        print(f"\n{len(R)} casos: rotas esperadas, RT verde, tetos ok — NADA fora do lugar.")
    return 1 if problemas else 0


if __name__ == "__main__":
    raise SystemExit(main())
