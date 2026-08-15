# -*- coding: utf-8 -*-
"""VIEW x COLUNAS TIPADAS — o `view` alcança o dado tipado? E o que custa não alcançar?

    python run.py

## O que este lab fecha

O owner adiou o `view` até "fechar todos os tipos". Os tipos fecharam (date, hora, float,
datetime, int, bool). A pergunta agora é direta: **o `view` funciona sobre coluna tipada?**

O `T-LAZY-BYPASS-ARITMETICO` já mapeou o lado SINGLE-COL (dispatch-only, ~20-25 linhas,
prototipado). O lado que ninguém mediu é o **`.8H`** — e é exatamente lá que a tabela tipada
mora.

## O achado que orienta o lab (declarado antes de medir)

`_tabela_flat` (`encoder.py:134-147`) exige `isinstance(x, str)` em TODO valor. Logo:

    qualquer coluna tipada  ->  .8H  ->  o view recusa

Então "view para colunas tipadas" **não é uma lacuna do view**. É consequência do dispatch,
um nível acima. A hipótese a medir é o TAMANHO dessa consequência.

## PREDIÇÃO DECLARADA (antes de rodar)

1. O view abre `.8M` e recusa todo o resto — inclusive todas as formas single-col.
2. Tipar UMA coluna de uma tabela retangular muda a rota e fecha o view.
3. **O custo em bytes vem do ENVELOPE `.8H`, não da tipagem** — uma tabela toda-string
   forçada ao `.8H` deve custar aproximadamente o mesmo que a tipada.
   (Se a 3 falhar, o problema é a tipagem e não a rota — muda a conclusão.)

## GATE

`src/tcf` INTOCADO. Nada aqui é proposta de weld — é a conta que precede a decisão.
"""
from __future__ import annotations

import datetime as _dt
import json
import pathlib
import random
import shutil
import sys
import time

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
assert (REPO / "src" / "tcf").is_dir(), f"REPO errado: {REPO}"
sys.path.insert(0, str(REPO / "src"))

from tcf import decode, encode, view                       # noqa: E402
from tcf.natures import SPEC_DATA_ISO                      # noqa: E402

INP, INT, OUT = RAIZ / "inputs", RAIZ / "intermediates", RAIZ / "outputs"
JSON_KW = {"ensure_ascii": False, "indent": 1}
N = 5000
SEED = 11


def _esc(p, t):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(t, encoding="utf-8", newline="")


def _js(p, o):
    _esc(p, json.dumps(o, **JSON_KW))


def B(t):
    return len(t.encode("utf-8"))


def rota(w):
    """A rota que o wire declara, lida do discriminador (ADR-0029)."""
    d = w[6:7]
    return {"M": "multi .8M", "H": "hier .8H"}.get(d, f"single {d!r}")


def abre(w):
    try:
        view(w)
        return True
    except Exception:
        return False


def _attr(o, n):
    """`materialized_bytes`/`total_bytes` sao ATRIBUTOS; `columns` e' metodo. Tolera os dois."""
    a = getattr(o, n)
    return a() if callable(a) else a


def cron(fn, rep=5):
    fn()
    ts = []
    for _ in range(rep):
        t0 = time.perf_counter()
        fn()
        ts.append(time.perf_counter() - t0)
    return min(ts) * 1000


