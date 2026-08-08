"""Quanto custa a AMBIGUIDADE de data — em bytes, e só em bytes. `python run.py`

## A tese do owner, testada

> *"a ambiguidade não é uma ambiguidade em si nas datas. Mesmo que o algoritmo ache um ou
> outro, se ele reconstruir igual, está ok. Não vai estar no máximo como em sequência, mas é
> aceitável já que mantém a integridade. A ambiguidade só gera problema de COMPRESSÃO, não
> de encode/decode."*

O lab constrói colunas **genuinamente ambíguas** — todas as datas com dia ≤ 12, onde
`DD/MM` e `MM/DD` são leituras igualmente válidas — e encoda cada uma com o spec **certo** e
com o spec **errado**.

    integridade   os dois têm de fazer round-trip byte-exato. Se algum falhar, a tese cai.
    compressão    a diferença de bytes entre o certo e o errado É o custo da ambiguidade.

## Por que o custo aparece

Uma coluna BR de dias consecutivos (`01/03`, `02/03`, `03/03`…) lida como US vira
`3 de janeiro`, `3 de fevereiro`, `3 de março` — os ordinais saltam ~30 em vez de +1. O dado
é o mesmo, a leitura é reversível, mas **a regularidade some** — e é a regularidade que o
`*N+M|` do seq-RLE come.

## A terceira opção: ignorar

Cada caso também é medido **sem spec nenhum** (a coluna como string pura, que é o que o TCF
faz hoje). É o piso de comparação: quanto se perde por simplesmente não tentar.

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
sys.path.insert(0, str(RAIZ))

from tcf import decode, encode  # noqa: E402
from tcf.side_outputs import SideOutputs  # noqa: E402

for x in ("inputs", "intermediates", "outputs"):
    (RAIZ / x).mkdir(exist_ok=True)

N = 480
MARCA = "_"                      # o marcador literal, igual ao da nature do CPF


def _escreve(p, t):
    p.write_text(t, encoding="utf-8", newline="")


# ── o spec mínimo: parseia numa grafia, transforma em ordinal, ou deixa literal ──
class Spec:
    def __init__(self, nome, fmt):
        self.nome, self.fmt = nome, fmt

    def para(self, vals):
        out, n_ok = [], 0
        for v in vals:
            try:
                d = _dt.datetime.strptime(v, self.fmt).date()
            except ValueError:
                out.append(MARCA + v)
                continue
            if d.strftime(self.fmt) != v:            # canonicidade por re-emissão
                out.append(MARCA + v)
                continue
            out.append(str(d.toordinal()))
            n_ok += 1
        return out, n_ok

    def de(self, vals):
        return [v[1:] if v.startswith(MARCA)
                else _dt.date.fromordinal(int(v)).strftime(self.fmt) for v in vals]


BR = Spec("br", "%d/%m/%Y")
US = Spec("us", "%m/%d/%Y")


def _lcg(n, mod, semente=31337):
    x, out = semente, []
    for _ in range(n):
        x = (1103515245 * x + 12345) % (1 << 31)
        out.append(x % mod)
    return out


def _amb(d: _dt.date) -> bool:
    """A data é ambígua? Só quando dia E mês são ≤ 12 — aí DD/MM e MM/DD ambos valem."""
    return d.day <= 12 and d.month <= 12


# ── os casos: colunas 100% AMBÍGUAS, em regimes diferentes ───────────────────
def casos():
    c = []
    # dias consecutivos dentro de um mês (dia 1..12) — regular em BR, espalhado em US
    seq = []
    m, y = 1, 2026
    while len(seq) < N:
        for dia in range(1, 13):
            seq.append(_dt.date(y, m, dia))
            if len(seq) >= N:
                break
        m += 1
        if m > 12:
            m, y = 1, y + 1
    c.append(("consecutivo-no-mes",
              "dias 1..12 correndo — REGULAR lido como BR, espalhado lido como US", seq))

    # o espelho: meses correndo com o dia fixo — regular em US, espalhado em BR
    esp = []
    dia, y = 1, 2026
    while len(esp) < N:
        for mes in range(1, 13):
            esp.append(_dt.date(y, mes, dia))
            if len(esp) >= N:
                break
        dia += 1
        if dia > 12:
            dia, y = 1, y + 1
    c.append(("consecutivo-no-mes-espelhado",
              "o espelho: REGULAR lido como US, espalhado lido como BR", esp))

    # ambíguo e sem ordem nenhuma — nenhuma leitura tem regularidade
    aleat = []
    for x in _lcg(N * 3, 144):
        d = _dt.date(2026, (x % 12) + 1, (x // 12) + 1)
        if _amb(d):
            aleat.append(d)
        if len(aleat) >= N:
            break
    c.append(("ambiguo-sem-ordem",
              "dia e mês ≤ 12 sem ordem — nenhuma leitura ganha regularidade", aleat))

    # baixa cardinalidade ambígua
    doze = [_dt.date(2026, (i % 12) + 1, (i % 12) + 1) for i in range(N)]
    c.append(("ambiguo-k12", "12 datas cicladas, todas ambíguas", doze))
    return c


def trilha(vals):
    so = SideOutputs()
    w = encode(vals, side_outputs=so)
    runs = so.seq_rle_runs or []
    cf = so.column_features
    return {
        "wire_bytes": len(w.encode()),
        "1_entrada": {"n_linhas": getattr(cf, "n_rows", None),
                      "n_unicas": getattr(cf, "n_unicas", None),
                      "cardinalidade": getattr(cf, "cardinality", None)},
        "2_pre_passe": {"cadencia_detectada": so.cadence_detected,
                        "min_len_escolhido": so.min_len},
        "4_hcc_composicional": {
            "seq_rle_disparou": bool(runs), "n_corridas": len(runs),
            "deltas_uniformes": sorted({r.get("uniform_delta") for r in runs
                                        if r.get("uniform_delta") is not None}),
            "corridas": [{"linhas": f"{r.get('start_line')}..{r.get('end_line')}",
                          "count": r.get("count"),
                          "delta_uniforme": r.get("uniform_delta")} for r in runs[:5]],
        },
        "5_saida": {"body_bytes": so.body_bytes, "primeira_linha": w.split("\n")[0]},
    }


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    linhas, falhas = [], []

    for nome, porque, datas in casos():
        assert all(_amb(d) for d in datas), f"{nome}: nem todas as datas são ambíguas"
        # a coluna EM BR — é este texto que chega no TCF
        vals = [d.strftime("%d/%m/%Y") for d in datas]
        hig = json.loads(json.dumps(vals)) == vals

        _escreve(RAIZ / "inputs" / f"{nome}--{'json-lib-like' if hig else 'fora-do-json'}.input.json",
                 json.dumps({
                     "_o_que_e": f"{len(vals)} datas escritas em BR (DD/MM/YYYY), TODAS ambíguas "
                                 "(dia e mês ≤ 12): a mesma string tem leitura válida em BR e em US",
                     "_por_que_este_caso": porque,
                     "_higiene": {"sobrevive_json": hig,
                                  "como": "json.loads(json.dumps(x)) == x"},
                     "amostra_12": vals[:12], "n_total": len(vals),
                 }, ensure_ascii=False, indent=1) + "\n")

        reg = {"caso": nome, "porque": porque, "n": len(vals)}

        # (a) IGNORAR: string pura, o que o TCF faz hoje
        w0 = encode(vals)
        assert decode(w0) == vals
        reg["ignorar_bytes"] = len(w0.encode())
        _escreve(RAIZ / "outputs" / f"{nome}--ignorar.tcf", w0)

        # (b) spec CERTO e (c) spec ERRADO — os dois têm de fazer RT
        for rot, spec in (("certo-br", BR), ("errado-us", US)):
            tx, n_ok = spec.para(vals)
            w = encode(tx)
            volta = spec.de(decode(w))
            if volta != vals:
                i = next((k for k in range(len(vals)) if volta[k] != vals[k]), None)
                falhas.append(f"{nome}/{rot}: RT QUEBROU em [{i}] {volta[i]!r} != {vals[i]!r}")
                continue
            reg[f"{rot}_bytes"] = len(w.encode())
            reg[f"{rot}_compressiveis_pct"] = round(100 * n_ok / len(vals), 1)
            _escreve(RAIZ / "outputs" / f"{nome}--{rot}.tcf", w)
            _escreve(RAIZ / "outputs" / f"{nome}--{rot}.roundtrip.json", json.dumps({
                "_o_que_e": f"round-trip de '{nome}' com o spec {rot.upper()}",
                "_a_tese": "o spec ERRADO tem de fazer RT igual ao certo. Se fizer, a "
                           "ambiguidade custa BYTES e não INTEGRIDADE.",
                "spec_usado": spec.nome, "formato_do_spec": spec.fmt,
                "rt_fechou": volta == vals,
                "valores_compressiveis_pct": round(100 * n_ok / len(vals), 1),
                "entrada_br": vals[:6],
                "apos_o_spec": tx[:6],
                "decode_do_wire": decode(w)[:6],
                "depois_da_inversa": volta[:6],
                "_amostra": f"6 primeiros de {len(vals)}",
            }, ensure_ascii=False, indent=1) + "\n")
            _escreve(RAIZ / "intermediates" / f"{nome}--{rot}.trilha.json", json.dumps({
                "_o_que_e": f"por onde '{nome}' com spec {rot.upper()} passou no codec — "
                            "telemetria real (`SideOutputs`)",
                "_o_que_olhar": "compare `deltas_uniformes` entre o spec certo e o errado: "
                                "é ali que a regularidade aparece ou some",
                **trilha(tx),
            }, ensure_ascii=False, indent=1, default=str) + "\n")

        if "certo-br_bytes" in reg and "errado-us_bytes" in reg:
            reg["custo_da_ambiguidade_pct"] = round(
                100 * (reg["errado-us_bytes"] - reg["certo-br_bytes"]) / reg["certo-br_bytes"], 1)
            # O QUE DECIDE: se o spec entrar como CANDIDATO do min() (o padrao FLOOR do
            # projeto) em vez de substituto, o pior caso cai de volta no wire de hoje.
            reg["com_floor_errado"] = min(reg["errado-us_bytes"], reg["ignorar_bytes"])
            reg["floor_vs_hoje_pct"] = round(
                100 * (reg["com_floor_errado"] - reg["ignorar_bytes"]) / reg["ignorar_bytes"], 1)
        linhas.append(reg)

    _escreve(RAIZ / "intermediates" / "medicoes.json",
             json.dumps(linhas, ensure_ascii=False, indent=2) + "\n")

    L = ["# O custo da ambiguidade de data", "",
         f"`n={N}` por caso. **Todas as datas são ambíguas** (dia e mês ≤ 12): a mesma "
         "string tem leitura válida em BR e em US.", "",
         "| caso | ignorar (hoje) | spec CERTO | spec ERRADO | custo bruto | **com FLOOR** | vs hoje | RT |",
         "|---|---:|---:|---:|---:|---:|---:|:-:|"]
    for r in linhas:
        c, e = r.get("certo-br_bytes"), r.get("errado-us_bytes")
        L.append(f"| `{r['caso']}` | {r['ignorar_bytes']} | {c} | {e} | "
                 f"{r.get('custo_da_ambiguidade_pct', '—')}% | "
                 f"**{r.get('com_floor_errado', '—')}** | "
                 f"**{r.get('floor_vs_hoje_pct', '—')}%** | "
                 f"{'ok' if c and e else '**QUEBROU**'} |")
    L += ["", "A coluna **com FLOOR** é `min(spec errado, ignorar)` — o que sai se o spec "
          "entrar como **candidato** em vez de substituto. **`vs hoje` é o prejuízo real "
          "da ambiguidade.**"]
    L += ["", "## O que cada caso é", "", "| caso | por quê |", "|---|---|"]
    for r in linhas:
        L.append(f"| `{r['caso']}` | {r['porque']} |")
    L += ["", "---", "", f"**falhas de RT: {len(falhas)}**"]
    if falhas:
        L += ["", *(f"- {f}" for f in falhas)]
    _escreve(RAIZ / "outputs" / "medicoes.md", "\n".join(L) + "\n")

    print(f"{len(linhas)} casos · {len(falhas)} falhas de RT")
    for f in falhas:
        print("  FALHA:", f)
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
