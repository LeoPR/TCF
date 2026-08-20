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


def _slug(s):
    return "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in s)[:44]


def grava_evidencia(estrategia, nome_col, vals, bytes_reportados, modo):
    """Materializa o wire REAL da coluna e prova que ele decoda. Devolve o caminho.

    POR QUE ISTO EXISTE (revisao 2026-08-17, apontada pelo owner):
    os labs 1000 e 1200 rodaram com `outputs/` VAZIO. O `min_do_M` devolve so'
    um COMPRIMENTO — nada era materializado, entao nao havia o que auditar.
    Reportar byte sem deixar o wire em disco e' o mesmo que nao ter medido:
    ninguem consegue conferir.

    O que se grava e' um `.8M` de UMA coluna com os MESMOS valores — wire de
    verdade, que o `decode` publico abre. E confere-se que o CORPO dentro dele
    bate com o numero reportado, senao o arquivo em disco estaria provando
    outra coisa que nao o numero da tabela.
    """
    d = OUT / _slug(estrategia)
    d.mkdir(parents=True, exist_ok=True)
    tab = {nome_col: vals}
    wire = encode(tab)
    volta = decode(wire)
    assert volta == tab, f"{estrategia}/{nome_col}: o wire gravado NAO decoda de volta"

    corpo = wire.split("\n", 1)[1].encode("utf-8")
    p_tcf = d / f"{_slug(nome_col)}.tcf"
    p_tcf.write_text(wire, encoding="utf-8", newline="")
    (d / f"{_slug(nome_col)}.roundtrip.json").write_text(
        json.dumps(volta[nome_col][:200], ensure_ascii=False),
        encoding="utf-8", newline="")
    (d / f"{_slug(nome_col)}.meta.json").write_text(json.dumps({
        "estrategia": estrategia, "coluna": nome_col, "n": len(vals),
        "distintos": len(set(vals)),
        "bytes_reportados_na_tabela": bytes_reportados, "modo_vencedor": modo,
        "bytes_do_corpo_no_wire": len(corpo),
        "bytes_do_wire_inteiro": B(wire),
        "roundtrip": True,
        "nota": "o .tcf e' um #TCF.8M de 1 coluna, decodavel pela API publica; "
                "o corpo dele e' o candidato que o min() elegeu",
    }, ensure_ascii=False, indent=1), encoding="utf-8", newline="")
    assert p_tcf.exists() and p_tcf.stat().st_size > 0, "evidencia vazia"
    return p_tcf


