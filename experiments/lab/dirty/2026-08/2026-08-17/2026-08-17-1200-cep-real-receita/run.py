"""CEP REAL (Receita Federal, 200k) contra as estrategias — e o D5 que faltava.

O QUE MUDA EM RELACAO AO LAB 1000
---------------------------------
O lab `2026-08-17-1000` mediu CEP SINTETICO e declarou 4 lacunas. Tres caem aqui:
  - "todo dado e' sintetico"                 -> agora e' Receita Federal, 200k linhas
  - "a distribuicao real nao foi observada"  -> observada (as 10 regioes, 5,1%-15,7%)
  - "o D5 cross-coluna nao foi medido"       -> medido, e a coluna `uf` esta' ao lado

COLETA — pelo SHAPER, nao por LIMIT/OFFSET
------------------------------------------
200k linhas e' teste de MASSA, entao a amostra vem de `src/shaper/` com
`stratify_by="uf"` e seed fixa. Amostra honesta = representatividade +
dimensionamento + distribuicao; `LIMIT/OFFSET` nao entrega nenhuma das tres.
O mix sai DECLARADO ao lado dos numeros — foi a ausencia disso que derrubou a
conclusao do lab 0800.

AS ESTRATEGIAS
--------------
  D0 opaco        8 digitos, como a Receita entrega (sem mascara)
  D1 mascarado    NNNNN-NNN — a grafia que o `split` do TCF explora
  D2 pre+sufixo   5 + 3, duas colunas
  D3 hierarquico  reg/sub/set/sse/div/sufixo, seis colunas
  D4 delta+sort   ordem, com as duas contas (com e sem permutacao)
  D5 CROSS-COLUNA o 1o digito derivado da UF — MEDIDO, nao suposto

O harness exige que cada estrategia DECLARE a algebra (`remonta=` ou
`reordena=True`) — a guarda que o lab 1000 nao tinha, e por onde o D4 entrou sem
ninguem notar que ele permuta linha.

§RT em tudo. `src/tcf` INTOCADO. Nada baixado (o dataset ja' esta' em disco).
"""

from __future__ import annotations

import collections
import json
import math
import sys
from pathlib import Path

AQUI = Path(__file__).parent
RAIZ = AQUI.parents[5]
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "scripts"))

OUT = AQUI / "outputs"
IN = AQUI / "inputs"
for d in (OUT, IN):
    d.mkdir(parents=True, exist_ok=True)

from tcf import encode, decode                          # noqa: E402
from tcf.multi.core import _fallback_safe               # noqa: E402
from tcf.multi.dict_v2b import _v2b_encode              # noqa: E402
from tcf.multi.split import _struct_split_encode        # noqa: E402
from tcf.pipeline import DEFAULT_PIPELINE               # noqa: E402
from shaper import Shaper, ShapeRequest                 # noqa: E402

SEED = 42
N = 20000


def B(t):
    return len(t.encode("utf-8"))


def min_do_M(vals):
    """`_best_of` de multi/core.py:456 (closure) — mesma ordem, mesmo criterio."""
    bb, bm = encode(vals, stamp=False).encode("utf-8"), "tcf"
    if _fallback_safe(vals):
        rb = "\n".join(vals).encode("utf-8")
        if len(rb) < len(bb):
            bb, bm = rb, "raw"
    vb = _v2b_encode(vals, cfg=DEFAULT_PIPELINE, min_len=None)
    if vb is not None and len(vb) < len(bb):
        bb, bm = vb, "dict"
    sb = _struct_split_encode(vals, cfg=DEFAULT_PIPELINE, min_len=None)
    if sb is not None and len(sb) < len(bb):
        bb, bm = sb, "split"
    return len(bb), bm


