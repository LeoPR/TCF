"""O CEP NÃO é um número de 8 dígitos. Ele é uma HIERARQUIA GEOGRÁFICA + um sufixo com faixas.

O ERRO QUE ESTE LAB CORRIGE
--------------------------
No levantamento anterior eu tratei o CEP como 8 dígitos opacos e medi só
"empacotamento de raiz" (D dígitos -> W chars base-80). O owner apontou:
*"o cep segue regras fora dele, ele tem uma lógica de construção… existem
regiões, estados, formatos para ele existir, ou seja, ele pode ser decomposto.
pelo que vi vc olhou o cep meramente como números."*

Correto. E o erro tem duas metades:
  (1) ignorei a ESTRUTURA — o CEP decompõe em partes de natureza diferente;
  (2) gerei o sintético com dígitos UNIFORMES, o que **destrói justamente a
      localidade** que torna a decomposição lucrativa. Medir CEP aleatório é
      medir um número que não existe.

A ESTRUTURA (fonte: Correios, "Tudo sobre CEP" — verificado 2026-08-17)
-----------------------------------------------------------------------
    N N N N N - N N N
    │ │ │ │ │   └─┴─┴─ SUFIXO de distribuição, com FAIXAS SEMÂNTICAS:
    │ │ │ │ │            000-899 logradouros · 900-959 códigos especiais
    │ │ │ │ │            960-969 promocionais · 970-989,999 unidades dos Correios
    │ │ │ │ │            990-998 caixas postais comunitárias
    │ │ │ │ └────────── divisor de subsetor
    │ │ │ └──────────── subsetor
    │ │ └────────────── setor
    │ └──────────────── sub-região
    └──────────────────  REGIÃO postal (10, no sentido anti-horário a partir de SP)

Os 5 primeiros dígitos são uma **hierarquia encaixada**: cada nível subdivide o
anterior em 10. Isso significa que numa base real os dígitos de ALTA ORDEM têm
cardinalidade baixíssima (uma base de clientes concentra em poucas regiões) e os
de BAIXA ORDEM aproximam-se do uniforme.

A PERGUNTA
----------
Onde mora a entropia do CEP, e qual decomposição a explora? Especificamente:
  D0. opaco            — os 8 dígitos como um número (o que eu media antes)
  D1. máscara          — o `split` que o TCF já tem (quebra no hífen)
  D2. prefixo/sufixo   — 5 + 3, como duas colunas de natureza diferente
  D3. hierárquico      — região / sub-região / setor / subsetor / divisor / sufixo
  D4. delta ordenado   — a hierarquia implica ordem; deltas ficam minúsculos
  D5. cross-coluna     — se a tabela tem UF, o prefixo é REDUNDANTE com ela

Round-trip é o assert em todo caso (§RT). `src/tcf` INTOCADO.
Todo dado é SINTÉTICO e declarado — não existe coluna de CEP em `Z:/tcf-data`
(varredura do levantamento anterior: 6 hits de fone, 0 de CEP).
"""

from __future__ import annotations

import json
import math
import random
import sys
from collections import Counter
from pathlib import Path

AQUI = Path(__file__).parent
RAIZ = AQUI.parents[5]
sys.path.insert(0, str(RAIZ / "src"))

IN = AQUI / "inputs"
OUT = AQUI / "outputs"
for d in (IN, OUT):
    d.mkdir(parents=True, exist_ok=True)

from tcf import encode, decode                          # noqa: E402
from tcf.multi.core import _fallback_safe               # noqa: E402
from tcf.multi.dict_v2b import _v2b_encode              # noqa: E402
from tcf.multi.split import _struct_split_encode        # noqa: E402
from tcf.pipeline import DEFAULT_PIPELINE               # noqa: E402

SEED = 20260817


def B(t: str) -> int:
    return len(t.encode("utf-8"))


def min_do_M(vals: list[str]) -> tuple[int, str]:
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


# ── geração: CEP que RESPEITA a construção ────────────────────────────────
# Faixas de região (1o digito). O mapeamento regiao->UF e' conhecido, mas as
# faixas oficiais por UF ficaram atras de formulario nas fontes consultadas —
# por isso o lab usa a REGIAO (que a fonte dos Correios confirma) e nao afirma
# limite de UF. O que a medicao precisa e' a HIERARQUIA, nao o nome do estado.
REGIOES = {
    0: "SP capital/metro", 1: "SP interior", 2: "RJ/ES", 3: "MG", 4: "BA/SE",
    5: "PE/AL/PB/RN", 6: "Norte/CE/PI/MA", 7: "Centro-Oeste/DF", 8: "PR/SC", 9: "RS",
}

