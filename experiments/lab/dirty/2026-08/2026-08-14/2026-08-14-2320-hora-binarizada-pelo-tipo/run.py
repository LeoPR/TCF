# -*- coding: utf-8 -*-
"""HORA binarizada pelo ESPAÇO DO TIPO — e onde ela vence o `bN` de domínio.

    python run.py

## A pergunta (uma só)

> Owner (2026-08-14): *"a hora usa bem os algoritmos que já tem, talvez se ele tiver uma forma
> binarizada própria para o espaço de números dele, já que vai de 0-24 e 0-60 por exemplo."*

Então: **binarizar pelo espaço do TIPO (que as duas pontas conhecem) vence binarizar pelo
domínio OBSERVADO (que tem de viajar)?**

## A distinção que organiza tudo

| | largura de bits | o domínio viaja? |
|---|---|---|
| **`bN` de domínio** (o núcleo já faz) | `w = ceil(log2 k)`, **k = distintos observados** | **sim** — os k valores vão no wire |
| **espaço do tipo** (a ideia) | `w` fixo pela **definição** do tipo | **não** — as duas pontas sabem |

O precedente é o **bool denso**: `b1` usa 1 bit e `b2` usa 2, e o domínio (`false/true`,
`null/false/true`) **não viaja** porque é fixo por tipo.

## A aritmética que faz a pergunta valer a pena

Para hora, as duas formas do espaço do tipo custam **o mesmo**:

- **por campo**: `0..23` → 5 bits, `0..59` → 6, `0..59` → 6 ⇒ **17 bits**
- **por ordinal**: `0..86399` ⇒ `ceil(log2 86400)` = **17 bits**

Não é coincidência: `2^5 · 2^6 · 2^6 = 131072 = 2^17`. As duas desperdiçam o mesmo
(`131072/86400` ≈ 1,52×, ou 0,6 bit).

**Então a escolha entre campo e ordinal não é de tamanho — é de que estrutura sobra.** O
ordinal é monotônico dentro do dia (alimenta seq-RLE); os campos separam o que cicla do que não
cicla. Este lab mede as duas.

## O ponto de virada

`bN` paga o domínio uma vez e gasta menos bits por linha; o espaço do tipo não paga domínio e
gasta 17 bits sempre. Logo **`bN` vence quando há poucos distintos e muitas linhas**, e o
espaço do tipo vence quando os distintos são muitos. O lab acha o cruzamento.

## GATE

Protótipo em lab, fora de `src/tcf`. Nada aqui é proposta de weld.
"""
from __future__ import annotations

import base64
import json
import math
import pathlib
import shutil
import sqlite3
import sys

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
assert (REPO / "src" / "tcf").is_dir(), f"REPO errado: {REPO}"
sys.path.insert(0, str(REPO / "src"))

from tcf import decode, encode          # noqa: E402
from tcf.bitpack import pack_w, unpack_w  # noqa: E402  (o mesmo do bool denso / bN)

INP, INT, OUT = RAIZ / "inputs", RAIZ / "intermediates", RAIZ / "outputs"
JSON_KW = {"ensure_ascii": False, "indent": 1}


def _esc(p, t):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(t, encoding="utf-8", newline="")


def _js(p, o):
    _esc(p, json.dumps(o, **JSON_KW))


def B(t):
    return len(t.encode("utf-8"))


# ── as formas ────────────────────────────────────────────────────────────────
def hhmmss_para_campos(h):
    return int(h[0:2]), int(h[3:5]), int(h[6:8])


def forma_texto(horas):
    """O baseline: o que o núcleo faz hoje."""
    return encode(horas)


def forma_ordinal_decimal(horas):
    """Segundos desde meia-noite, em DECIMAL — o desenho irmão do `data-iso`."""
    return encode([str(h * 3600 + m * 60 + s) for h, m, s in map(hhmmss_para_campos, horas)])


def _b64(bits_por_valor, valores, marca):
    """Empacota com o MESMO `pack_w` do bool denso e do bN, e serializa como o core faz."""
    raw = pack_w(valores, bits_por_valor)
    b64 = base64.b64encode(raw).decode("ascii")
    # header ilustrativo: magic + marca + n em hex (a mesma forma de `#TCF.8b1<n>`)
    return f"#TCF.8{marca}{len(valores):x}\n={b64}", raw, b64


def forma_ordinal_17bits(horas):
    """O espaço do tipo, forma ORDINAL: 0..86399 em 17 bits. O domínio não viaja."""
    ords = [h * 3600 + m * 60 + s for h, m, s in map(hhmmss_para_campos, horas)]
    wire, raw, _ = _b64(17, ords, "t17_")
    volta = [f"{o//3600:02d}:{(o%3600)//60:02d}:{o%60:02d}"
             for o in unpack_w(raw, 17, len(ords))]
    return wire, volta


