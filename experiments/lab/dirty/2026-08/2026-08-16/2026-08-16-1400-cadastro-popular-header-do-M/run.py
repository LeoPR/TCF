# -*- coding: utf-8 -*-
"""CADASTRO POPULAR no `.8M` — a construção do header com specs variados, pra inspeção.

    python run.py     # sai 0 só se todos os RTs fecharem e o invariante de fronteira bater

## O pedido (owner, 2026-08-15)

*"um cadastro simples e popular de transmissão, com o básico de nome, cpf, email, telefone,
data de nascimento e um flag de ativo/inativo... a intenção agora é ver a construção do header
com alguns specs variados... revisar a parte de término de coluna, quando uma acaba e outra
começa... o .8 é pra funcionalidade e resumo das coisas."*

## O que a sonda prévia já mostrou (e o lab grava)

1. **`:cpf` aplica e VENCE o FLOOR** (rate=1.0, used=True) — o header carrega `!<size>=cpf:cpf`.
2. **`:dt` aplica mas PERDE o FLOOR** pro split `%` em data de nascimento (rate=1.0,
   used=False) — o header sai `%<size>=nascimento`, sem `:dt`. Honesto: o FLOOR decide.
3. **`int-pad` NÃO aplica em id de largura uniforme** (`format_noncanonical`) — investigado
   no Bloco 1.
4. **flag como BOOL vira a tabela inteira pra `.8H`** (+33%) — a fronteira do `_tabela_flat`.
5. Por coluna, flat × `.8M` mostram o gap de candidatos NOS DOIS SENTIDOS: `ativo` flat-bN
   105 B contra `@dict` 522 B; `nascimento` `.8M`-split 2062 B contra flat 5462 B.

## CPF — a política, resolvida pelo precedente do repo

A suíte soldada (`tests/test_nature_compete.py:21-48`) GERA CPFs DV-válidos algoritmicamente
(base sequencial/aleatória via seed + DV mod-11 calculado). Este lab usa o MESMO gerador,
mesma disciplina: são CPFs-contador sintéticos, não amostrados de distribuição real.

## GATE

`src/tcf` INTOCADO. Dado 100% sintético e determinístico (seed fixa), sem `Z:`.
"""
from __future__ import annotations

import datetime as _dt
import json
import pathlib
import random
import shutil
import sys

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
assert (REPO / "src" / "tcf").is_dir(), f"REPO errado: {REPO}"
sys.path.insert(0, str(REPO / "src"))

from tcf import decode, encode                                    # noqa: E402
from tcf.natures import (                                          # noqa: E402
    SPEC_CPF, SPEC_DATA_ISO, encode_value, int_pad_para,
)
from tcf.side_outputs import SideOutputs                           # noqa: E402

INP, OUT = RAIZ / "inputs", RAIZ / "outputs"
JSON_KW = {"ensure_ascii": False, "indent": 1}
SEED, N = 20260815, 500


def _esc(p, t):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(t, encoding="utf-8", newline="")


def _js(p, o):
    _esc(p, json.dumps(o, **JSON_KW))


def B(t):
    return len(t.encode("utf-8"))


# ── o gerador de CPF da suíte soldada (tests/test_nature_compete.py:21-29) ──
def _cpf_dv(b9):
    ds = [int(c) for c in b9]
    d1 = (sum(d * w for d, w in zip(ds, range(10, 1, -1))) * 10) % 11 % 10
    d2 = (sum(d * w for d, w in zip(ds + [d1], range(11, 1, -1))) * 10) % 11 % 10
    return f"{d1}{d2}"


def _cpf(b9):
    return f"{b9[:3]}.{b9[3:6]}.{b9[6:9]}-{_cpf_dv(b9)}"