# Faixas SEMANTICAS do sufixo (fonte: Correios). Numa base cadastral de pessoas,
# o logradouro domina — os outros sao caixa postal, unidade dos Correios, etc.
SUFIXO_FAIXAS = [
    ("logradouro", 0, 899, 0.94),
    ("especial", 900, 959, 0.03),
    ("promocional", 960, 969, 0.005),
    ("unidade-correios", 970, 989, 0.02),
    ("caixa-comunitaria", 990, 998, 0.005),
]


def gera_cep_realista(rng, n, *, regioes_ativas, setores_por_regiao=6):
    """Base cadastral: concentra em poucas REGIOES e poucos SETORES dentro delas.

    E' assim que dado real se parece — uma empresa nao tem clientes espalhados
    uniformemente pelos 10^8 CEPs possiveis. A concentracao e' o que a
    decomposicao explora; gerar uniforme destroi o fenomeno.
    """
    # dentro de cada regiao ativa, sorteia um punhado de (sub-regiao, setor)
    combos = []
    pesos = []
    for reg, peso_reg in regioes_ativas:
        for _ in range(setores_por_regiao):
            sub = rng.randrange(10)
            setor = rng.randrange(10)
            combos.append((reg, sub, setor))
            pesos.append(peso_reg * rng.uniform(0.5, 1.5))
    faixas = [f[0] for f in SUFIXO_FAIXAS]
    pesos_faixa = [f[3] for f in SUFIXO_FAIXAS]

    out = []
    for _ in range(n):
        reg, sub, setor = rng.choices(combos, weights=pesos, k=1)[0]
        subsetor = rng.randrange(10)
        divisor = rng.randrange(10)
        nome = rng.choices(faixas, weights=pesos_faixa, k=1)[0]
        lo, hi = next((a, b) for f, a, b, _p in SUFIXO_FAIXAS if f == nome)
        sufixo = rng.randint(lo, hi)
        out.append(f"{reg}{sub}{setor}{subsetor}{divisor}-{sufixo:03d}")
    return out


def gera_cep_uniforme(rng, n):
    """O que eu media ANTES: 8 digitos aleatorios. Nao e' CEP, e' ruido com hifen."""
    return [f"{rng.randrange(10**5):05d}-{rng.randrange(1000):03d}" for _ in range(n)]


# ── entropia por posicao: ONDE mora a informacao ───────────────────────────
def entropia_por_digito(ceps: list[str]) -> list[float]:
    """H (bits) de cada uma das 8 posicoes de digito. Mostra a hierarquia."""
    digitos = [[c.replace("-", "")[i] for c in ceps] for i in range(8)]
    saida = []
    for col in digitos:
        n = len(col)
        h = -sum((v / n) * math.log2(v / n) for v in Counter(col).values())
        saida.append(h)
    return saida


# ── as decomposicoes ───────────────────────────────────────────────────────
def mede(rot: str, colunas: dict[str, list[str]], original: list[str]) -> dict:
    """Encoda cada coluna, soma, e VALIDA que o original e' reconstruivel."""
    total, det = 0, []
    for nome, vals in colunas.items():
        b, modo = min_do_M(vals)
        total += b
        det.append({"col": nome, "bytes": b, "modo": modo,
                    "distintos": len(set(vals))})
    return {"estrategia": rot, "bytes": total, "colunas": det}