# ── a tabela: realista, retangular, e a MESMA em todas as variantes ─────────
def tabela():
    rnd = random.Random(SEED)
    base = _dt.date(2015, 1, 1).toordinal()
    return {
        "data":    [_dt.date.fromordinal(base + rnd.randint(0, 4000)).isoformat()
                    for _ in range(N)],
        "cliente": [f"cliente-{rnd.randint(1, 400):03d}" for _ in range(N)],
        "produto": [f"SKU-{rnd.randint(1, 900):04d}" for _ in range(N)],
        "qtd":     [str(rnd.randint(1, 99)) for _ in range(N)],
        "preco":   [f"{rnd.uniform(1, 500):.2f}" for _ in range(N)],
    }


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for p in (INP, INT, OUT):
        if p.exists():
            shutil.rmtree(p)
        p.mkdir(parents=True)
    falhas, reg = [], {}

    COLS = tabela()
    TIPADA = {**COLS,
              "qtd": [int(x) for x in COLS["qtd"]],
              "preco": [float(x) for x in COLS["preco"]]}
    # a MESMA tabela como list[dict] — força o `.8H` SEM tipar nada (isola o ENVELOPE)
    RECS_STR = [dict(zip(COLS, t)) for t in zip(*COLS.values())]

    _js(INP / "tabela.entrada.json", COLS)
    _js(INP / "tabela.fonte.json", {
        "gerador": "run.py::tabela()", "seed": SEED, "n": N,
        "colunas": "data(ISO) cliente produto qtd preco — retangular, sem nulls",
        "ideia": "tabela de pedidos plausivel; as 3 variantes tem os MESMOS valores, "
                 "so' muda o TIPO Python e a FORMA de chamada",
        "pin": "sinteticp determinístico (random.Random(SEED)), sem Z:",
    })

    # ── BLOCO 1 — quais formas de wire o view abre ──────────────────────────
    print("BLOCO 1 — quais formas de wire o `view` abre\n")
    rnd = random.Random(SEED + 1)
    DATAS = COLS["data"][:200]
    STRS = COLS["cliente"][:200]
    FORMAS = [
        ("single string (bN/OBAT)",  lambda: encode(STRS)),
        ("single + spec `:dt`",      lambda: encode(DATAS, nature=SPEC_DATA_ISO)),
        ("tipado n (int)",           lambda: encode([rnd.randint(1, 999999) for _ in range(200)])),
        ("tipado n (float)",         lambda: encode([i + 0.5 for i in range(200)])),
        ("tipado b (bool)",          lambda: encode([rnd.random() > .5 for _ in range(200)])),
        ("tipado n denso (nB)",      lambda: encode([rnd.choice([0, 1]) for _ in range(200)])),
        ("stamp / vazio",            lambda: encode([])),
        ("MULTI .8M (todo string)",  lambda: encode({"d": DATAS, "s": STRS})),
        ("MULTI .8M + spec",         lambda: encode({"d": DATAS, "s": STRS},
                                                    nature_per_col={"d": SPEC_DATA_ISO})),
        ("HIER .8H",                 lambda: encode([{"d": a, "s": b} for a, b in zip(DATAS, STRS)])),
    ]
    print(f"  {'forma':<26} {'rota':<12} {'view':<8} header")
    linhas_f = []
    for rot, fn in FORMAS:
        w = fn()
        ok = abre(w)
        _esc(OUT / f"forma-{rot.split()[0].lower()}-{len(linhas_f):02d}.tcf", w)
        linhas_f.append({"forma": rot, "rota": rota(w), "view_abre": ok,
                         "bytes": B(w), "header": w.split("\n", 1)[0][:40]})
        print(f"  {rot:<26} {rota(w):<12} {'ABRE' if ok else 'RECUSA':<8} "
              f"{w.split(chr(10), 1)[0][:38]!r}")
    n_abre = sum(1 for x in linhas_f if x["view_abre"])
    print(f"\n  ABRE {n_abre} de {len(linhas_f)} formas — "
          f"{'so as .8M' if all(x['rota'] == 'multi .8M' for x in linhas_f if x['view_abre']) else 'ver tabela'}")
    reg["bloco1_formas"] = linhas_f

    # ── BLOCO 2 — a fronteira do dispatch, e o par de contra-prova ──────────
    print("\nBLOCO 2 — a fronteira: onde a tabela deixa de ser `.8M`")
    wM = encode(COLS)
    wHt = encode(TIPADA)
    wHs = encode(RECS_STR)
    for rot, w in (("M-todo-string", wM), ("H-todo-string", wHs), ("H-2-tipadas", wHt)):
        _esc(OUT / f"tabela-{rot}.tcf", w)
    # RT das tres (gate: nenhuma conclusao vale sem RT)
    for rot, w, esp in (("M-todo-string", wM, COLS),
                        ("H-todo-string", wHs, RECS_STR),
                        ("H-2-tipadas", wHt, TIPADA)):
        try:
            if decode(w) != esp:
                falhas.append(f"{rot}: RT divergiu")
        except Exception as e:
            falhas.append(f"{rot}: RT levantou {type(e).__name__}: {e}")
    _js(OUT / "tabela-M-todo-string.roundtrip.json", decode(wM))

    print(f"  {'variante':<22} {'rota':<12} {'bytes':>9} {'vs .8M':>9}  view")
    b2 = []
    for rot, w in (("todo string (dict)", wM), ("todo string (.8H)", wHs),
                   ("2 cols TIPADAS", wHt)):
        d = 100 * (B(w) / B(wM) - 1)
        b2.append({"variante": rot, "rota": rota(w), "bytes": B(w),
                   "vs_M_pct": round(d, 1), "view_abre": abre(w)})
        print(f"  {rot:<22} {rota(w):<12} {B(w):>9} {d:>+8.1f}%  "
              f"{'ABRE' if abre(w) else 'RECUSA'}")
    reg["bloco2_fronteira"] = b2

    # A CONTRA-PROVA da predicao 3: envelope x tipagem
    delta_envelope = B(wHs) - B(wM)
    delta_tipagem = B(wHt) - B(wHs)
    print(f"\n  CONTRA-PROVA (envelope x tipagem, CONSTANTE = os mesmos valores):")
    print(f"    forcar .8H sem tipar nada : {delta_envelope:+8d} B  <- o ENVELOPE")
    print(f"    tipar 2 colunas dentro do .8H: {delta_tipagem:+8d} B  <- a TIPAGEM")
    veredito = ("o custo e' o ENVELOPE" if abs(delta_envelope) > 5 * abs(delta_tipagem)
                else "a tipagem tambem pesa — predicao 3 REFUTADA")
    print(f"    => {veredito}")
    reg["bloco2_contraprova"] = {
        "delta_envelope_B": delta_envelope, "delta_tipagem_B": delta_tipagem,
        "veredito": veredito,
        "CONSTANTE_na_comparacao": "os MESMOS valores nas tres; muda a FORMA de chamada e o TIPO",
    }

    # ── BLOCO 3 — o que está em jogo: o valor da view ───────────────────────
    print("\nBLOCO 3 — o valor que a tabela tipada perde (dev-run: razoes, nao absolutos)")
    v = view(wM)
    v.where("data", pred=lambda x: x >= "2020-01-01").count()
    frac_where = 100 * _attr(v, "materialized_bytes") / _attr(v, "total_bytes")
    v2 = view(wM)
    v2.select(["cliente"])
    frac_sel = 100 * _attr(v2, "materialized_bytes") / _attr(v2, "total_bytes")
    v3 = view(wM)
    perfil = {c: v3.column_bytes(c) for c in _attr(v3, "columns")}
    print(f"  where+count   tocou {v.touched}  -> {frac_where:.1f}% do blob")
    print(f"  select 1 col  tocou {v2.touched}  -> {frac_sel:.1f}% do blob")
    print(f"  column_bytes  tocou {v3.touched} (perfil SEM descomprimir): {perfil}")

    VERDADE = sum(1 for x in COLS["data"] if x >= "2020-01-01")
    t_v = cron(lambda: view(wM).where("data", pred=lambda x: x >= "2020-01-01").count())
    t_m = cron(lambda: sum(1 for x in decode(wM)["data"] if x >= "2020-01-01"))
    t_h = cron(lambda: sum(1 for x in decode(wHt)["data"] if x >= "2020-01-01"))
    if view(wM).where("data", pred=lambda x: x >= "2020-01-01").count() != VERDADE:
        falhas.append("view.where divergiu da verdade do decode")
    print(f"\n  responder 'quantas linhas com data>=2020' (verdade={VERDADE}):")
    print(f"    view sobre .8M         {t_v:>8.1f} ms   ({frac_where:.1f}% do blob tocado)")
    print(f"    decode completo .8M    {t_m:>8.1f} ms   ({t_m/t_v:>4.1f}x a view)")
    print(f"    decode completo .8H    {t_h:>8.1f} ms   ({t_h/t_v:>4.1f}x a view)  <- UNICA opcao se TIPADA")
    reg["bloco3_valor"] = {
        "pct_blob_where": round(frac_where, 1), "pct_blob_select": round(frac_sel, 1),
        "perfil_column_bytes": perfil, "touched_perfil": list(v3.touched),
        "verdade": VERDADE, "ms_view": round(t_v, 1), "ms_decode_M": round(t_m, 1),
        "ms_decode_H": round(t_h, 1), "razao_M": round(t_m / t_v, 1),
        "razao_H": round(t_h / t_v, 1),
        "AVISO": "dev-run, maquina nao quiescente — razoes, nao absolutos",
    }

    # ── BLOCO 4 — a armadilha da API do where() ─────────────────────────────
    print("\nBLOCO 4 — ARMADILHA DA API: callable POSICIONAL devolve 0 CALADO")
    pos = view(wM).where("data", lambda x: x >= "2020-01-01").count()
    kw = view(wM).where("data", pred=lambda x: x >= "2020-01-01").count()
    print(f"  verdade (decode)                          = {VERDADE}")
    print(f"  where('data', lambda ...)     POSICIONAL  = {pos}   "
          f"{'<- 0 CALADO, resposta ERRADA sem erro' if pos == 0 else ''}")
    print(f"  where('data', pred=lambda ...) KEYWORD    = {kw}   "
          f"{'correto' if kw == VERDADE else 'DIVERGE'}")
    # a causa, verificada: o lambda entra como `value` e e' comparado com `==`
    causa = "assinatura `where(col, value=None, *, pred=None)`: callable posicional vira `value` e cai no `v == value`"
    print(f"  causa: {causa}")
    if kw != VERDADE:
        falhas.append("where(pred=) nao bate com a verdade do decode")
    reg["bloco4_armadilha"] = {
        "verdade": VERDADE, "posicional": pos, "keyword": kw, "causa": causa,
        "classe": "resposta errada SEM erro — mesma familia de `nunca ignorar calado`",
        "CONSTANTE_na_comparacao": "o MESMO wire e o MESMO predicado; so' muda posicional x keyword",
    }

    _js(INT / "medicoes.json", reg)
    _js(RAIZ / "resultado.json", {**reg, "falhas": falhas})
    _esc(OUT / "INDEX.md", "\n".join(
        ["# INDEX — view x colunas tipadas", "",
         "| forma | rota | view abre? | bytes |", "|---|---|---|---|"] +
        [f"| {x['forma']} | {x['rota']} | {'sim' if x['view_abre'] else '**nao**'} | {x['bytes']} |"
         for x in linhas_f]) + "\n")

    print(f"\n{len(falhas)} falha(s)")
    for f in falhas[:10]:
        print(f"  FALHA: {f}")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