def cadastro():
    """O cadastro popular: 7 colunas plausíveis, todas string (a condição do `.8M`)."""
    rng = random.Random(SEED)
    n1 = ["ana", "bruno", "carla", "diego", "edna", "felipe", "gilda", "hugo", "iara",
          "jonas", "karen", "luis", "marta", "nilo", "olga", "paulo", "rita", "saulo",
          "tania", "vitor"]
    n2 = ["silva", "souza", "oliveira", "santos", "lima", "pereira", "costa", "gomes",
          "rocha", "alves"]
    nome = [f"{rng.choice(n1).title()} {rng.choice(n2).title()}" for _ in range(N)]
    return {
        "id":         [f"{i + 1:06d}" for i in range(N)],
        "nome":       nome,
        "cpf":        [_cpf(f"{rng.randint(0, 999999999):09d}") for _ in range(N)],
        "email":      [f"{x.split()[0].lower()}.{x.split()[1].lower()}{rng.randint(1, 99)}"
                       f"@{rng.choice(['gmail.com', 'hotmail.com', 'yahoo.com.br'])}"
                       for x in nome],
        "telefone":   [f"+55 11 9{rng.randint(1000, 9999)}-{rng.randint(1000, 9999)}"
                       for _ in range(N)],
        "nascimento": [(_dt.date(1950, 1, 1) + _dt.timedelta(days=rng.randint(0, 20000)))
                       .isoformat() for _ in range(N)],
        "ativo":      [rng.choice(["ativo", "inativo"]) for _ in range(N)],
    }


# ── anatomia do header: o parser REAL do formato (paridade por construção) ──
def anatomia(wire):
    """Decompõe a linha 1 do `.8M` com o `_parse_meta` do próprio formato, e devolve
    a lista de colunas com fronteiras de corpo: [(nome, modo, nat, ini, fim)]."""
    from tcf.multi.core import _parse_meta
    line1, _, body = wire.partition("\n")
    meta = line1[7:]                      # após '#TCF.8M'
    cols = _parse_meta(meta)
    corpo = body.encode("utf-8")
    out, off = [], 0
    for size, nomec, modo, nat in cols:
        fim = len(corpo) if size is None else off + size
        out.append({"nome": nomec, "modo": modo, "nat": nat,
                    "size_hex": None if size is None else format(size, "x"),
                    "ini": off, "fim": fim, "bytes": fim - off})
        off = fim
    return line1, corpo, out


