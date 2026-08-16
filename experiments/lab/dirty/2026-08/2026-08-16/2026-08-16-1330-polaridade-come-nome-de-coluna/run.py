# -*- coding: utf-8 -*-
"""RT QUEBRADO CALADO: a polaridade come o fim do nome da coluna no `.8M` e no `.8H`.

    python run.py     # ANTES do fix: sai 0 se REPRODUZIR o defeito
                      # DEPOIS do fix: sai 0 se o defeito SUMIR e nada legítimo regredir

O lab se AUTODETECTA: mede o comportamento, decide se está rodando contra `src/` com ou
sem o fix, e aplica o critério de saída correspondente. Os artefatos levam o estado no
nome (`antes-`/`depois-`), então as duas rodadas coexistem e são diffáveis.

## O defeito

`decode({"obs.": [...]})` devolve a chave `"obs"`. Com pontuação DOBRADA (`"obs.."`), além
da chave, **os valores também corrompem**. Nenhum warning, nenhuma exceção.

## O mecanismo, verificado

A polaridade é **camada de borda, a PRIMEIRA coisa do decode** (`decoder.py:154-161`):

    _tag, _sufixo = _separa_sufixo_polaridade(line1[6:])

Ela roda sobre `line1[6:]` — que no `.8M` é `M<meta>`, e no fim do meta está o **nome da
última coluna** (forma `min_header`, `multi/core.py:413-414`). A polaridade não sabe disso:
vê `Mobs.`, separa `('Mobs', '.')`, e entrega ao parser um meta onde a coluna se chama `obs`.

O separador **já é conservador** (`decoder.py:294`: só separa se a tag for alfanumérica) —
é por isso que o defeito só alcança **coluna única em modo `tcf`**: com 2+ colunas o meta
ganha `,`/`=` e a tag deixa de ser alfanumérica.

## A CORREÇÃO APROVADA (owner, 2026-08-16): opção B — escopo de discriminador

O encode **nunca** polariza `.8M`/`.8H` — está escrito em `encoder.py:489` (*"`.8M`/`.8H`/spec
ficam de fora deste weld"*) e medido aqui no Bloco 5: 4.000 wires de cada, zero com sufixo.
Logo o pré-passe rodando sobre um header `M`/`H` **só pode errar**. A opção B faz ele não
agir nesses discriminadores: **zero byte de mudança**, e ataca a causa em vez do sintoma.

A opção A (escapar o nome no emissor) foi descartada: mudaria bytes, exigiria re-pinar
baseline, e deixaria a polaridade lendo header que não é dela.

## GATE

`src/tcf` só é tocado com aprovação — este lab REPRODUZ, DELIMITA e VERIFICA.
"""
from __future__ import annotations

import json
import pathlib
import string
import sys
import warnings

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
assert (REPO / "src" / "tcf").is_dir(), f"REPO errado: {REPO}"
sys.path.insert(0, str(REPO / "src"))

from tcf import decode, encode, view                              # noqa: E402
from tcf.natures import SPEC_DATA_ISO                             # noqa: E402

INP, OUT = RAIZ / "inputs", RAIZ / "outputs"
JSON_KW = {"ensure_ascii": False, "indent": 1}
VALS = [f"v{i}" for i in range(26)]


def _esc(p, t):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(t, encoding="utf-8", newline="")


def _js(p, o):
    _esc(p, json.dumps(o, **JSON_KW))


def rt(dados, **kw):
    """(rt_ok, wire, volta) — a prova, e o wire pra inspeção."""
    w = encode(dados, **kw)
    try:
        v = decode(w)
    except Exception as e:
        return False, w, f"{type(e).__name__}: {e}"
    return v == dados, w, v


def grava_caso(nome, dados, wire, volta, extra=None):
    """entrada + wire + roundtrip + meta, com o diff textual como prova."""
    _js(INP / f"{nome}.entrada.json", dados)
    _esc(OUT / f"{nome}.tcf", wire)
    _js(OUT / f"{nome}.roundtrip.json", volta)
    igual = ((INP / f"{nome}.entrada.json").read_text(encoding="utf-8")
             == (OUT / f"{nome}.roundtrip.json").read_text(encoding="utf-8"))
    _js(OUT / f"{nome}.meta.json", {
        "wire_bytes": len(wire.encode("utf-8")), "linha1": wire.split("\n", 1)[0],
        "roundtrip_identico_a_entrada": igual, **(extra or {})})
    return igual