def mede(rot, colunas, original, *, remonta=None, reordena=False,
         remonta_conjunto=None):
    """Soma os bytes E PROVA que o original volta. A guarda e' o ponto.

    Herdada do lab 1000 apos o incidente do D4 — e CORRIGIDA na revisao
    2026-08-17: a primeira copia deste harness DEGRADOU a guarda do ramo
    `reordena=True` (o lab 1000 validava o CONJUNTO via `_remonta_conjunto`;
    a copia trocou por um `assert remonta is None`, que nao valida NADA).
    Guardas nao sobrevivem a copia — por isso o ramo agora EXIGE
    `remonta_conjunto` e compara os multiconjuntos.

    `remonta` reconstroi posicao a posicao; `reordena=True` permuta linha
    (contrato de CONJUNTO, nao de sequencia).
    """
    total, det = 0, []
    for nome, vals in colunas.items():
        b, modo = min_do_M(vals)
        total += b
        # EVIDENCIA OBRIGATORIA: nenhum byte entra na tabela sem o wire em disco.
        p = grava_evidencia(rot, nome, vals, b, modo)
        det.append({"col": nome, "bytes": b, "modo": modo,
                    "distintos": len(set(vals)),
                    "evidencia": str(p.relative_to(AQUI)).replace("\\", "/")})
    if reordena:
        assert remonta is None, f"{rot}: reordena=True e remonta= sao exclusivos"
        assert remonta_conjunto is not None, (
            f"{rot}: reordena=True exige `remonta_conjunto` — sem ele o ramo nao valida nada")
        assert sorted(remonta_conjunto(colunas)) == sorted(original), (
            f"{rot}: nem como CONJUNTO o original volta")
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
    def _desfaz_delta(k):
        acum, saida = int(k["delta"][0]), [k["delta"][0].zfill(8)]
        for x in k["delta"][1:]:
            acum += int(x)
            saida.append(f"{acum:08d}")
        return saida

    d4 = mede("D4a delta+sort (ordem NAO semantica)", {"delta": deltas}, ceps,
              reordena=True, remonta_conjunto=_desfaz_delta)
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

    # D6 — CONTROLE DE ATRIBUICAO (revisao 2026-08-17). O D5' mistura DOIS
    # mecanismos: (a) separar o 1o digito preservando a mascara do resto, e
    # (b) derivar esse digito da UF. Sem este controle, o -20,8% seria
    # atribuido inteiro a' "redundancia entre colunas" — a mesma classe de
    # meia-atribuicao que derrubou a conclusao do lab 0800 (mix vs mecanismo).
    # O D6 faz SO' o (a): o digito vira coluna propria, sem UF nenhuma.
    # D5' - D6 = o que a derivacao pela UF REALMENTE vale.
    resto_m = [f"{c[1:5]}-{c[5:]}" for c in ceps]
    ests.append(mede("D6 digito como COLUNA + resto mascarado (sem UF)",
                     {"dig": [c[0] for c in ceps], "resto": resto_m}, ceps,
                     remonta=lambda k: [d + rr.replace("-", "")
                                        for d, rr in zip(k["dig"], k["resto"])]))

    # D5' — a MESMA derivacao, PRESERVANDO A MASCARA.
    # A diferenca entre D5 e D5' nao e' a derivacao: e' que o D5 ingenuo destroi
    # a estrutura posicional que o `split` explorava (medido: o modo cai de
    # `split` pra `raw`). Manter o hifen mantem o split vivo.
    # CUSTO NAO CONTADO NAS COLUNAS: o mapa UF->digito (27 pares) teria de
    # viajar ou ser tabela fixa do formato; ~100 B, declarado abaixo.
    ests.append(mede("D5' resto MASCARADO NNNN-NNN + excecao (UF)",
                     {"resto": resto_m, "exc": excecao}, ceps,
                     remonta=lambda k: [(e if e else mapa[u]) + rr.replace("-", "")
                                        for rr, e, u in zip(k["resto"], k["exc"], ufs)]))
    custo_mapa = B("\n".join(f"{u}{d}" for u, d in sorted(mapa.items())))
    print(f"\nATRIBUICAO do D5' (mapa UF->digito custaria ~{custo_mapa} B, nao contado):")

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
    (IN / "cep_uf_completo.json").write_text(
        json.dumps([{"cep": c, "uf": u} for c, u in pares], ensure_ascii=False),
        encoding="utf-8", newline="")

    # ── PORTAO FINAL: evidencia COMPLETA e sem ORFAO ──
    # A 1a versao so' checava `>=`, e por isso deixou passar uma pasta `teste-ok/`
    # que um teste meu do proprio portao escreveu aqui dentro (achada pelo owner).
    # Evidencia orfa e' pior que evidencia faltando: parece medicao e nao esta' em
    # relatorio nenhum. Agora o portao exige correspondencia EXATA com o que a
    # tabela reporta.
    esperados = {e["colunas"][0].get("evidencia") and
                 (AQUI / c["evidencia"]).resolve()
                 for e in ests for c in e["colunas"] if "evidencia" in c}
    esperados = {p for p in esperados if p}
    achados = {p.resolve() for p in OUT.rglob("*.tcf")}
    orfaos = achados - esperados
    faltando = esperados - achados
    assert not faltando, f"EVIDENCIA FALTANDO: {sorted(str(p.name) for p in faltando)}"
    assert not orfaos, (
        "EVIDENCIA ORFA (arquivo em outputs/ que nenhuma linha da tabela reporta): "
        f"{sorted(str(p.relative_to(OUT)) for p in orfaos)}")
    n_tcf, n_rt = len(achados), len(list(OUT.rglob("*.roundtrip.json")))
    print(f"\n-> {AQUI / 'resultado.json'}")
    print(f"-> evidencia: {n_tcf} wires .tcf + {n_rt} roundtrips em {OUT.name}/ "
          f"({sum(f.stat().st_size for f in OUT.rglob('*'))/1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