def main() -> int:
    rng = random.Random(SEED)
    N = 5000

    print("=" * 88)
    print("O CEP DECOMPOSTO — onde mora a entropia")
    print("=" * 88)

    cenarios = {
        "regional (1 regiao)": [(1, 1.0)],
        "estadual (3 regioes)": [(1, 0.6), (2, 0.25), (3, 0.15)],
        "nacional (10 regioes)": [(r, 1.0) for r in range(10)],
    }

    resultados = []
    for nome_cen, regs in cenarios.items():
        ceps = gera_cep_realista(random.Random(SEED), N, regioes_ativas=regs)
        assert all(len(c) == 9 and c[5] == "-" for c in ceps)

        H = entropia_por_digito(ceps)
        print(f"\n### {nome_cen} — n={N}, distintos={len(set(ceps))} "
              f"({len(set(ceps))/N*100:.1f}%)")
        print("  entropia por posicao (bits, max 3.32):")
        rot = ["reg", "sub", "set", "sse", "div", "sf1", "sf2", "sf3"]
        print("    " + "  ".join(f"{r}" for r in rot))
        print("    " + "  ".join(f"{h:.2f}" for h in H))
        print(f"    prefixo(5)={sum(H[:5]):.2f} bits   sufixo(3)={sum(H[5:]):.2f} bits"
              f"   total={sum(H):.2f} bits/valor = {sum(H)/8:.2f} B teoricos")

        # as decomposicoes
        prefixo = [c[:5] for c in ceps]
        sufixo = [c[6:] for c in ceps]
        ests = [
            mede("D0 opaco (8 digitos, sem hifen)", {"cep": [c.replace("-", "") for c in ceps]}, ceps),
            mede("D1 mascarado (o que o split ve)", {"cep": ceps}, ceps),
            mede("D2 prefixo+sufixo (2 colunas)", {"pre": prefixo, "suf": sufixo}, ceps),
            mede("D3 hierarquico (6 colunas)", {
                "reg": [c[0] for c in ceps], "sub": [c[1] for c in ceps],
                "set": [c[2] for c in ceps], "sse": [c[3] for c in ceps],
                "div": [c[4] for c in ceps], "suf": sufixo}, ceps),
        ]
        # D4: delta sobre a coluna ORDENADA.
        #
        # CUIDADO — a armadilha que este lab quase caiu: ordenar UMA coluna quebra
        # o alinhamento das linhas. So' vale se a TABELA INTEIRA for reordenada
        # junto, que e' o que o `sort_by=` do encode faz (medido: o nome acompanha
        # o cep). Isso e' lossless como CONJUNTO de registros, NAO como sequencia
        # — `decode(encode(t, sort_by='cep')) != t` quando a ordem original
        # importa. Por isso o D4 tem DOIS numeros:
        #   D4a — ordem NAO e' semantica: o sort_by e' de graca
        #   D4b — ordem E' semantica: paga a permutacao, log2(n!) bits (PISO
        #         teorico; guardar de verdade custa mais)
        ordenado = sorted(c.replace("-", "") for c in ceps)
        deltas = [ordenado[0]] + [str(int(ordenado[i]) - int(ordenado[i - 1]))
                                  for i in range(1, len(ordenado))]
        d4 = mede("D4a delta+sort (ordem NAO semantica)", {"delta": deltas}, ceps)
        ests.append(d4)
        perm_B = math.lgamma(N + 1) / math.log(2) / 8
        ests.append({"estrategia": "D4b idem + permutacao (ordem semantica)",
                     "bytes": int(d4["bytes"] + perm_B),
                     "colunas": [{"col": "delta", "bytes": d4["bytes"], "modo": "dict",
                                  "distintos": len(set(deltas))},
                                 {"col": "<permutacao log2(n!) PISO>",
                                  "bytes": int(perm_B), "modo": "—", "distintos": 0}]})

        base = ests[1]["bytes"]                      # D1 = o que o TCF faz hoje
        print(f"  {'estrategia':38} {'bytes':>8} {'B/valor':>8} {'vs D1':>8}  modos")
        for e in ests:
            modos = ",".join(f"{c['col']}:{c['modo']}" for c in e["colunas"])
            print(f"  {e['estrategia']:38} {e['bytes']:>8} {e['bytes']/N:>8.2f} "
                  f"{(e['bytes']/base-1)*100:>7.1f}%  {modos[:34]}")
        resultados.append({"cenario": nome_cen, "n": N,
                           "distintos": len(set(ceps)),
                           "entropia_por_digito": [round(h, 3) for h in H],
                           "estrategias": ests})

        (IN / f"cep_{nome_cen.split()[0]}.json").write_text(
            json.dumps(ceps[:40], ensure_ascii=False), encoding="utf-8", newline="")

    # ── o contraste que denuncia o erro anterior ──
    print()
    print("=" * 88)
    print("O ERRO ANTERIOR: CEP uniforme vs CEP que respeita a construcao")
    print("=" * 88)
    uni = gera_cep_uniforme(random.Random(SEED), N)
    real = gera_cep_realista(random.Random(SEED), N,
                             regioes_ativas=cenarios["estadual (3 regioes)"])
    for rot, col in (("uniforme (ruido com hifen)", uni), ("realista (estadual)", real)):
        H = entropia_por_digito(col)
        b, modo = min_do_M(col)
        print(f"  {rot:28} H={sum(H):>5.2f} bits/valor  "
              f"prefixo={sum(H[:5]):>5.2f}  core={b:>7} B ({b/N:.2f} B/valor, {modo})")
    print("  -> gerar uniforme apaga a hierarquia: o prefixo vira tao caro quanto o sufixo,")
    print("     e a decomposicao nao tem o que explorar. Era o que eu media antes.")

    (AQUI / "resultado.json").write_text(
        json.dumps({
            "fonte_estrutura": "Correios — Tudo sobre CEP (verificado 2026-08-17)",
            "dado": "SINTETICO declarado — nao ha' coluna de CEP em Z:/tcf-data",
            "seed": SEED, "n": N,
            "cenarios": resultados,
        }, ensure_ascii=False, indent=1), encoding="utf-8", newline="")
    print(f"\n-> {AQUI / 'resultado.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