def detecta_estado() -> str:
    """Roda o repro canônico e deduz se `src/` já tem o fix."""
    d = {"obs.": list(VALS)}
    try:
        return "depois" if decode(encode(d)) == d else "antes"
    except Exception:
        return "antes"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    import shutil
    for p in (INP, OUT):
        if p.exists():
            shutil.rmtree(p)
        p.mkdir(parents=True)
    EST = detecta_estado()
    reg = {"estado_do_src": EST}
    falhas, regressoes = [], []
    print(f"ESTADO DETECTADO DO `src/`: **{EST.upper()} do fix**\n")

    # ── BLOCO 1 — o caso concreto, e a dependência de n ─────────────────────
    print("BLOCO 1 — o mesmo nome, variando só o NÚMERO DE VALORES")
    print(f"  {'nome':<8} {'n':>5}  {'header':<24} {'RT':<7} chave de volta")
    b1 = []
    for nome in ("obs.", "qtd.", "ab."):
        for n in (3, 5, 10, 26, 100):
            d = {nome: [f"v{i}" for i in range(n)]}
            ok, w, volta = rt(d)
            chave = list(volta)[0] if isinstance(volta, dict) and volta else "?"
            b1.append({"nome": nome, "n": n, "header": w.split("\n", 1)[0],
                       "rt": ok, "chave_volta": chave})
            print(f"  {nome:<8} {n:>5}  {w.split(chr(10),1)[0]:<24} "
                  f"{'ok' if ok else 'QUEBRA':<7} {chave!r}")
    reg["bloco1_dependencia_de_n"] = b1

    # ── BLOCO 2 — o sweep ASCII, .8M e .8H ──────────────────────────────────
    print("\nBLOCO 2 — sweep de toda a pontuação ASCII, .8M e .8H (n=26)")
    so_chave, chave_e_vals, ok_M = [], [], []
    falhas_H = ok_H = 0
    with warnings.catch_warnings(record=True) as capt:
        warnings.simplefilter("always")
        for p in string.punctuation:
            for nome in (f"ab{p}", f"ab{p}{p}"):
                d = {nome: list(VALS)}
                try:
                    volta = decode(encode(d))
                    if volta == d:
                        ok_M.append(nome)
                    elif list(volta.values())[0] == VALS:
                        so_chave.append(nome)
                    else:
                        chave_e_vals.append(nome)
                except Exception:
                    pass
                r = [{nome: v} for v in VALS]
                try:
                    if decode(encode(r)) == r:
                        ok_H += 1
                    else:
                        falhas_H += 1
                except Exception:
                    pass
    n_tot = len(string.punctuation) * 2
    n_falha_M = len(so_chave) + len(chave_e_vals)
    print(f"  .8M: {n_falha_M}/{n_tot} RT FALSO ({100*n_falha_M/n_tot:.1f}%)  "
          f"[só chave {len(so_chave)} · chave+valores {len(chave_e_vals)} · ok {len(ok_M)}]")
    print(f"  .8H: {falhas_H}/{n_tot} RT FALSO ({100*falhas_H/n_tot:.1f}%)")
    print(f"  WARNINGS em todo o sweep: {len(capt)}")
    reg["bloco2_sweep_ascii"] = {
        "n_casos": n_tot, "M_falso": n_falha_M, "M_so_chave": so_chave,
        "M_chave_e_valores": chave_e_vals, "M_ok": len(ok_M),
        "H_falso": falhas_H, "warnings": len(capt)}

    # ── BLOCO 3 — contra-prova: 2 colunas ───────────────────────────────────
    print("\nBLOCO 3 — CONTRA-PROVA: a MESMA coluna com uma SEGUNDA ao lado")
    ok2 = sum(1 for p in string.punctuation for nome in (f"ab{p}", f"ab{p}{p}")
              if rt({nome: list(VALS), "zz": list(VALS)})[0])
    print(f"  2 colunas: {ok2}/{n_tot} RT OK ({100*ok2/n_tot:.1f}%) — o defeito é da coluna ÚNICA")
    reg["bloco3_contraprova_2col"] = {"ok": ok2, "de": n_tot}

    # ── BLOCO 4 — VARIAÇÕES NOVAS (pedido do owner, 2026-08-16) ─────────────
    print("\nBLOCO 4 — VARIAÇÕES NOVAS: o que o sweep ASCII de 1 coluna NÃO cobria")
    print(f"  {'variação':<34} {'header':<30} {'RT':<7} nota")
    b4 = []

    def caso(rot, dados, nota="", **kw):
        ok, w, volta = rt(dados, **kw)
        if kw.get("drop_names") and isinstance(dados, dict):
            # com `drop_names` os nomes viram POSICIONAIS por DESIGN (ADR-0029) — comparar
            # chaves aqui seria erro do teste, não defeito. A prova é a dos VALORES,
            # na ordem. (Erro que eu cometi na 1ª rodada desta extensão.)
            ok = isinstance(volta, dict) and list(volta.values()) == list(dados.values())
            nota = (nota + "; RT por VALORES (nomes posicionais)").strip("; ")
        l1 = w.split("\n", 1)[0]
        b4.append({"variacao": rot, "header": l1, "rt": ok, "nota": nota,
                   "kw": {k: str(v) for k, v in kw.items()}})
        print(f"  {rot:<34} {l1[:30]:<30} {'ok' if ok else 'QUEBRA':<7} {nota}")
        return ok, w

    # 4a — UNICODE (o viés declarado da versão anterior: "só ASCII")
    for nome in ("obs°", "valor€", "medida±", "temp℃", "ção…"):
        caso(f"unicode {nome!r}", {nome: list(VALS)}, "não-ASCII no fim")
    # 4b — nome de 1 char, e nome SÓ pontuação
    caso("nome de 1 char '.'", {".": list(VALS)}, "nome inteiro é pontuação")
    caso("nome de 2 chars '..'", {"..": list(VALS)}, "")
    caso("nome 'a.'", {"a.": list(VALS)}, "tag alnum mínima")
    # 4c — pontuação no MEIO (controle: não deve quebrar)
    caso("pontuação no MEIO 'a.b'", {"a.b": list(VALS)}, "controle — não é sufixo")
    # 4d — 3+ colunas
    caso("3 colunas, última com '.'", {"a": list(VALS), "b": list(VALS), "c.": list(VALS)}, "")
    caso("3 colunas, PRIMEIRA com '.'", {"a.": list(VALS), "b": list(VALS), "c": list(VALS)}, "")
    # 4e — kwargs que mudam a forma do header
    caso("1 col, min_header=False", {"obs.": list(VALS)}, "size explícito", min_header=False)
    caso("1 col, drop_names=True", {"obs.": list(VALS)}, "nome SAI do header",
         drop_names=True)
    caso("2 col, drop_names=True", {"obs.": list(VALS), "z": list(VALS)}, "",
         drop_names=True)
    # 4f — a rota com SPEC (o separador não casa por causa do ':')
    datas = [f"2015-{m:02d}-01" for m in range(1, 13)] * 2
    caso("1 col + spec :dt", {"dt.": datas}, "meta tem ':'",
         nature_per_col={"dt.": SPEC_DATA_ISO})
    # 4g — .8H aninhado
    ok, w = caso(".8H aninhado, folha com '.'",
                 [{"o": {"obs.": v}} for v in VALS[:6]], "objeto dentro de objeto")
    # 4h — modos que mudam o marcador (o prefixo !@% quebra o .isalnum())
    caso("1 col modo raw '!'", {"obs.": ["q", "w", "e"]}, "n=3 → raw")
    caso("1 col modo dict '@'", {"obs.": ["alpha", "beta"] * 50}, "K=2 → dict")
    caso("1 col modo split '%'", {"obs.": [f"+55 11 9{i:04d}-{i:04d}" for i in range(30)]},
         "template → split")
    reg["bloco4_variacoes_novas"] = b4
    quebrou4 = [x for x in b4 if not x["rt"]]
    print(f"\n  quebraram: {len(quebrou4)}/{len(b4)}  {[x['variacao'] for x in quebrou4]}")

    # ── BLOCO 5 — o single-col LEGÍTIMO não pode regredir ───────────────────
    print("\nBLOCO 5 — CONTROLE: o single-col usa a polaridade DE VERDADE")
    print(f"  {'caso':<26} {'header':<16} {'sufixo':<8} {'RT':<7} nota")
    b5 = []
    from tcf.decoder import _separa_sufixo_polaridade as _sep
    CTRL = [
        ("flat com literais", [f"{i:02d}.{i:02d}-{i:03d}" for i in range(30)]),
        ("tipado int", [1000 + i * 7 for i in range(30)]),
        ("tipado float", [i + 0.5 for i in range(30)]),
        ("flat texto", [f"nome-{i}" for i in range(30)]),
        ("flat + spec", [f"2015-{m:02d}-01" for m in range(1, 13)]),
    ]
    for rot, v in CTRL:
        kw = {"nature": SPEC_DATA_ISO} if rot == "flat + spec" else {}
        ok, w, _ = rt(v, **kw)
        l1 = w.split("\n", 1)[0]
        _tag, _suf = _sep(l1[6:])
        pol = bool(_suf)
        b5.append({"caso": rot, "header": l1, "sufixo": _suf, "rt": ok, "polarizado": pol})
        print(f"  {rot:<26} {l1:<16} {_suf!r:<8} {'ok' if ok else 'QUEBRA':<7} "
              f"{'POLARIZADO (legítimo)' if pol else '—'}")
        if not ok:
            regressoes.append(f"single-col {rot}")
    n_pol = sum(1 for x in b5 if x["polarizado"])
    print(f"  → {n_pol} dos {len(b5)} controles usam polaridade de verdade; "
          f"nenhum pode regredir")
    reg["bloco5_single_col_controle"] = b5

    # ── BLOCO 6 — o encode NUNCA polariza .8M/.8H (a base da opção B) ───────
    print("\nBLOCO 6 — a PREMISSA da opção B: o encode nunca polariza .8M/.8H")
    import random as _r
    rng = _r.Random(3)
    tot = {"M": 0, "H": 0}
    com_sufixo = {"M": 0, "H": 0}
    for _ in range(2000):
        n = rng.randint(2, 8)
        cols = {}
        for i in range(rng.randint(1, 4)):
            est = rng.choice(["num", "cat", "txt", "pol"])
            if est == "num":
                v = [str(rng.randint(0, 999)) for _ in range(n)]
            elif est == "cat":
                v = [rng.choice(["a", "b"]) for _ in range(n)]
            elif est == "txt":
                v = [f"t{rng.randint(0, 50)}" for _ in range(n)]
            else:
                v = [f"{rng.randint(10,99)}.{rng.randint(10,99)}-{rng.randint(100,999)}"
                     for _ in range(n)]
            cols[f"c{i}"] = v
        for dado in (cols, [dict(zip(cols, t)) for t in zip(*cols.values())]):
            try:
                w = encode(dado)
            except Exception:
                continue
            d = w[6:7]
            if d not in tot:
                continue
            tot[d] += 1
            _t, _s = _sep(w.split("\n", 1)[0][6:])
            if _s:
                com_sufixo[d] += 1
    for d in ("M", "H"):
        print(f"  .8{d}: {tot[d]} wires -> {com_sufixo[d]} com sufixo separável "
              f"{'OK (premissa vale)' if com_sufixo[d] == 0 else '>>> PREMISSA FALSA <<<'}")
        if com_sufixo[d]:
            falhas.append(f"premissa da opcao B falsa em .8{d}")
    reg["bloco6_premissa"] = {"total": tot, "com_sufixo": com_sufixo}

    # ── evidência gravada dos casos concretos ───────────────────────────────
    for nome, dados in (("quebra-ponto", {"obs.": list(VALS)}),
                        ("quebra-ponto-duplo", {"obs..": list(VALS)}),
                        ("controle-2-colunas", {"obs.": list(VALS), "z": list(VALS)}),
                        ("controle-single-col-polarizado",
                         [f"{i:02d}.{i:02d}-{i:03d}" for i in range(30)])):
        ok, w, volta = rt(dados)
        grava_caso(f"{EST}-{nome}", dados, w, volta,
                   extra={"estado_do_src": EST, "rt_ok": ok})
    _js(INP / "sweep.fonte.json", {
        "gerador": "run.py — string.punctuation x {1,2} + variacoes do bloco 4",
        "valores": "26 sinteticos v0..v25 (o dado nao importa; o NOME e' a variavel)",
        "pin": "sem Z:, deterministico"})

    # ── veredito, dependente do estado ──────────────────────────────────────
    _js(RAIZ / f"resultado-{EST}.json", {**reg, "falhas": falhas,
                                         "regressoes": regressoes})
    print(f"\n{'='*74}")
    if EST == "antes":
        reproduziu = n_falha_M > 0 and falhas_H > 0 and len(capt) == 0
        print(f"ANTES DO FIX — defeito {'REPRODUZIDO' if reproduziu else 'NAO reproduzido'}: "
              f"RT falso em {n_falha_M}/{n_tot} (.8M) e {falhas_H}/{n_tot} (.8H), "
              f"{len(capt)} warnings")
        return 0 if (reproduziu and not falhas) else 1
    limpo = (n_falha_M == 0 and falhas_H == 0 and not quebrou4
             and not regressoes and not falhas)
    print(f"DEPOIS DO FIX — .8M {n_falha_M}/{n_tot} · .8H {falhas_H}/{n_tot} · "
          f"variações novas {len(quebrou4)}/{len(b4)} · regressões {len(regressoes)}")
    print(f"{'DEFEITO ELIMINADO, nada regrediu' if limpo else 'AINDA HA FALHA'}")
    for f_ in falhas + regressoes:
        print(f"  FALHA: {f_}")
    return 0 if limpo else 1


if __name__ == "__main__":
    raise SystemExit(main())
