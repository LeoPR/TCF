"""Data LAZY — a fatia mais barata e de maior retorno. `python run.py`

Recorte deliberado (owner: *"prefiro matar algo que dê mais retorno e seja mais fácil"*):
**só o spec ISO**, no molde exato da nature do CPF (per-valor, fallback literal com 1 char).
Os outros formatos são variação do mesmo molde e ficam pra depois.

## As três perguntas que este lab responde

    1. QUANTO RENDE quando o dado é limpo?
    2. A QUE PONTO a válvula de escape mata o ganho? (x% de sujeira e o lazy deixa de pagar)
    3. O RT SOBREVIVE a dado sujo, misturado e ambíguo — sempre, sem exceção?

A (3) é a que decide se a ideia é viável. As outras duas dizem se vale a pena.

## O que NÃO é medido

Custo de **declarar** o spec no wire. O CPF resolve com `#TCF.8 :cpf` (ADR-0027,
self-describing), então existe precedente e é custo fixo de header — mas não está aqui.
Nenhum número deste lab é "o ganho final".

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

from spec_data import SPECS, aplica, desfaz  # noqa: E402

from tcf import decode, encode  # noqa: E402

for d in ("inputs", "intermediates", "outputs"):
    (RAIZ / d).mkdir(exist_ok=True)

ISO = SPECS["iso"]
BASE = _dt.date(2026, 1, 1)
N = 500


def _escreve(p, t):
    p.write_text(t, encoding="utf-8", newline="")


def _lcg(n, mod, semente=987):
    x, out = semente, []
    for _ in range(n):
        x = (1103515245 * x + 12345) % (1 << 31)
        out.append(x % mod)
    return out


def d(i):
    return (BASE + _dt.timedelta(days=i)).isoformat()


# ── os casos: limpo, sujo, misturado, ambíguo, degenerado ────────────────────
def casos():
    c = []
    lim = [d(i) for i in range(N)]
    c.append(("limpo-diario", "ISO puro, passo 1 — o melhor caso", lim))
    c.append(("limpo-mensal", "ISO puro, passo 30 — onde o core mais sofre",
              [d(30 * i) for i in range(N)]))
    c.append(("limpo-espalhado", "ISO puro, sem ordem — onde o ordinal não ajuda",
              [d(x) for x in _lcg(N, 3650)]))

    # SUJEIRA CRESCENTE: o eixo que responde "a que ponto deixa de pagar"
    for pct in (1, 2, 5, 10, 25, 50):
        k = N * pct // 100
        vals = [d(i) for i in range(N)]
        for j in range(k):                                  # espalha a sujeira
            vals[(j * 997) % N] = f"data invalida {j}"
        c.append((f"sujo-{pct:02d}pct", f"{pct}% de valor que não parseia", vals))

    # OUTRAS SUJEIRAS, as que aparecem em dado real
    vals = [d(i) for i in range(N)]
    for j in range(0, N, 20):
        vals[j] = None
    c.append(("com-nulo", "5% de null — o slot do core, não do spec", vals))

    vals = [d(i) for i in range(N)]
    for j in range(0, N, 10):
        vals[j] = ""
    c.append(("com-vazio", "10% de string vazia", vals))

    vals = [d(i) for i in range(N)]
    for j in range(0, N, 4):                                 # 25% em outro formato
        vals[j] = (BASE + _dt.timedelta(days=j)).strftime("%d/%m/%Y")
    c.append(("misto-iso-br", "25% em BR na mesma coluna — o chute errado", vals))

    c.append(("tudo-br", "coluna inteira em BR: o spec ISO erra em 100%",
              [(BASE + _dt.timedelta(days=i)).strftime("%d/%m/%Y") for i in range(N)]))

    # AMBIGUIDADE: dia <= 12, onde BR e US são indistinguíveis
    c.append(("ambiguo-br-us", "só dias 1..12 — BR e US indistinguíveis",
              [f"2026-{(i % 12) + 1:02d}-{(i % 12) + 1:02d}" for i in range(N)]))

    # GRAFIA NÃO-CANÔNICA: parseia mas não é o que o spec emitiria
    vals = [d(i) for i in range(N)]
    vals[0] = "2026-1-01"
    c.append(("grafia-frouxa", "`2026-1-01` parseia mas não é a grafia canônica", vals))

    # BORDAS DE CALENDÁRIO
    c.append(("bissexto", "29/02 em ano bissexto e o dia seguinte",
              ["2024-02-28", "2024-02-29", "2024-03-01"] * (N // 3)))
    c.append(("bissexto-invalido", "29/02 em ano NÃO-bissexto — não existe",
              ["2026-02-28", "2026-02-29", "2026-03-01"] * (N // 3)))
    c.append(("virada-ano", "31/12 -> 01/01, onde o afixo quebra",
              [d(364 + i) for i in range(N)]))
    c.append(("epoca-remota", "ano 1 e ano 9999 — as bordas do calendário",
              ["0001-01-01", "9999-12-31"] * (N // 2)))
    return c


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    linhas, falhas = [], []

    for nome, porque, vals in casos():
        _escreve(RAIZ / "inputs" / f"{nome}.json",
                 json.dumps({"caso": nome, "porque": porque, "n": len(vals),
                             "amostra": vals[:6]}, ensure_ascii=False, indent=1) + "\n")

        # ── SEM o lazy: o que o TCF faz hoje ─────────────────────────────────
        w_sem = encode(vals)
        assert decode(w_sem) == vals, f"{nome}: RT do wire de hoje quebrou"

        # ── COM o lazy: pré-tx, encode, decode, pós-tx ───────────────────────
        tx, contagem = aplica(ISO, vals)
        w_com = encode(tx)
        volta = desfaz(ISO, decode(w_com))

        # A PROVA QUE DECIDE: o round-trip completo devolve os dados ORIGINAIS?
        ok = volta == vals and [type(a) is type(b) for a, b in zip(volta, vals)].count(False) == 0
        if not ok:
            i = next((k for k in range(len(vals)) if volta[k] != vals[k]), None)
            falhas.append(f"{nome}: RT do lazy quebrou em [{i}] "
                          f"{volta[i]!r} != {vals[i]!r}" if i is not None
                          else f"{nome}: RT do lazy quebrou (comprimento)")

        comp = contagem.get("compressible", 0)
        b_sem, b_com = len(w_sem.encode()), len(w_com.encode())
        linhas.append({
            "caso": nome, "porque": porque, "n": len(vals),
            "compressiveis_pct": round(100 * comp / len(vals), 1),
            "status": {k: v for k, v in sorted(contagem.items())},
            "bytes_sem": b_sem, "bytes_com": b_com,
            "delta_pct": round(100 * (b_com - b_sem) / b_sem, 1),
            "vence": "lazy" if b_com < b_sem else ("empate" if b_com == b_sem else "hoje"),
            "rt": ok,
        })
        _escreve(RAIZ / "outputs" / f"{nome}--hoje.tcf", w_sem)
        _escreve(RAIZ / "outputs" / f"{nome}--lazy.tcf", w_com)

    _escreve(RAIZ / "intermediates" / "medicoes.json",
             json.dumps(linhas, ensure_ascii=False, indent=2) + "\n")
    _relatorio(linhas, falhas)
    print(f"{len(linhas)} casos · {len(falhas)} falhas de RT")
    for f in falhas:
        print("  FALHA:", f)
    return 1 if falhas else 0


def _relatorio(linhas, falhas):
    L = ["# Data lazy (spec ISO) — pré-tx no molde da nature do CPF", "",
         f"`n={N}` por caso. **`rt`** = o round-trip completo (pré-tx → encode → decode →",
         "pós-tx) devolve os dados **originais**, com tipo. É a prova que decide a viabilidade;",
         "as colunas de byte só dizem se vale a pena.", "",
         "| caso | % compressível | bytes hoje | bytes lazy | Δ | vence | RT |",
         "|---|---:|---:|---:|---:|:-:|:-:|"]
    for r in linhas:
        L.append(f"| `{r['caso']}` | {r['compressiveis_pct']}% | {r['bytes_sem']} | "
                 f"{r['bytes_com']} | {r['delta_pct']:+.1f}% | "
                 f"{'**lazy**' if r['vence'] == 'lazy' else r['vence']} | "
                 f"{'ok' if r['rt'] else '**QUEBROU**'} |")

    L += ["", "## Por que cada valor não foi comprimido", "",
          "| caso | contagem por status |", "|---|---|"]
    for r in linhas:
        st = " · ".join(f"`{k}`={v}" for k, v in r["status"].items() if k != "compressible")
        L.append(f"| `{r['caso']}` | {st or '—'} |")

    L += ["", "## Onde a válvula de escape mata o ganho", "",
          "| sujeira | % compressível | Δ bytes | vence |", "|---|---:|---:|:-:|"]
    for r in linhas:
        if r["caso"].startswith("sujo-"):
            L.append(f"| {r['caso'][5:]} | {r['compressiveis_pct']}% | "
                     f"{r['delta_pct']:+.1f}% | {r['vence']} |")

    L += ["", "---", "", f"**falhas de RT: {len(falhas)}**"]
    if falhas:
        L += ["", *(f"- {f}" for f in falhas)]
    _escreve(RAIZ / "outputs" / "medicoes.md", "\n".join(L) + "\n")


if __name__ == "__main__":
    sys.exit(main())
