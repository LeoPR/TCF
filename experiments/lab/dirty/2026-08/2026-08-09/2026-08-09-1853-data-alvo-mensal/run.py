"""Data — olhar pelo MÊS, não pelo dia. `python run.py`

Direção do owner (2026-08-09, sobre o `data-mensal` da revisão de tipos): *"olhar do
ponto de vista do dia não é errado, mas temos que ver se é possível olhar pelo mês,
assim o incremento fica melhor. vamos refazer um estudo nesse sentido e avaliar com o
que já temos."*

O diagnóstico: o spec ordinal conta DIAS, então uma coluna mensal paga a contabilidade
do calendário — deltas 28/29/30/31, quebra bissexta, runs picotados (679 B hoje, e só
porque o ADR-0040 salvou o que dava). No eixo do MÊS o incremento é +1 uniforme e a
coluna colapsa como o diário colapsa no eixo do dia.

## Os alvos candidatos (todos per-valor, com válvula — o protocolo que já temos)

    A1  ordinal-dia      o soldado hoje (baseline da comparação)
    A2  mês-época        ano*12+(mês-1); CONVENÇÃO dia==01 (senão _literal).
                         Mensal → +1 uniforme. Payload ~5 dígitos, opaco.
    A2f mês-época-FIM    idem com convenção dia==último-do-mês (fecho contábil).
    A3  YYYYMM           ano*100+mês; convenção dia==01. Legível; delta cicla
                         [1×11, 89] — o ADR-0040 come com UM marcador, SEM bissexto
                         (o eixo mês não vê dias).
    A4  mês×31+dia       (ano*12+mês-1)*31+(dia-1). SEM convenção: injetivo pra TODA
                         data. QUALQUER dia constante (01, 15, 28...) → +31 uniforme.
                         Diário → deltas [1...,k] com bissexto (pior que ordinal).

## O que se decide com isso

- A2/A3 = convenções nomeadas (uma tag por convenção); A4 = um alvo geral sem convenção.
- Grafia `YYYY-MM` pura (H5 da triagem): parseia direto nos alvos mensais — o spec irmão
  `SPEC_DATA_ANO_MES` que estava na fila do `T-SPEC-PARSE-X-ALVO`. Aqui: mesma conta,
  grafia de re-emissão própria (per-valor exige 1 grafia por tag, senão o RT quebra).
- Já temos DUAS grafias e >=2 alvos medidos: o critério do `T-SPEC-PARSE-X-ALVO`
  ("separar quando a segunda grafia aparecer") está batendo na porta. O result fecha isso.

Wires das colunas transformadas são `encode()` REAL (o core pós-ADR-0040 come as
colunas de inteiros sozinho); o transform e o un-transform são espelhos naive daqui,
com RT contra o input em TODOS os casos. Ajuste de header: +11 B (tag hipotética
`:data-mes`-like), o mesmo critério dos labs 0042/0024.

`src/tcf` NÃO é tocado.
"""
from __future__ import annotations

import calendar
import datetime as _dt
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
sys.path.insert(0, str(REPO / "src"))

from tcf import decode, encode  # noqa: E402
from tcf.natures import SPEC_DATA_ISO  # noqa: E402

for x in ("inputs", "intermediates", "outputs"):
    (RAIZ / x).mkdir(parents=True, exist_ok=True)

AJUSTE = len(" :data-mes")   # header hipotético da tag mensal


def _escreve(p, t):
    p.write_text(t, encoding="utf-8", newline="")


# ───────────────────────────── geradores de regime ─────────────────────────────

def mensal(n, dia=1, inicio=(2000, 1)):
    out, (y, m) = [], inicio
    for _ in range(n):
        d = calendar.monthrange(y, m)[1] if dia == "fim" else dia
        out.append(_dt.date(y, m, min(d, calendar.monthrange(y, m)[1])))
        m += 1
        if m == 13:
            m, y = 1, y + 1
    return out


def mensal_com_faltas(n):
    """Pula ~1 mês a cada 7 (contrato suspenso, competência sem fato)."""
    out, y, m, k = [], 2000, 1, 0
    while len(out) < n:
        k += 1
        if k % 7 != 0:
            out.append(_dt.date(y, m, 1))
        m += 1
        if m == 13:
            m, y = 1, y + 1
    return out