def mede(rot, colunas, original, *, remonta=None, reordena=False):
    """Soma os bytes E PROVA que o original volta. A guarda e' o ponto.

    Herdada do lab 1000 apos o incidente do D4: quem chama tem de declarar a
    algebra. `remonta` reconstroi posicao a posicao; `reordena=True` permuta
    linha (contrato de CONJUNTO, nao de sequencia).
    """
    total, det = 0, []
    for nome, vals in colunas.items():
        b, modo = min_do_M(vals)
        total += b
        det.append({"col": nome, "bytes": b, "modo": modo, "distintos": len(set(vals))})
    if reordena:
        assert remonta is None
    else:
        assert remonta is not None, f"{rot}: declare `remonta` ou `reordena=True`"
        volta = remonta(colunas)
        assert volta == original, f"{rot}: a remontagem NAO devolve o original"
    return {"estrategia": rot, "bytes": total, "colunas": det,
            "preserva_ordem": not reordena}


def entropia(vals):
    n = len(vals)
    return -sum((v / n) * math.log2(v / n) for v in collections.Counter(vals).values())


def main():
    print("=" * 94)
    print("CEP REAL — Receita Federal, coleta pelo SHAPER (stratify_by=uf, seed=42)")
    print("=" * 94)

    r = Shaper().apply(ShapeRequest(dataset="receita-cnpj-enderecos", volume=N,
                                    seed=SEED, stratify_by="uf"))
    rows = r.tables[list(r.tables)[0]]
    pares = [(x["cep"], x["uf"]) for x in rows
             if x.get("cep") and len(x["cep"]) == 8 and x["cep"].isdigit()]
    ceps = [c for c, _u in pares]
    ufs = [u for _c, u in pares]
    n = len(ceps)

    mix = collections.Counter(ufs)
    print(f"\nMIX DECLARADO (o que o Shaper entregou): n={n:,} de {len(rows):,} pedidos")
    print("  " + " · ".join(f"{u}:{c / n * 100:.1f}%" for u, c in mix.most_common(8)))
    print(f"  UFs distintas: {len(mix)}   CEPs distintos: {len(set(ceps)):,} "
          f"({len(set(ceps)) / n * 100:.1f}%)")

    H = [entropia([c[i] for c in ceps]) for i in range(8)]
    print("\nENTROPIA POR POSICAO (bits, max 3.32):")
    print("    reg   sub   set   sse   div   sf1   sf2   sf3")
    print("  " + "  ".join(f"{h:.2f}" for h in H))
    print(f"  prefixo(5)={sum(H[:5]):.2f}  sufixo(3)={sum(H[5:]):.2f}  "
          f"total={sum(H):.2f} bits = {sum(H) / 8:.2f} B teoricos/valor")

    masc = [f"{c[:5]}-{c[5:]}" for c in ceps]
    pre = [c[:5] for c in ceps]
    suf = [c[5:] for c in ceps]

    ests = [
        mede("D0 opaco (8 digitos, como a Receita entrega)", {"cep": ceps}, ceps,
             remonta=lambda k: list(k["cep"])),
        mede("D1 mascarado NNNNN-NNN", {"cep": masc}, masc,
             remonta=lambda k: list(k["cep"])),
        mede("D2 prefixo+sufixo", {"pre": pre, "suf": suf}, ceps,
             remonta=lambda k: [a + b for a, b in zip(k["pre"], k["suf"])]),
        mede("D3 hierarquico (6 colunas)",
             {"reg": [c[0] for c in ceps], "sub": [c[1] for c in ceps],
              "set": [c[2] for c in ceps], "sse": [c[3] for c in ceps],
              "div": [c[4] for c in ceps], "suf": suf}, ceps,
             remonta=lambda k: [a + b + c + d + e + f for a, b, c, d, e, f in
                                zip(k["reg"], k["sub"], k["set"],
                                    k["sse"], k["div"], k["suf"])]),
    ]

    # D4 — ordem (permuta linha: contrato de CONJUNTO, nao de sequencia)
    ordenado = sorted(ceps)
    deltas = [ordenado[0]] + [str(int(ordenado[i]) - int(ordenado[i - 1]))
                              for i in range(1, n)]
    d4 = mede("D4a delta+sort (ordem NAO semantica)", {"delta": deltas}, ceps,
              reordena=True)
    ests.append(d4)
    perm = int(math.lgamma(n + 1) / math.log(2) / 8)
    ests.append({"estrategia": "D4b idem + permutacao (ordem semantica)",
                 "bytes": d4["bytes"] + perm, "preserva_ordem": True,
                 "colunas": [{"col": "delta", "bytes": d4["bytes"], "modo": "dict",
                              "distintos": len(set(deltas))},
                             {"col": "<permutacao log2(n!) PISO>", "bytes": perm,
                              "modo": "-", "distintos": 0}]})

    # ── D5: o 1o digito e' derivavel da UF? MEDIDO ──
    por_uf = collections.defaultdict(set)
    for c, u in pares:
        por_uf[u].add(c[0])
    det_ufs = {u for u, s in por_uf.items() if len(s) == 1}
    mapa = {u: next(iter(s)) for u, s in por_uf.items() if len(s) == 1}
    cobertas = sum(1 for u in ufs if u in det_ufs)
    print(f"\nD5 — CROSS-COLUNA: UFs com regiao UNICA: {len(det_ufs)}/{len(por_uf)}  "
          f"({cobertas / n * 100:.1f}% das linhas cobertas)")
    ambiguas = {u: sorted(s) for u, s in por_uf.items() if len(s) > 1}
    if ambiguas:
        print(f"  ambiguas: {ambiguas}")

    excecao = ["" if (u in mapa and mapa[u] == c[0]) else c[0] for c, u in pares]

    # D5 ingenuo: tira o 1o digito e entrega 7 digitos CRUS.
    resto = [c[1:] for c in ceps]
    ests.append(mede("D5 resto(7) CRU + excecao",
                     {"resto": resto, "exc": excecao}, ceps,
                     remonta=lambda k: [(e if e else mapa[u]) + rr
                                        for rr, e, u in zip(k["resto"], k["exc"], ufs)]))

    # D5' — a MESMA derivacao, PRESERVANDO A MASCARA.
    # A diferenca entre os dois nao e' a derivacao: e' que o D5 ingenuo destroi a
    # estrutura posicional que o `split` explorava (medido: o modo cai de `split`
    # pra `raw`). Manter o hifen mantem o split vivo — e ai' a derivacao paga.
    resto_m = [f"{c[1:5]}-{c[5:]}" for c in ceps]
    ests.append(mede("D5' resto MASCARADO NNNN-NNN + excecao",
                     {"resto": resto_m, "exc": excecao}, ceps,
                     remonta=lambda k: [(e if e else mapa[u]) + rr.replace("-", "")
                                        for rr, e, u in zip(k["resto"], k["exc"], ufs)]))

    base = next(e for e in ests if e["estrategia"].startswith("D1"))["bytes"]
    print(f"\n{'estrategia':44} {'bytes':>9} {'B/val':>7} {'vs D1':>8} {'ordem':>6}  modos")
    print("-" * 94)
    for e in ests:
        modos = ",".join(f"{c['col']}:{c['modo']}" for c in e["colunas"])
        ordem = "sim" if e["preserva_ordem"] else "NAO"
        print(f"{e['estrategia']:44} {e['bytes']:>9,} {e['bytes'] / n:>7.2f} "
              f"{(e['bytes'] / base - 1) * 100:>7.1f}% {ordem:>6}  {modos[:24]}")

    (AQUI / "resultado.json").write_text(json.dumps({
        "fonte": "Receita Federal, dado aberto (perfil enderecos), 200k linhas",
        "coleta": f"Shaper: ShapeRequest(volume={N}, seed={SEED}, stratify_by='uf')",
        "mix_declarado": dict(mix.most_common()),
        "n_valido": n, "distintos": len(set(ceps)),
        "entropia_por_digito": [round(h, 3) for h in H],
        "d5_ufs_deterministicas": sorted(det_ufs),
        "d5_ufs_ambiguas": ambiguas,
        "estrategias": ests,
    }, ensure_ascii=False, indent=1), encoding="utf-8", newline="")
    (IN / "amostra.json").write_text(
        json.dumps([{"cep": c, "uf": u} for c, u in pares[:50]], ensure_ascii=False),
        encoding="utf-8", newline="")
    print(f"\n-> {AQUI / 'resultado.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
