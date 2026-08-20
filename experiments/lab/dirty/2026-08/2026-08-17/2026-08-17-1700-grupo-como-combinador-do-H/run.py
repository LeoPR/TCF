"""O GRUPO como COMBINADOR do `.8H` — emprestando a lógica da hierarquia ao split.

A OBSERVAÇÃO (owner, 2026-08-17)
--------------------------------
*"o group fica muito mais limpo e de certa forma dá pra emprestar a lógica da
hierarquia, pensando que ele só vai tratar um pouco diferente na hora de combinar."*

E ela bate com a gramática. O `.8H` JÁ É "N colunas físicas + uma regra de
recombinar" — o meta declara o combinador em cada campo:

    a{b            `{`     combina ANINHANDO       -> {"a": {"b": v}}
    a#:6[          `#:[`   combina por CONTAGEM    -> {"a": [v, v]}
    a?:5           `?:`    combina com MÁSCARA     -> presente/ausente/null
    a:6n           `:tag`  folha escalar TIPADA

O grupo seria **mais um combinador da mesma família**:

    a|.|           `|…|`   combina CONCATENANDO    -> parte0 + c0 + parte1 + c1 + …

O QUE ISSO DESTRAVA (o fio que estava aberto)
---------------------------------------------
O lab `2026-08-17-0400` mediu: o `.8H` perde +23,0% pro `.8M`, e **100% do gap** é o
CANDIDATO ÚNICO — a folha do `.8H` chama `_encode_col` e não tem raw/dict/split.
Minha proposta na época foi "abrir um slot de modo no meta da folha".

A ideia do owner ataca por outra rota: se o grupo é um COMBINADOR, o `.8H` ganha o
efeito do split **estruturalmente** — sem slot de modo, sem `%`, sem sub-wire. A folha
estruturada vira N colunas irmãs, e cada uma passa pelo pipeline normal.

Medido aqui:  `.8H` hoje  ×  `.8H` + combinador de grupo  ×  `.8M` com split (a referência)

MOCK (dirty; `src/tcf` INTOCADO). §RT em tudo; evidência obrigatória em `outputs/`.
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
from tcf.pipeline import DEFAULT_PIPELINE                     # noqa: E402


def B(x):
    return len(x.encode("utf-8")) if isinstance(x, str) else len(x)


# ── o pipeline de UMA coluna: os candidatos que já existem ────────────────
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


def decoda_coluna(blob, modo):
    """NENHUM decoder novo — os três que o `.8M` já usa."""
    if modo == "!":
        return _decode_raw_body(blob)
    if modo == "@":
        return _decode_v2b(blob)
    return decode(blob.decode("utf-8"))


# ── template (o mesmo do split): partes não-dígito / campos de dígito ─────
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
    for eh_dig, tok in seq:
        (campos if eh_dig else partes).append(tok)
    if seq[-1][0]:
        partes.append("")
    return partes, campos


def grupo_de(vals):
    """(partes, colunas) se TODOS compartilham o template e há >=2 campos; senão None."""
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
    if all(len(set(c)) == 1 for c in cols):      # nada varia: não é grupo útil
        return None
    return p0, cols


# ── shredding hierárquico (o que o `.8H` faz), + o combinador de GRUPO ────
def shred(ds):
    """dataset -> [(caminho, valores)] em ordem DFS. Só a classe que este mock cobre:
    objetos aninhados de folhas string. Basta para a pergunta."""
    cols, ordem = {}, []

    def anda(obj, pref):
        for k, v in obj.items():
            p = pref + (k,)
            if isinstance(v, dict):
                anda(v, p)
            else:
                if p not in cols:
                    cols[p] = []; ordem.append(p)
                cols[p].append(v)
    for reg in ds:
        anda(reg, ())
    return [(p, cols[p]) for p in ordem]


def esc(s):
    return (s.replace("\\", "\\\\").replace("|", "\\|").replace(",", "\\,")
             .replace("{", "\\{").replace("=", "\\=").replace(":", "\\:"))


def unesc(s):
    out, i = [], 0
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s):
            out.append(s[i + 1]); i += 2
        else:
            out.append(s[i]); i += 1
    return "".join(out)


def _split_unesc(s, sep):
    out, atual, i = [], "", 0
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s):
            atual += s[i:i + 2]; i += 2; continue
        if s[i] == sep:
            out.append(atual); atual = ""; i += 1; continue
        atual += s[i]; i += 1
    out.append(atual)
    return out


def encode_H_grupo(ds, *, usar_grupo=True):
    """Mock do `.8H` com o combinador de GRUPO. Meta:

        <caminho>            folha simples        -> [modo]<size>
        <caminho>|<t0>|<t1>| folha em GRUPO      -> nf entradas [modo]<size>, irmãs

    O caminho usa `{` como o `.8H` real. As entradas de coluna são as MESMAS do `.8M`.
    """
    entradas, corpos = [], []
    for caminho, vals in shred(ds):
        nome = "{".join(esc(k) for k in caminho)
        g = grupo_de(vals) if usar_grupo else None
        if g is None:
            corpo, modo = melhor_coluna(vals)
            entradas.append((nome, [(modo, corpo)], None))
            corpos.append(corpo)
        else:
            partes, cols = g
            subs = []
            for c in cols:
                corpo, modo = melhor_coluna(c)
                subs.append((modo, corpo)); corpos.append(corpo)
            entradas.append((nome, subs, partes))

    # monta o meta; a ÚLTIMA coluna do wire omite o size (regra do .8M/.8H)
    total = sum(len(c) for _n, s, _p in entradas for _m, c in s)
    toks, vistos = [], 0
    for nome, subs, partes in entradas:
        cab = nome if partes is None else nome + "|" + "|".join(esc(p) for p in partes) + "|"
        pedacos = []
        for modo, corpo in subs:
            vistos += len(corpo)
            ultima = vistos == total
            pedacos.append(f"{modo}{'' if ultima else format(len(corpo), 'x')}")
        toks.append(cab + ":" + ",".join(pedacos))
    return ("#TCF.8H" + ";".join(toks) + "\n").encode("utf-8") + b"".join(corpos)


def decode_H_grupo(wire):
    l1, corpo = wire.split(b"\n", 1)
    meta = l1.decode("utf-8")[len("#TCF.8H"):]
    campos, off = [], 0
    for tok in _split_unesc(meta, ";"):
        cab, _, entr = tok.rpartition(":")
        partes = None
        if "|" in cab and not cab.endswith("\\|"):
            nome_raw, _, tail = cab.partition("|")
            partes = [unesc(p) for p in _split_unesc(tail, "|")[:-1]]
            cab = nome_raw
        caminho = [unesc(k) for k in _split_unesc(cab, "{")]
        cols = []
        for e in _split_unesc(entr, ","):
            modo = e[0] if e[:1] in ("!", "@") else ""
            sz = e[1:] if modo else e
            fim = off + int(sz, 16) if sz else None
            blob = corpo[off:fim] if fim else corpo[off:]
            off = fim if fim else len(corpo)
            cols.append(decoda_coluna(blob, modo))
        campos.append((caminho, cols, partes))

    n = len(campos[0][1][0])
    saida = []
    for r in range(n):
        reg = {}
        for caminho, cols, partes in campos:
            if partes is None:
                v = cols[0][r]
            else:                                  # o COMBINADOR de grupo
                v = "".join(partes[k] + cols[k][r] for k in range(len(cols))) + partes[-1]
            d = reg
            for k in caminho[:-1]:
                d = d.setdefault(k, {})
            d[caminho[-1]] = v
        saida.append(reg)
    return saida


# ── os casos ──────────────────────────────────────────────────────────────
def casos():
    precos = [f"{p}.{c:02d}" for p in [12, 45, 7, 103, 88, 45, 12, 250, 7, 61, 45, 12]
              for c in (0, 50, 99)][:24]
    datas = [f"2026-{m:02d}-{d:02d}" for m in (1, 2, 3) for d in (5, 12, 19, 26)] * 2
    yield ("h1-folha-decimal", "objeto aninhado, folha = decimal",
           [{"item": {"sku": f"SKU{i % 6}", "preco": precos[i]}} for i in range(24)])
    yield ("h2-folha-data", "objeto aninhado, folha = data ISO",
           [{"ped": {"id": str(i), "criado": datas[i]}} for i in range(24)])
    yield ("h3-duas-folhas", "DUAS folhas estruturadas no mesmo registro",
           [{"v": {"preco": precos[i], "quando": datas[i]}} for i in range(24)])
    from shaper import Shaper, ShapeRequest
    r = Shaper().apply(ShapeRequest(dataset="receita-cnpj-enderecos", volume=4000,
                                    seed=42, stratify_by="uf"))
    rows = [x for x in r.tables[list(r.tables)[0]]
            if x.get("cep") and len(x["cep"]) == 8 and x["cep"].isdigit()]
    yield ("h4-cep-real", "CEP real (Receita) como folha de objeto aninhado",
           [{"end": {"uf": x["uf"], "cep": f"{x['cep'][:5]}-{x['cep'][5:]}"}} for x in rows])


def main():
    print("=" * 94)
    print("O GRUPO COMO COMBINADOR DO .8H")
    print("=" * 94)
    print("`.8H` hoje  ×  `.8H` + combinador de grupo  ×  `.8M` com split (referência)")

    res = []
    for cid, desc, ds in casos():
        wH = encode(ds); assert decode(wH) == ds, f"{cid}: RT do .8H real falhou"
        wSem = encode_H_grupo(ds, usar_grupo=False)
        assert decode_H_grupo(wSem) == ds, f"{cid}: RT do mock-sem-grupo falhou"
        wCom = encode_H_grupo(ds, usar_grupo=True)
        assert decode_H_grupo(wCom) == ds, f"{cid}: RT do mock-COM-grupo falhou"

        # referência: a folha estruturada isolada, pelo .8M (que tem split)
        folhas = [(p, v) for p, v in shred(ds) if grupo_de(v)]
        ref = sum(B(encode({"_": v})) for _p, v in folhas)

        (IN / f"{cid}.json").write_text(json.dumps(ds[:40], ensure_ascii=False),
                                        encoding="utf-8", newline="")
        (OUT / f"{cid}.8H-real.tcf").write_text(wH, encoding="utf-8", newline="")
        (OUT / f"{cid}.mock-sem-grupo.tcf").write_bytes(wSem)
        (OUT / f"{cid}.mock-com-grupo.tcf").write_bytes(wCom)
        (OUT / f"{cid}.roundtrip.json").write_text(
            json.dumps(decode_H_grupo(wCom)[:40], ensure_ascii=False),
            encoding="utf-8", newline="")

        bH, bs, bc = B(wH), len(wSem), len(wCom)
        res.append({"caso": cid, "desc": desc, "n": len(ds),
                    "H_real": bH, "mock_sem": bs, "mock_com": bc,
                    "ganho_pct": (bc / bs - 1) * 100,
                    "vs_H_real": (bc / bH - 1) * 100,
                    "folhas_agrupadas": len(folhas),
                    "meta_H": wH.splitlines()[0],
                    "meta_grupo": wCom.split(b"\n")[0].decode("utf-8")})
        print(f"\n### {cid} — {desc}  (n={len(ds)})")
        print(f"  .8H real           : {bH:>8,} B   meta: {wH.splitlines()[0][:64]!r}")
        print(f"  mock SEM grupo     : {bs:>8,} B")
        print(f"  mock COM grupo     : {bc:>8,} B   {(bc/bs-1)*100:+.1f}% vs sem  "
              f"({(bc/bH-1)*100:+.1f}% vs .8H real)")
        print(f"  meta com grupo     : {wCom.split(chr(10).encode())[0].decode()[:74]!r}")
        print(f"  folhas agrupadas   : {len(folhas)}")

    print("\n" + "=" * 94)
    print(f"{'caso':20} {'.8H real':>10} {'sem grupo':>10} {'com grupo':>10} {'ganho':>8} {'vs .8H':>8}")
    print("-" * 94)
    for r in res:
        print(f"{r['caso']:20} {r['H_real']:>10,} {r['mock_sem']:>10,} {r['mock_com']:>10,} "
              f"{r['ganho_pct']:>7.1f}% {r['vs_H_real']:>7.1f}%")

    (AQUI / "resultado.json").write_text(json.dumps(res, ensure_ascii=False, indent=1),
                                         encoding="utf-8", newline="")
    n_ev = len(list(OUT.glob("*.tcf")))
    assert n_ev == 3 * len(res), f"evidencia incompleta: {n_ev}"
    print(f"\n-> {n_ev} wires + {len(res)} roundtrips em outputs/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