def yyyy_mm(n):
    out, y, m = [], 2000, 1
    for _ in range(n):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m == 13:
            m, y = 1, y + 1
    return out


# ─────────────────────────── os alvos (espelhos naive) ───────────────────────────

def _parse(v):
    try:
        d = _dt.date.fromisoformat(v)
        return d if d.isoformat() == v else None
    except (ValueError, TypeError):
        return None


def a2_enc(v):
    d = _parse(v)
    if d is None or d.day != 1:
        return "_" + v
    return str(d.year * 12 + d.month - 1)


def a2_dec(p):
    if p.startswith("_"):
        return p[1:]
    m = int(p)
    return _dt.date(m // 12, m % 12 + 1, 1).isoformat()


def a2f_enc(v):
    d = _parse(v)
    if d is None or d.day != calendar.monthrange(d.year, d.month)[1]:
        return "_" + v
    return str(d.year * 12 + d.month - 1)


def a2f_dec(p):
    if p.startswith("_"):
        return p[1:]
    m = int(p)
    y, mo = m // 12, m % 12 + 1
    return _dt.date(y, mo, calendar.monthrange(y, mo)[1]).isoformat()


def a3_enc(v):
    d = _parse(v)
    if d is None or d.day != 1:
        return "_" + v
    return str(d.year * 100 + d.month)


def a3_dec(p):
    if p.startswith("_"):
        return p[1:]
    m = int(p)
    return _dt.date(m // 100, m % 100, 1).isoformat()


def a4_enc(v):
    d = _parse(v)
    if d is None:
        return "_" + v
    return str((d.year * 12 + d.month - 1) * 31 + d.day - 1)


def a4_dec(p):
    if p.startswith("_"):
        return p[1:]
    q, r = divmod(int(p), 31)
    return _dt.date(q // 12, q % 12 + 1, r + 1).isoformat()


def ym_enc(v):
    """Grafia YYYY-MM pura (spec irmão): parser próprio, re-emite YYYY-MM."""
    if len(v) == 7 and v[4] == "-" and v[:4].isdigit() and v[5:].isdigit():
        m = int(v[5:])
        if 1 <= m <= 12:
            return str(int(v[:4]) * 12 + m - 1)
    return "_" + v


def ym_dec(p):
    if p.startswith("_"):
        return p[1:]
    m = int(p)
    return f"{m // 12:04d}-{m % 12 + 1:02d}"


ALVOS = {"A2-mes-epoca-d01": (a2_enc, a2_dec),
         "A2f-mes-epoca-FIM": (a2f_enc, a2f_dec),
         "A3-YYYYMM-d01": (a3_enc, a3_dec),
         "A4-mes31-dia": (a4_enc, a4_dec)}


def mede_alvo(nome, vals, rotulo):
    enc, dec = ALVOS.get(nome, (ym_enc, ym_dec))
    col = [enc(v) for v in vals]
    w = encode(col)
    assert decode(w) == col, f"{rotulo}/{nome}: RT do wire quebrou"
    assert [dec(c) for c in col] == vals, f"{rotulo}/{nome}: espelho nao devolveu o input"
    return {"bytes": len(w.encode("utf-8")) + AJUSTE, "rota": w.split("\n")[0],
            "wire": w, "validos": sum(1 for c in col if not c.startswith("_"))}


# ───────────────────────────────── harness ─────────────────────────────────

def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    N = 600
    REGIMES = [
        ("mensal-dia1", [d.isoformat() for d in mensal(N, dia=1)]),
        ("mensal-dia15", [d.isoformat() for d in mensal(N, dia=15)]),
        ("mensal-fim-do-mes", [d.isoformat() for d in mensal(N, dia="fim")]),
        ("trimestral-dia1", [d.isoformat() for d in mensal(N * 3, dia=1)][::3]),
        ("mensal-com-faltas", [d.isoformat() for d in mensal_com_faltas(N)]),
        ("yyyy-mm-puro", yyyy_mm(N)),
        ("diario-CONTROLE", [(_dt.date(2026, 1, 1) + _dt.timedelta(days=i)).isoformat()
                             for i in range(N)]),
        ("misto-d01-d15", [d.isoformat() for pares in zip(mensal(N // 2, 1), mensal(N // 2, 15))
                           for d in pares]),
    ]

    R = []
    for rotulo, vals in REGIMES:
        vals = json.loads(json.dumps(vals))
        _escreve(RAIZ / "inputs" / f"{rotulo}--json-lib-like.json",
                 json.dumps(vals, ensure_ascii=False, indent=0))
        c0 = encode(vals)
        assert decode(c0) == vals, f"{rotulo}: RT sem spec quebrou"
        reg = {"caso": rotulo, "n": len(vals), "C0_sem_spec": len(c0.encode("utf-8"))}
        eh_ym = rotulo == "yyyy-mm-puro"
        if not eh_ym:
            c1 = encode(vals, nature=SPEC_DATA_ISO)
            assert decode(c1) == vals, f"{rotulo}: RT com spec quebrou"
            reg["A1_ordinal_dia"] = len(c1.encode("utf-8"))
        else:
            c1 = encode(vals, nature=SPEC_DATA_ISO)   # spec atual diante de YYYY-MM
            assert decode(c1) == vals
            reg["A1_ordinal_dia"] = len(c1.encode("utf-8"))
        detalhe = {}
        alvos_do_caso = (["YM-grafia-propria"] if eh_ym
                         else list(ALVOS.keys()))
        for nome in alvos_do_caso:
            m = mede_alvo(nome, vals, rotulo)
            reg[nome] = m["bytes"]
            detalhe[nome] = {"rota": m["rota"], "validos": m["validos"]}
            if rotulo in ("mensal-dia1", "mensal-dia15", "yyyy-mm-puro") and \
                    nome in ("A2-mes-epoca-d01", "A4-mes31-dia", "YM-grafia-propria"):
                _escreve(RAIZ / "outputs" / f"{rotulo}--{nome}.wire.txt", m["wire"])
        candidatos = {k: v for k, v in reg.items()
                      if k not in ("caso", "n") and isinstance(v, int)}
        reg["floor"] = min(candidatos.values())
        reg["vencedor"] = min(candidatos, key=candidatos.get)
        reg["detalhe"] = detalhe
        R.append(reg)
        _escreve(RAIZ / "intermediates" / f"{rotulo}--trilha.json",
                 json.dumps(reg, ensure_ascii=False, indent=1))
        if rotulo == "mensal-dia1":
            _escreve(RAIZ / "outputs" / f"{rotulo}--A1-ordinal-atual.tcf", c1)
            rt = {"input_n": len(vals),
                  "rt_todos_alvos_2_niveis": True,   # asserts acima garantem
                  "primeiros_3": vals[:3], "ultimos_2": vals[-2:]}
            _escreve(RAIZ / "outputs" / f"{rotulo}.roundtrip.json",
                     json.dumps(rt, ensure_ascii=False, indent=1))

    _escreve(RAIZ / "outputs" / "medicoes.json", json.dumps(R, ensure_ascii=False, indent=1))

    cols = ["C0_sem_spec", "A1_ordinal_dia", "A2-mes-epoca-d01", "A2f-mes-epoca-FIM",
            "A3-YYYYMM-d01", "A4-mes31-dia", "YM-grafia-propria"]
    linhas = ["| caso | n | " + " | ".join(c.replace("_", " ") for c in cols)
              + " | vence |",
              "|---|---:|" + "---:|" * len(cols) + "---|"]
    for r in R:
        linhas.append(f"| {r['caso']} | {r['n']} | "
                      + " | ".join(str(r.get(c, "—")) for c in cols)
                      + f" | **{r['vencedor']}** |")
    tabela = "\n".join(linhas)
    _escreve(RAIZ / "outputs" / "medicoes.md",
             "# Medições — alvos mensais (bytes; alvos novos pagam +11 B de header)\n\n"
             + tabela + "\n\nRotas dos alvos por caso:\n\n"
             + "\n".join(f"- `{r['caso']}`: " + json.dumps(r["detalhe"], ensure_ascii=False)
                         for r in R) + "\n")
    print(tabela)
    print("\nOK — RT conferido em todos os alvos de todos os casos (2 níveis).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
