"""DATA como TIPO — exploração (dirty). `python run.py`

Até agora data apareceu no lab só como pretexto pra exercer o bN. Aqui ela é o assunto, e o
bN fica em segundo plano: uma das rotas possíveis, não o alvo.

## As quatro perguntas (filosofia do lab sujo)

    ERA    o que a gente supunha? que data é "string com estrutura" e o core dá conta
    FOI    o que já foi medido? só o `dom-datas-incrementais` do EXP-016 (3 datas, 20 B)
    É      o que acontece de fato, nos quatro eixos abaixo
    SERÁ   onde há espaço pra um tratamento por natureza — e onde NÃO há

## Os eixos

    FORMATO    a mesma data em 10 grafias (ISO, BR, US, compacto, epoch, extenso…)
    PRECISÃO   ano → ano-mês → data → datetime → +ms → +tz (8 níveis)
    REGIME     8 de data + 4 de timestamp: incremental, repetido, espalhado, agrupado, log
    ESCALA     n = 12 · 120 · 1200

## Hipóteses NAIVE, medidas como referência

Três ideias óbvias, calculadas sobre os MESMOS dados. **Não são wire** — são o piso do que
um tratamento por natureza teria de bater pra valer a pena:

    H-SPLIT    quebrar em campos (YYYY / MM / DD) e encodar cada um como coluna
    H-DELTA    primeira data por extenso + diferenças em dias
    H-EPOCH    dias desde a época, como número

`src/tcf` NÃO é tocado. Exploração: descreve, não afirma.
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

from dados import (ESCALAS, FORMATOS, PRECISOES, REGIMES, REGIMES_TS,  # noqa: E402
                   BASE_TS, regime, timestamps)

from tcf import decode, encode  # noqa: E402
from tcf.decoder import _separa_sufixo_polaridade  # noqa: E402

for d in ("inputs", "intermediates", "outputs"):
    (RAIZ / d).mkdir(exist_ok=True)


def _escreve(p, texto: str) -> None:
    p.write_text(texto, encoding="utf-8", newline="")     # `\n` fica `\n`, mesmo no Windows


def rota(wire: str) -> str:
    """Nome curto da rota — mesma classificação do EXP-016."""
    resto = wire.split("\n", 1)[0][6:]
    tag, suf = _separa_sufixo_polaridade(resto)
    corpo = tag if suf else resto
    d, d2 = corpo[:1], corpo[1:2]
    pol = "+pol" if suf else ""
    if d in ("B", "C"):
        return f"bN{pol}"
    if d == "":
        return f"core{pol}"
    if d in ("b", "n", "s") and d2 in ("B", "C"):
        return f"bN-tipado-{d}{pol}"
    if d in ("b", "n", "s"):
        return f"tipado-{d}{pol}"
    return f"outro-{d!r}{pol}"


def med(vals) -> dict:
    """Encoda, confere o RT e devolve `(bytes, rota, wire)`. RT quebrado = falha do lab."""
    w = encode(vals)
    if decode(w) != vals:
        raise AssertionError(f"RT quebrado em {vals[:3]}")
    return {"bytes": len(w.encode()), "rota": rota(w), "wire": w}


# ────────────────────────────────────────────── as hipóteses naive (não são wire)
def h_split(datas) -> int:
    """Campos separados. Soma dos corpos + 2 B de separador por campo (estimativa grosseira)."""
    campos = list(zip(*[d.isoformat().split("-") for d in datas]))
    return sum(len(encode(list(c)).encode()) for c in campos)


def h_delta(datas) -> int:
    """1ª data por extenso + diferenças em dias como coluna própria."""
    if len(datas) < 2:
        return len(encode([datas[0].isoformat()]).encode())
    deltas = [str((datas[i] - datas[i - 1]).days) for i in range(1, len(datas))]
    return (len(encode([datas[0].isoformat()]).encode())
            + len(encode(deltas).encode()))


def h_epoch(datas) -> int:
    return len(encode([str(d.toordinal()) for d in datas]).encode())


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    tudo = []

    # ── EIXO FORMATO × ESCALA (regime fixo: diário, o mais comum) ────────────
    for n in ESCALAS:
        datas = regime("R1-diario", n)
        for fmt, f in FORMATOS.items():
            vals = [f(d) for d in datas]
            r = med(vals)
            tudo.append({"eixo": "formato", "caso": fmt, "n": n,
                         "len_valor": len(vals[0]), "k": len(set(vals)), **r})
            if n == 120:
                _escreve(RAIZ / "outputs" / f"formato-{fmt}.tcf", r["wire"])

    # ── EIXO PRECISÃO × ESCALA ──────────────────────────────────────────────
    for n in ESCALAS:
        ts = [BASE_TS + _dt.timedelta(seconds=97 * i) for i in range(n)]
        for prec, f in PRECISOES.items():
            vals = [f(t) for t in ts]
            r = med(vals)
            tudo.append({"eixo": "precisao", "caso": prec, "n": n,
                         "len_valor": len(vals[0]), "k": len(set(vals)), **r})
            if n == 120:
                _escreve(RAIZ / "outputs" / f"precisao-{prec}.tcf", r["wire"])

    # ── EIXO REGIME × ESCALA (formato fixo: ISO) + hipóteses naive ──────────
    for n in ESCALAS:
        for reg in REGIMES:
            datas = regime(reg, n)
            vals = [d.isoformat() for d in datas]
            r = med(vals)
            tudo.append({"eixo": "regime", "caso": reg, "n": n,
                         "len_valor": 10, "k": len(set(vals)), **r,
                         "h_split": h_split(datas), "h_delta": h_delta(datas),
                         "h_epoch": h_epoch(datas)})
            if n == 120:
                _escreve(RAIZ / "outputs" / f"regime-{reg}.tcf", r["wire"])
        for reg in REGIMES_TS:
            ts = timestamps(reg, n)
            vals = [t.isoformat(sep="T") for t in ts]
            r = med(vals)
            tudo.append({"eixo": "regime-ts", "caso": reg, "n": n,
                         "len_valor": len(vals[0]), "k": len(set(vals)), **r})
            if n == 120:
                _escreve(RAIZ / "outputs" / f"regime-{reg}.tcf", r["wire"])

    for reg in REGIMES:
        _escreve(RAIZ / "inputs" / f"regime-{reg}.json",
                 json.dumps([d.isoformat() for d in regime(reg, 120)],
                            ensure_ascii=False, indent=1) + "\n")

    _escreve(RAIZ / "intermediates" / "medicoes.json",
             json.dumps([{k: v for k, v in r.items() if k != "wire"} for r in tudo],
                        ensure_ascii=False, indent=2) + "\n")
    _relatorio(tudo)
    print(f"{len(tudo)} medições · {len(list((RAIZ / 'outputs').glob('*.tcf')))} wires gravados")
    return 0


def _relatorio(tudo):
    def sel(eixo, n):
        return [r for r in tudo if r["eixo"] == eixo and r["n"] == n]

    L = ["# DATA como tipo — exploração", "",
         "`bytes/valor` = bytes do wire ÷ n. É a métrica que compara formatos de tamanhos",
         "diferentes; o wire cru favoreceria sempre o formato mais curto.", ""]

    L += ["## Eixo FORMATO — a mesma sequência diária, 10 grafias", ""]
    for n in ESCALAS:
        L += [f"### n = {n}", "",
              "| formato | len | k | bytes | bytes/valor | rota |",
              "|---|---:|---:|---:|---:|---|"]
        for r in sorted(sel("formato", n), key=lambda x: x["bytes"]):
            L.append(f"| `{r['caso']}` | {r['len_valor']} | {r['k']} | {r['bytes']} | "
                     f"{r['bytes'] / r['n']:.2f} | {r['rota']} |")
        L.append("")

    L += ["## Eixo PRECISÃO — campo a campo, sobre o mesmo instante", ""]
    for n in ESCALAS:
        L += [f"### n = {n}", "",
              "| precisão | len | k | bytes | bytes/valor | Δ vs anterior | rota |",
              "|---|---:|---:|---:|---:|---:|---|"]
        ant = None
        for r in sel("precisao", n):
            d = f"{r['bytes'] - ant:+d}" if ant is not None else "—"
            ant = r["bytes"]
            L.append(f"| `{r['caso']}` | {r['len_valor']} | {r['k']} | {r['bytes']} | "
                     f"{r['bytes'] / r['n']:.2f} | {d} | {r['rota']} |")
        L.append("")

    L += ["## Eixo REGIME — como os valores se distribuem", "",
          "As três últimas colunas são **hipóteses naive**, não wire: o piso que um",
          "tratamento por natureza teria de bater.", ""]
    for n in ESCALAS:
        L += [f"### n = {n} — datas (ISO)", "",
              "| regime | k | bytes | bytes/valor | rota | H-split | H-delta | H-epoch | melhor |",
              "|---|---:|---:|---:|---|---:|---:|---:|---|"]
        for r in sel("regime", n):
            cands = {"TCF": r["bytes"], "split": r["h_split"],
                     "delta": r["h_delta"], "epoch": r["h_epoch"]}
            melhor = min(cands, key=cands.get)
            marca = f"**{melhor}**" if melhor != "TCF" else "TCF"
            L.append(f"| `{r['caso']}` | {r['k']} | {r['bytes']} | {r['bytes'] / r['n']:.2f} | "
                     f"{r['rota']} | {r['h_split']} | {r['h_delta']} | {r['h_epoch']} | {marca} |")
        L += ["", f"### n = {n} — timestamps", "",
              "| regime | len | k | bytes | bytes/valor | rota |", "|---|---:|---:|---:|---:|---|"]
        for r in sel("regime-ts", n):
            L.append(f"| `{r['caso']}` | {r['len_valor']} | {r['k']} | {r['bytes']} | "
                     f"{r['bytes'] / r['n']:.2f} | {r['rota']} |")
        L.append("")

    _escreve(RAIZ / "outputs" / "medicoes.md", "\n".join(L) + "\n")


if __name__ == "__main__":
    sys.exit(main())