def imprime_anatomia(rotulo, wire):
    line1, corpo, cols = anatomia(wire)
    print(f"\n  {rotulo}")
    print(f"  linha 1 ({B(line1)} B): {line1!r}")
    print(f"  {'coluna':<12} {'modo':<6} {'nat':<5} {'size(hex)':>9} {'bytes':>7} "
          f"{'[ini:fim)':>15}  começo do corpo")
    for c in cols:
        seg = corpo[c["ini"]:c["ini"] + 22].decode("utf-8", "replace").replace("\n", "⏎")
        sh = c["size_hex"] if c["size_hex"] is not None else "(EOF)"
        nomec = c["nome"] if c["nome"] is not None else "(anon)"
        print(f"  {nomec:<12} {c['modo']:<6} {c['nat'] or '-':<5} {sh:>9} "
              f"{c['bytes']:>7} {f'[{c['ini']}:{c['fim']})':>15}  {seg!r}")
    # O INVARIANTE de fronteira: as fatias cobrem o corpo inteiro, sem furo nem sobra.
    assert cols[0]["ini"] == 0 and cols[-1]["fim"] == len(corpo), "fronteira FUROU"
    for a, b in zip(cols, cols[1:]):
        assert a["fim"] == b["ini"], f"furo entre {a['nome']} e {b['nome']}"
    return cols


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for p in (INP, OUT):
        if p.exists():
            shutil.rmtree(p)
        p.mkdir(parents=True)
    falhas = []
    T = cadastro()
    _js(INP / "cadastro.entrada.json", T)
    _js(INP / "cadastro.fonte.json", {
        "gerador": "run.py::cadastro()", "seed": SEED, "n": N,
        "colunas": list(T),
        "cpf": "gerador da suite soldada (tests/test_nature_compete.py:21-29): base "
               "aleatoria com seed + DV mod-11 calculado — CPF-contador sintetico, nao "
               "amostrado de distribuicao real",
        "pin": "100% sintetico e deterministico; sem Z:"})

    # ── BLOCO 1 — cada spec contra sua coluna: aplica? ──────────────────────
    print("BLOCO 1 — o spec aplica na coluna? (encode_value, por valor)\n")
    from collections import Counter
    ipad = int_pad_para(T["id"])
    print(f"  int_pad_para(id) = {ipad!r}")
    print("    (id tem largura UNIFORME 6; o int-pad existe pra normalizar largura MISTA —")
    print("     coluna ja uniforme nao precisa dele, e o construtor devolve o que se ve acima)")
    SPECS = {"cpf": SPEC_CPF, "nascimento": SPEC_DATA_ISO}
    if ipad is not None:
        SPECS["id"] = ipad
    b1 = {"int_pad_para_id": repr(ipad)}
    for c, sp in SPECS.items():
        sts = Counter(encode_value(sp, v)[1] for v in T[c])
        print(f"  {c:<11} spec={sp.name:<9} by_status={dict(sts)}")
        b1[c] = {"spec": sp.name, "by_status": dict(sts)}

    # ── BLOCO 2 — o wire, sem e com specs, com a ANATOMIA do header ─────────
    print("\nBLOCO 2 — a construção do header (o centro do lab)")
    w0 = encode(T)
    if decode(w0) != T:
        falhas.append("RT do .8M sem specs")
    _esc(OUT / "cadastro-sem-spec.tcf", w0)
    _js(OUT / "cadastro-sem-spec.roundtrip.json", decode(w0))
    cols0 = imprime_anatomia(f"SEM specs — {B(w0)} B", w0)

    side = SideOutputs()
    w1 = encode(T, nature_per_col=SPECS, side_outputs=side)
    if decode(w1) != T:
        falhas.append("RT do .8M com specs")
    _esc(OUT / "cadastro-com-spec.tcf", w1)
    _js(OUT / "cadastro-com-spec.roundtrip.json", decode(w1))
    cols1 = imprime_anatomia(f"COM specs (nature_per_col) — {B(w1)} B "
                             f"({100 * (1 - B(w1) / B(w0)):.1f}% menor)", w1)
    print("\n  o FLOOR por coluna (side_outputs.nature_apply):")
    na = {}
    for c, st in (side.nature_apply or {}).items():
        print(f"    {c:<11} apply_rate={st.get('apply_rate')}  used={st.get('used')}"
              f"{'   <- aplicou e VENCEU' if st.get('used') else '   <- aplicou mas o FLOOR preferiu outro candidato' if st.get('apply_rate') == 1.0 else ''}")
        na[c] = {k: v for k, v in st.items() if k in ("apply_rate", "used", "by_status")}

    # ── BLOCO 3 — as variantes de grafia do header ──────────────────────────
    print("\nBLOCO 3 — variantes de grafia do MESMO conteúdo")
    wf = encode(T, nature_per_col=SPECS, min_header=False)
    wd = encode(T, nature_per_col=SPECS, drop_names=True)
    if decode(wf) != T:
        falhas.append("RT min_header=False")
    dd = decode(wd)
    if list(dd.values()) != list(T.values()):
        falhas.append("RT drop_names (valores)")
    _esc(OUT / "cadastro-header-cheio.tcf", wf)
    _esc(OUT / "cadastro-sem-nomes.tcf", wd)
    b3 = {}
    for rot, w in (("default (min_header)", w1), ("min_header=False", wf),
                   ("drop_names=True", wd)):
        l1 = w.split("\n", 1)[0]
        b3[rot] = {"linha1_B": B(l1), "total_B": B(w), "linha1": l1}
        print(f"  {rot:<22} linha1={B(l1):>4} B  total={B(w):>6} B   {l1[:64]!r}")
    print(f"  (drop_names: decode devolve nomes POSICIONAIS '0'..'{len(T)-1}' — os valores "
          f"conferem: {list(dd.values()) == list(T.values())})")

    # ── BLOCO 4 — a fronteira: um tipo nativo vira a rota inteira ───────────
    print("\nBLOCO 4 — a FRONTEIRA: flag como bool empurra a tabela pro .8H")
    Tb = {**T, "ativo": [v == "ativo" for v in T["ativo"]]}
    wb = encode(Tb)
    if decode(wb) != Tb:
        falhas.append("RT do .8H (flag bool)")
    _esc(OUT / "cadastro-flag-bool.tcf", wb)
    print(f"  flag string  -> {w1.split(chr(10), 1)[0][:10]}…  {B(w1):>6} B  (.8M, com specs)")
    print(f"  flag BOOL    -> {wb.split(chr(10), 1)[0][:10]}…  {B(wb):>6} B  (.8H, specs NAO entram: "
          f"{100 * (B(wb) / B(w1) - 1):+.1f}%)")
    print("  => no .8M de hoje, tipar UMA coluna troca a rota da tabela INTEIRA")
    print("     (é o `_tabela_flat`, encoder.py:146 — e o custo é o candidato único do .8H,")
    print("      T-8H-UM-CANDIDATO-SO, não a tipagem em si)")

    # ── BLOCO 5 — por coluna: o que o flat faria (o gap de candidatos AQUI) ─
    print("\nBLOCO 5 — a mesma coluna sozinha: flat × .8M (o gap de candidatos neste dado)")
    print(f"  {'coluna':<12} {'flat':>7} {'modo flat':<13} {'.8M':>7} {'modo .8M':<8} quem")
    b5 = []
    for c in T:
        # JUSTA: o spec vai pros DOIS lados (flat via nature=, .8M via nature_per_col=)
        wflat = encode(T[c], nature=SPECS[c]) if c in SPECS else encode(T[c])
        w1c = encode({c: T[c]}, nature_per_col={c: SPECS[c]} if c in SPECS else None)
        if decode(wflat) != T[c]:
            falhas.append(f"RT flat {c}")
        hf = wflat.split("\n", 1)[0]
        _, _, colsc = anatomia(w1c)
        modo_m = colsc[0]["modo"] + (f":{colsc[0]['nat']}" if colsc[0]["nat"] else "")
        quem = "flat" if B(wflat) < B(w1c) else ".8M"
        b5.append({"coluna": c, "flat_B": B(wflat), "flat_header": hf,
                   "m_B": B(w1c), "m_modo": modo_m, "vence": quem})
        print(f"  {c:<12} {B(wflat):>7} {hf[:13]:<13} {B(w1c):>7} {modo_m:<8} {quem}")
    vf = sum(1 for x in b5 if x["vence"] == "flat")
    print(f"\n  flat vence em {vf}/{len(b5)} — nenhum lado domina; a resposta registrada é a")
    print(f"  UNIÃO dos candidatos (T-UM-CAMINHO-SO), não a troca de um pelo outro.")

    # ── INDEX pra inspeção ──────────────────────────────────────────────────
    linhas_idx = [
        "# INDEX — cadastro popular: o header do `.8M` com specs, pra inspeção", "",
        f"n={N}, seed={SEED}. Todos os wires com RT validado (falhas: {len(falhas)}).", "",
        "| wire | B | linha 1 |", "|---|---|---|"]
    for f_, w_ in (("cadastro-sem-spec.tcf", w0), ("cadastro-com-spec.tcf", w1),
                   ("cadastro-header-cheio.tcf", wf), ("cadastro-sem-nomes.tcf", wd),
                   ("cadastro-flag-bool.tcf", wb)):
        linhas_idx.append(f"| [`{f_}`](./{f_}) | {B(w_)} | `{w_.split(chr(10), 1)[0][:72]}` |")
    linhas_idx += ["", "## A anatomia do header COM specs (fronteiras de coluna)", "",
                   "| coluna | modo | nat | size hex | bytes | [ini:fim) |", "|---|---|---|---|---|---|"]
    for c in cols1:
        linhas_idx.append(
            f"| {c['nome']} | `{c['modo']}` | {c['nat'] or '—'} | "
            f"`{c['size_hex'] or '(EOF)'}` | {c['bytes']} | [{c['ini']}:{c['fim']}) |")
    _esc(OUT / "INDEX.md", "\n".join(linhas_idx) + "\n")

    _js(RAIZ / "resultado.json", {
        "bloco1_specs": b1, "bloco2_nature_apply": na,
        "bloco2_bytes": {"sem_spec": B(w0), "com_spec": B(w1)},
        "bloco2_anatomia_com_spec": cols1, "bloco3_grafias": b3,
        "bloco4_fronteira": {"m_com_spec": B(w1), "h_flag_bool": B(wb)},
        "bloco5_flat_vs_m": b5, "falhas": falhas,
        "CONSTANTE_na_comparacao": "o MESMO cadastro (mesma seed) em todos os blocos; "
                                   "muda so' o kwarg/tipo/forma de chamada"})

    print(f"\n{len(falhas)} falha(s)")
    for f_ in falhas:
        print(f"  FALHA: {f_}")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
