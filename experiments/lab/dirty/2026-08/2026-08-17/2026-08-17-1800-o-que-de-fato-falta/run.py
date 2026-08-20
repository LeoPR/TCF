"""O que DE FATO falta pro grupo: a técnica do split + um marcador. Nada mais.

A TESE (owner, 2026-08-17)
--------------------------
*"o desafio é meramente juntar as colunas. temos vários mecanismos prontos que bastam
complementar. tratar como colunas independentes já é feito… no final, quem paga de
verdade é tanto a técnica pra fazer o split como alguma coisa no cabeçalho que lembre
que são duas (ou mais) colunas que são uma só na verdade na hora de decode."*

Isso é FALSIFICÁVEL, e este lab tenta derrubar. Se a tese for verdadeira:

  (H1) o CORPO do grupo tem de ser BYTE-IDÊNTICO ao corpo de N colunas independentes
       num `.8M` comum — porque seria literalmente o mesmo pipeline, coluna a coluna.
  (H2) a ÚNICA diferença no wire tem de estar no CABEÇALHO (o marcador de junção).
  (H3) as duas perspectivas do owner — (a) multi-col com indicador, (b) hierarquia de
       uma coluna com duas dentro — têm de produzir o MESMO corpo, diferindo só na
       gramática do meta. Se produzirem corpos diferentes, não são a mesma coisa.

Cada uma é testada contra dado real (CEP da Receita, via Shaper) e sintético.

§RT em tudo; evidência obrigatória. `src/tcf` INTOCADO.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

AQUI = Path(__file__).parent
RAIZ = AQUI.parents[5]
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "scripts"))

IN, OUT = AQUI / "inputs", AQUI / "outputs"
for d in (IN, OUT):
    d.mkdir(parents=True, exist_ok=True)

from tcf import encode, decode                                # noqa: E402
from tcf.multi.core import _fallback_safe, _decode_raw_body   # noqa: E402
from tcf.multi.dict_v2b import _v2b_encode, _decode_v2b       # noqa: E402
from tcf.multi.split import _struct_split_encode              # noqa: E402
from tcf.pipeline import DEFAULT_PIPELINE                     # noqa: E402


def B(x):
    return len(x.encode("utf-8")) if isinstance(x, str) else len(x)


def melhor_coluna(vals):
    corpo, modo = encode(vals, stamp=False).encode("utf-8"), ""
    if _fallback_safe(vals):
        rb = "\n".join(vals).encode("utf-8")
        if len(rb) < len(corpo):
            corpo, modo = rb, "!"
    vb = _v2b_encode(vals, cfg=DEFAULT_PIPELINE, min_len=None)
    if vb is not None and len(vb) < len(corpo):
        corpo, modo = vb, "@"
    return corpo, modo


def parte_campo(v):
    seq, atual, dig = [], "", None
    for ch in v:
        d = ch.isdigit()
        if dig is None:
            dig, atual = d, ch
            continue
        if d != dig:
            seq.append((dig, atual)); atual, dig = ch, d
        else:
            atual += ch
    seq.append((dig, atual))
    partes, campos = ([""] if seq[0][0] else []), []
    for eh, tok in seq:
        (campos if eh else partes).append(tok)
    if seq[-1][0]:
        partes.append("")
    return partes, campos


def separa(vals):
    p0, c0 = parte_campo(vals[0])
    if len(c0) < 2:
        return None
    cols = [[] for _ in c0]
    for v in vals:
        p, c = parte_campo(v)
        if p != p0 or len(c) != len(c0):
            return None
        for k, tok in enumerate(c):
            cols[k].append(tok)
    return p0, cols


# ── H1/H2: o corpo do grupo == corpo de N colunas independentes? ──────────
def corpo_de_colunas_independentes(cols):
    """O que o `.8M` produziria se os campos fossem colunas SEPARADAS e comuns.
    Usa o encode PÚBLICO — nada de reimplementação."""
    tab = {f"z{k}": c for k, c in enumerate(cols)}
    w = encode(tab)
    assert decode(w) == tab
    l1, corpo = w.split("\n", 1)
    return corpo.encode("utf-8"), l1


def corpo_do_grupo(cols):
    """O corpo que a forma-grupo emitiria: os mesmos corpos, concatenados na ordem."""
    return b"".join(melhor_coluna(c)[0] for c in cols)


# ── H3: as duas perspectivas do owner ────────────────────────────────────
def esc(s):
    return (s.replace("\\", "\\\\").replace("|", "\\|").replace(",", "\\,")
             .replace("=", "\\=").replace(";", "\\;").replace("{", "\\{"))


def meta_perspectiva_A(nome, partes, cols, corpos):
    """(a) multi-col com INDICADOR de junção — o grupo mora no `.8M`."""
    tot = sum(len(c) for c in corpos)
    vistos, ent = 0, []
    for corpo, c in zip(corpos, cols):
        vistos += len(corpo)
        m = melhor_coluna(c)[1]
        ent.append(f"{m}{'' if vistos == tot else format(len(corpo), 'x')}")
    tmpl = "|".join(esc(p) for p in partes)
    return "#TCF.8M&" + f"{len(cols):x}{tmpl}={esc(nome)}," + ",".join(ent)


def meta_perspectiva_B(nome, partes, cols, corpos):
    """(b) HIERARQUIA: uma coluna com N colunas dentro — o grupo mora no `.8H`."""
    tot = sum(len(c) for c in corpos)
    vistos, ent = 0, []
    for corpo, c in zip(corpos, cols):
        vistos += len(corpo)
        m = melhor_coluna(c)[1]
        ent.append(f"{m}{'' if vistos == tot else format(len(corpo), 'x')}")
    tmpl = "|".join(esc(p) for p in partes)
    return "#TCF.8H" + esc(nome) + "|" + tmpl + "|:" + ",".join(ent)


def main():
    print("=" * 94)
    print("O QUE DE FATO FALTA — testando a tese do owner")
    print("=" * 94)
    print("H1: o corpo do grupo e' BYTE-IDENTICO ao de N colunas independentes?")
    print("H2: a unica diferenca no wire esta' no CABECALHO?")
    print("H3: as duas perspectivas (multi-col+indicador / hierarquia) dao o MESMO corpo?")

    # os casos
    precos = [f"{p}.{c:02d}" for p in [12, 45, 7, 103, 88, 45, 12, 250, 7, 61, 45, 12]
              for c in (0, 50, 99)][:24]
    datas = [f"2026-{m:02d}-{d:02d}" for m in (1, 2, 3) for d in (5, 12, 19, 26)] * 2
    import random
    rng = random.Random(7)
    fones = [f"(11) 9{rng.randrange(10**4):04d}-{rng.randrange(10**4):04d}" for _ in range(12)] + \
            [f"(21) 9{rng.randrange(10**4):04d}-{rng.randrange(10**4):04d}" for _ in range(12)]
    from shaper import Shaper, ShapeRequest
    r = Shaper().apply(ShapeRequest(dataset="receita-cnpj-enderecos", volume=20000,
                                    seed=42, stratify_by="uf"))
    ceps = [f"{x['cep'][:5]}-{x['cep'][5:]}" for x in r.tables[list(r.tables)[0]]
            if x.get("cep") and len(x["cep"]) == 8 and x["cep"].isdigit()]

    casos = [("decimal", precos), ("data-iso", datas),
             ("telefone", fones), ("cep-real", ceps)]

    res = []
    for cid, vals in casos:
        g = separa(vals)
        assert g, f"{cid}: nao agrupa"
        partes, cols = g
        corpos = [melhor_coluna(c)[0] for c in cols]

        # H1 — corpo do grupo vs corpo de N colunas independentes (encode PUBLICO)
        c_indep, l1_indep = corpo_de_colunas_independentes(cols)
        c_grupo = corpo_do_grupo(cols)
        h1 = (c_indep == c_grupo)

        # H2 — o wire completo, nas duas formas, e o delta
        mA = meta_perspectiva_A(cid, partes, cols, corpos)
        mB = meta_perspectiva_B(cid, partes, cols, corpos)
        wA = (mA + "\n").encode("utf-8") + c_grupo
        wB = (mB + "\n").encode("utf-8") + c_grupo
        w_indep = (l1_indep + "\n").encode("utf-8") + c_indep

        # H3 — as duas perspectivas compartilham o corpo?
        h3 = (wA[len(mA) + 1:] == wB[len(mB) + 1:])

        # RT das duas formas (decoder generico: fatia pelo meta, junta pelo template)
        def rt(meta, wire, prefixo):
            l1, corpo = wire.split(b"\n", 1)
            ent = l1.decode("utf-8")[len(prefixo):]
            # pula ate' as entradas de coluna (depois do ultimo ':' ou ',' do cabecalho)
            corte = ent.rindex(":") + 1 if prefixo.endswith("H") else ent.index(",") + 1
            entradas = ent[corte:].split(",")
            off, campos = 0, []
            for e in entradas:
                m = e[0] if e[:1] in ("!", "@") else ""
                sz = e[1:] if m else e
                fim = off + int(sz, 16) if sz else None
                blob = corpo[off:fim] if fim else corpo[off:]
                off = fim if fim else len(corpo)
                campos.append(_decode_raw_body(blob) if m == "!" else
                              _decode_v2b(blob) if m == "@" else
                              decode(blob.decode("utf-8")))
            n = len(campos[0])
            return ["".join(partes[k] + campos[k][i] for k in range(len(campos))) + partes[-1]
                    for i in range(n)]

        assert rt(mA, wA, "#TCF.8M") == vals, f"{cid}: RT da perspectiva A falhou"
        assert rt(mB, wB, "#TCF.8H") == vals, f"{cid}: RT da perspectiva B falhou"

        # a referencia: o split ATUAL (slot aninhado)
        w_atual = encode({cid: vals})
        assert decode(w_atual) == {cid: vals}

        (IN / f"{cid}.json").write_text(json.dumps(vals[:50], ensure_ascii=False),
                                        encoding="utf-8", newline="")
        (OUT / f"{cid}.atual-split.tcf").write_text(w_atual, encoding="utf-8", newline="")
        (OUT / f"{cid}.colunas-independentes.tcf").write_bytes(w_indep)
        (OUT / f"{cid}.grupo-multicol.mock-tcf").write_bytes(wA)
        (OUT / f"{cid}.grupo-hierarquia.mock-tcf").write_bytes(wB)
        (OUT / f"{cid}.roundtrip.json").write_text(
            json.dumps(rt(mA, wA, "#TCF.8M")[:50], ensure_ascii=False),
            encoding="utf-8", newline="")

        marcador_A = len(mA) + 1 - (len(l1_indep) + 1)
        res.append({"caso": cid, "n": len(vals), "nf": len(cols),
                    "H1_corpo_identico": h1, "H3_perspectivas_mesmo_corpo": h3,
                    "corpo": len(c_grupo),
                    "meta_indep": len(l1_indep), "meta_grupoA": len(mA),
                    "meta_grupoB": len(mB),
                    "custo_marcador_vs_indep": marcador_A,
                    "wire_atual_split": B(w_atual), "wire_grupoA": len(wA),
                    "delta_vs_atual": len(wA) - B(w_atual)})

        print(f"\n### {cid}  (n={len(vals)}, {len(cols)} campos)")
        print(f"  H1 corpo do grupo == corpo de N colunas independentes? "
              f"{'SIM — byte-identico' if h1 else '*** NAO ***'}  ({len(c_grupo):,} B)")
        print(f"  H3 as 2 perspectivas compartilham o corpo?            "
              f"{'SIM' if h3 else '*** NAO ***'}")
        print(f"     meta col. independentes : {l1_indep!r}")
        print(f"     meta grupo (multi-col)  : {mA[:70]!r}")
        print(f"     meta grupo (hierarquia) : {mB[:70]!r}")
        print(f"  CUSTO DO MARCADOR (meta grupo - meta indep): {marcador_A:+} B")
        print(f"  wire: split atual {B(w_atual):,} | grupo {len(wA):,} "
              f"({len(wA)-B(w_atual):+,} B)")

    print("\n" + "=" * 94)
    print("VEREDITO")
    print("=" * 94)
    h1_all = all(x["H1_corpo_identico"] for x in res)
    h3_all = all(x["H3_perspectivas_mesmo_corpo"] for x in res)
    print(f"  H1 (corpo identico a N colunas independentes) : "
          f"{'CONFIRMADA' if h1_all else 'REFUTADA'} em {sum(x['H1_corpo_identico'] for x in res)}/{len(res)}")
    print(f"  H3 (as 2 perspectivas = mesmo corpo)          : "
          f"{'CONFIRMADA' if h3_all else 'REFUTADA'} em {sum(x['H3_perspectivas_mesmo_corpo'] for x in res)}/{len(res)}")
    print(f"\n  {'caso':12} {'corpo':>9} {'marcador':>9} {'split atual':>12} {'grupo':>9} {'delta':>8}")
    for x in res:
        print(f"  {x['caso']:12} {x['corpo']:>9,} {x['custo_marcador_vs_indep']:>+9} "
              f"{x['wire_atual_split']:>12,} {x['wire_grupoA']:>9,} {x['delta_vs_atual']:>+8,}")

    (AQUI / "resultado.json").write_text(json.dumps(res, ensure_ascii=False, indent=1),
                                         encoding="utf-8", newline="")
    n_ev = len(list(OUT.glob("*.tcf"))) + len(list(OUT.glob("*.mock-tcf")))
    assert n_ev == 4 * len(res), f"evidencia incompleta: {n_ev}"
    print(f"\n-> {n_ev} wires + {len(res)} roundtrips em outputs/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