def forma_campos_5_6_6(horas):
    """O espaço do tipo, forma POR CAMPO: 5+6+6 bits. Mesmo total, outra estrutura."""
    campos = list(map(hhmmss_para_campos, horas))
    juntos = [(h << 12) | (m << 6) | s for h, m, s in campos]   # 5+6+6 = 17 bits
    wire, raw, _ = _b64(17, juntos, "tc_")
    volta = []
    for x in unpack_w(raw, 17, len(juntos)):
        volta.append(f"{(x >> 12) & 0x1F:02d}:{(x >> 6) & 0x3F:02d}:{x & 0x3F:02d}")
    return wire, volta


def forma_campos_separados(horas):
    """3 streams independentes: hora(5) · minuto(6) · segundo(6). Cada um com seu w."""
    campos = list(map(hhmmss_para_campos, horas))
    partes, raws = [], []
    for idx, w in ((0, 5), (1, 6), (2, 6)):
        vals = [c[idx] for c in campos]
        raw = pack_w(vals, w)
        raws.append((raw, w, len(vals)))
        partes.append(base64.b64encode(raw).decode("ascii"))
    wire = f"#TCF.8tsep{len(campos):x}\n" + "\n".join("=" + p for p in partes)
    cols = [unpack_w(r, w, n) for r, w, n in raws]
    volta = [f"{a:02d}:{b:02d}:{c:02d}" for a, b, c in zip(*cols)]
    return wire, volta


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for d in (INP, INT, OUT):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
    falhas, reg = [], []

    def _hh(seg):
        return f"{seg//3600:02d}:{(seg%3600)//60:02d}:{seg%60:02d}"

    # ── os regimes, variando o que importa: n e k (distintos) ───────────────
    CASOS = [
        ("k096-n0672-batimento15min-7dias",
         [_hh((i * 900) % 86400) for i in range(672)],
         "96 distintos em 672 linhas — o regime cíclico do lab anterior"),
        ("k096-n096-batimento15min-1dia",
         [_hh(i * 900) for i in range(96)],
         "96 distintos em 96 linhas — sem repetição nenhuma"),
        ("k1440-n1440-cada-minuto",
         [_hh(i * 60) for i in range(1440)],
         "1440 distintos em 1440 linhas — resolução de minuto, 1 dia inteiro"),
        ("k2000-n2000-cada-segundo",
         [_hh(i) for i in range(2000)],
         "2000 distintos, todos diferentes — o pior caso para o bN"),
        ("k0024-n2000-so-hora-cheia",
         [_hh((i % 24) * 3600) for i in range(2000)],
         "24 distintos em 2000 linhas — o melhor caso para o bN"),
    ]
    try:
        con = sqlite3.connect("file:Z:/tcf-data/interim/online-retail.db?mode=ro", uri=True)
        v = [str(r[0]).split(" ")[1] for r in con.execute(
            "SELECT InvoiceDate FROM online_retail WHERE InvoiceDate LIKE '% %'")]
        con.close()
        passo = max(1, len(v) // 2000)
        v = v[::passo][:2000]
        CASOS.append((f"real-retail-k{len(set(v))}-n{len(v)}", v,
                      "a única hora do corpus (segundo constante `00`)"))
    except Exception:
        print("(sem Z: — o caso real será pulado)")

    FORMAS = [("texto", None), ("ordinal-decimal", None),
              ("tipo-ordinal-17b", forma_ordinal_17bits),
              ("tipo-campos-5+6+6", forma_campos_5_6_6),
              ("tipo-campos-separados", forma_campos_separados)]

    print(f"{'caso':>34} {'k':>5} {'n':>5} | {'texto':>7} {'ord-dec':>8} "
          f"{'t-ord17':>8} {'t-5+6+6':>8} {'t-3cols':>8} | vencedor")
    for nome, horas, ideia in CASOS:
        _js(INP / f"{nome}.entrada.json", horas)
        _js(INP / f"{nome}.fonte.json",
            {"gerador": "run.py::CASOS", "ideia": ideia, "n": len(horas),
             "distintos": len(set(horas)),
             "pin": "sintético viesado por construção" if not nome.startswith("real")
                    else "corpus Z: — não versionado"})
        linha = {"caso": nome, "ideia": ideia, "n": len(horas), "k": len(set(horas)),
                 "CONSTANTE_na_comparacao": "as MESMAS horas; só muda COMO se binariza"}
        for rot, fn in FORMAS:
            if rot == "texto":
                w, volta = forma_texto(horas), None
                volta = decode(w)
            elif rot == "ordinal-decimal":
                w = forma_ordinal_decimal(horas)
                segs = decode(w)
                volta = [_hh(int(x)) for x in segs]
            else:
                w, volta = fn(horas)
            ok = volta == horas
            if not ok:
                falhas.append(f"{nome}/{rot}: RT não fechou")
            linha[rot] = B(w)
            linha[f"{rot}_rt"] = ok
            _esc(OUT / f"{nome}.{rot}.tcf", w)
            _js(OUT / f"{nome}.{rot}.roundtrip.json", volta)
        cands = {r: linha[r] for r, _ in FORMAS}
        venc = min(cands, key=cands.get)
        linha["vencedor"] = venc
        linha["ganho_vs_texto_pct"] = round(100 * (1 - cands[venc] / linha["texto"]), 1)
        _js(OUT / f"{nome}.meta.json", {"input": f"inputs/{nome}.entrada.json", **linha})
        reg.append(linha)
        print(f"{nome:>34} {linha['k']:>5} {linha['n']:>5} | {linha['texto']:>7} "
              f"{linha['ordinal-decimal']:>8} {linha['tipo-ordinal-17b']:>8} "
              f"{linha['tipo-campos-5+6+6']:>8} {linha['tipo-campos-separados']:>8} | "
              f"{venc} ({linha['ganho_vs_texto_pct']:+.1f}%)")

    # ── O PONTO DE VIRADA ────────────────────────────────────────────────────
    #
    # DEFEITO DA 1ª RODADA: eu gerava `_hh((i % k) * (86400 // k))`, que varia `k` **e** a
    # regularidade ao mesmo tempo — o resultado saiu NÃO-MONOTÔNICO (k=1440 vencia enquanto
    # k=288 perdia), porque alguns `k` produziam progressão aritmética limpa e outros não.
    # Confundir as duas variáveis é o mesmo erro do artefato de alinhamento de 2026-07-23.
    #
    # Aqui `k` é isolado: as horas são sorteadas (LCG determinístico) de um POOL de k valores,
    # então a ordem é irregular em todo `k`, e só a cardinalidade muda.
    print("\nO PONTO DE VIRADA — n=2000, ordem IRREGULAR (k isolado)")
    print(f"  {'k':>6} {'núcleo':>8} {'tipo-17b':>9} {'quem vence':>15}  {'w_bN':>5}  header")
    virada = []
    x = 12345
    for k in (2, 8, 24, 60, 96, 144, 288, 500, 1000, 1440, 2000):
        pool = [_hh(int(i * 86400 / k)) for i in range(k)]
        horas = []
        for _ in range(2000):
            x = (x * 1103515245 + 12345) % 2147483648
            horas.append(pool[x % k])
        kreal = len(set(horas))
        w_txt = encode(horas)                     # o núcleo decide sozinho (bN se valer)
        w_tipo, volta = forma_ordinal_17bits(horas)
        if volta != horas:
            falhas.append(f"virada k={k}: RT do tipo-17b não fechou")
        vence = "núcleo" if B(w_txt) <= B(w_tipo) else "espaço-do-tipo"
        virada.append({"k_pedido": k, "k_real": kreal, "n": 2000,
                       "bytes_nucleo": B(w_txt), "bytes_tipo_17b": B(w_tipo),
                       "vencedor": vence,
                       "w_bN_teorico": math.ceil(math.log2(max(kreal, 2))),
                       "header_nucleo": w_txt.split("\n")[0],
                       "CONSTANTE_na_comparacao": "n=2000 e ordem IRREGULAR (LCG) em todo k; "
                                                  "só a CARDINALIDADE varia"})
        print(f"  {kreal:>6} {B(w_txt):>8} {B(w_tipo):>9} {vence:>15}  "
              f"{math.ceil(math.log2(max(kreal,2))):>5}  {w_txt.split(chr(10))[0]}")

    _js(INT / "formas.json", reg)
    _js(INT / "ponto-de-virada.json", virada)
    _js(RAIZ / "resultado.json", {"formas": reg, "virada": virada, "falhas": falhas})
    _esc(OUT / "INDEX.md", "\n".join(
        ["# INDEX — hora binarizada pelo espaço do tipo", "",
         "| caso | k | n | texto | ord-dec | tipo-17b | tipo-5+6+6 | 3 cols | vencedor |",
         "|---|---|---|---|---|---|---|---|---|"] +
        [f"| [`{x['caso']}`](./{x['caso']}.texto.tcf) | {x['k']} | {x['n']} | {x['texto']} | "
         f"{x['ordinal-decimal']} | {x['tipo-ordinal-17b']} | {x['tipo-campos-5+6+6']} | "
         f"{x['tipo-campos-separados']} | **{x['vencedor']}** |" for x in reg] +
        ["", "Ponto de virada em `../intermediates/ponto-de-virada.json`.", ""]))

    print(f"\n{len(falhas)} falha(s)")
    for f in falhas[:12]:
        print(f"  FALHA: {f}")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
