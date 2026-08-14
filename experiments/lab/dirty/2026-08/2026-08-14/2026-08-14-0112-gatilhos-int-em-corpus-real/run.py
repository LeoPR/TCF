"""Os gatilhos do int em CORPUS REAL — com que frequência aparecem? `python run.py`

## A lacuna que este lab fecha

Os três labs de inteiro (22h58, 23h26, 00h32) são **sintéticos controlados**, por escolha:
isolar o mecanismo. Todos declararam a mesma pendência: *"falta medir a FREQUÊNCIA dos
gatilhos em corpus real — o corpus dita o default"*. É a regra que valeu para data.

Aqui os gatilhos são classificados e medidos em **39 colunas numéricas reais**, descobertas
automaticamente nos hubs de `Z:/tcf-data` (o `extrai.py` varre os bancos e pega toda coluna
de tipo numérico com dados suficientes — escolher a dedo seria montar o corpus para a
resposta).

## Os 4 mecanismos em disputa (desenho de 2026-08-14)

    PAD       zero-pad p/ largura fixa    gatilho: progressão + largura VARIÁVEL
    B94       base-94 densa               gatilho: SEM progressão + largura FIXA
    min_len   (núcleo, não é spec)        gatilho: fragmentação do OBAT
    bN        (já funciona)               gatilho: baixa cardinalidade

O `OFFPAD` saiu de cena em 2026-08-14 (ver `notas/2026-08/…-0210-offpad-detalhado…`).

Cada coluna é medida **nas duas ordens** (natural e ordenada): a ordem é a maior alavanca
conhecida do projeto, e um gatilho pode existir só numa delas.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import sys
from collections import Counter

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
assert (REPO / "src" / "tcf").is_dir(), f"REPO errado: {REPO}"
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(RAIZ.parent.parent / "2026-08-13" / "2026-08-13-2258-int-spec-faz-sentido"))

from specs import IntB94, IntPad  # noqa: E402  (mesma fonte dos alvos, não copiada)
from tcf import decode, encode  # noqa: E402

FONTES = RAIZ / "inputs" / "fontes"
INT, OUT = RAIZ / "intermediates", RAIZ / "outputs"
JSON_KW = {"ensure_ascii": False, "indent": 1}
GRADE_ML = (4, 8, 12, 16, 20)


def _esc(p, t):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(t, encoding="utf-8", newline="")


def _js(p, o):
    _esc(p, json.dumps(o, **JSON_KW))


def B(t):
    return len(t.encode("utf-8"))


def classifica(vals) -> dict:
    """Os gatilhos, medidos na coluna — o que um auto-detector veria ANTES de encodar."""
    v = [x for x in vals if x is not None]
    larguras = {len(str(abs(x))) for x in v}
    k = len(set(v))
    n = len(v)
    difs = [b - a for a, b in zip(v, v[1:])]
    passo_unico = len(set(difs)) == 1 if difs else False
    monotona = all(d >= 0 for d in difs) or all(d <= 0 for d in difs) if difs else False
    return {
        "n": len(vals), "k": k, "nulos": len(vals) - n,
        "larguras": sorted(larguras), "largura_varia": len(larguras) > 1,
        "cardinalidade": round(k / n, 3) if n else 0,
        "passo_constante": passo_unico,
        "monotona": monotona,
        "tem_negativo": any(x < 0 for x in v),
        # os GATILHOS do desenho
        "gat_PAD": monotona and len(larguras) > 1,
        "gat_B94": (not monotona) and len(larguras) == 1 and k / n > 0.5,
        "gat_bN": k <= 64,
        "gat_min_len": monotona and len(larguras) == 1 and min(larguras) >= 6,
    }


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for d in (INT, OUT):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
    man = json.loads((FONTES / "_manifesto.json").read_text(encoding="utf-8"))
    if not man:
        print("sem corpus — rode extrai.py com Z: montado")
        return 0

    linhas, falhas = [], []
    for meta in man:
        rot = meta["rotulo"]
        for ordem in ("natural", "ordenado"):
            p = FONTES / f"{rot}.{ordem}.json"
            if not p.exists():
                continue
            vals = json.loads(p.read_text(encoding="utf-8"))
            g = classifica(vals)
            strs = [None if x is None else str(x) for x in vals]

            base = encode(vals)                       # rota TIPADA (o caminho natural)
            if decode(base) != vals:
                falhas.append(f"{rot}.{ordem}: RT do core quebrou")
            cand = {"core": B(base)}

            # min_len (nucleo, sem spec).
            # ACHADO DESTE LAB (2026-08-14): `min_len=` tambem e' RECUSADO na rota tipada —
            # `ValueError: kwargs ['min_len'] so' valem no flat de STRING`. Mesma classe do
            # `nature=`. Ou seja: a rota tipada e' fechada para os DOIS mecanismos que o int
            # precisa. Medimos na rota string e somamos o +1 do disc `n`, que e' o que um
            # `min_len` tipado pagaria — igual ao tratamento de PAD/B94 abaixo.
            mml = min((B(encode(strs, min_len=m)) + 1, m) for m in GRADE_ML)
            cand["min_len"] = mml[0]

            # PAD e B94 — hoje so' expressaveis na rota STRING; medidos la',
            # e o custo do disc tipado (+1 B) somado, que e' o que um spec tipado pagaria
            larg = max(len(str(abs(x))) for x in vals if x is not None)
            for nome, alvo in (("PAD", IntPad(largura=larg)),
                               ("B94", IntB94(digitos=larg) if larg <= 12 else None)):
                if alvo is None:
                    cand[nome] = None
                    continue
                try:
                    w = encode(strs, nature=alvo)
                    if decode(w, nature=alvo) != strs:
                        falhas.append(f"{rot}.{ordem}/{nome}: RT quebrou")
                        cand[nome] = None
                        continue
                    cand[nome] = B(w) + 1             # +1 = o disc `n` que a rota tipada leva
                except Exception as e:
                    falhas.append(f"{rot}.{ordem}/{nome}: {type(e).__name__}")
                    cand[nome] = None

            venc = min((v, k) for k, v in cand.items() if v is not None)
            linhas.append({"coluna": rot, "ordem": ordem, **g, "bytes": cand,
                           "vencedor": venc[1], "ganho_vs_core": round(cand["core"] / venc[0], 3),
                           "ml_melhor": mml[1], "header": base.split("\n")[0][:16]})
            _esc(OUT / f"{rot}.{ordem}.tcf", base)
            _js(OUT / f"{rot}.{ordem}.roundtrip.json", decode(base))
    _js(INT / "por-coluna.json", linhas)

    # ── frequência dos gatilhos ──
    nat = [x for x in linhas if x["ordem"] == "natural"]
    print(f"{len(man)} colunas x 2 ordens = {len(linhas)} medições\n")
    print("FREQUÊNCIA DOS GATILHOS (ordem natural, o que se vê no dado como está)")
    for gat in ("gat_PAD", "gat_B94", "gat_bN", "gat_min_len"):
        q = sum(1 for x in nat if x[gat])
        print(f"  {gat:14s} {q:3d}/{len(nat)}  ({q / len(nat) * 100:4.1f}%)")

    print("\nQUEM VENCE, na prática (as duas ordens)")
    for ordem in ("natural", "ordenado"):
        c = Counter(x["vencedor"] for x in linhas if x["ordem"] == ordem)
        tot = sum(c.values())
        print(f"  {ordem:9s} " + "  ".join(f"{k}={v} ({v / tot * 100:.0f}%)"
                                           for k, v in c.most_common()))

    print("\nONDE ALGUÉM BATE O CORE (ganho > 1.00)")
    ganha = sorted([x for x in linhas if x["ganho_vs_core"] > 1.0],
                   key=lambda x: -x["ganho_vs_core"])
    print(f"  {len(ganha)}/{len(linhas)} medições")
    for x in ganha[:12]:
        print(f"    {x['coluna'][:44]:44s} {x['ordem']:9s} "
              f"{x['bytes']['core']:7d} -> {x['vencedor']:8s} "
              f"{x['ganho_vs_core']:5.2f}x")

    _js(RAIZ / "resultado.json", {"linhas": linhas, "falhas": falhas})
    print(f"\n{len(falhas)} falha(s)")
    for f in falhas[:8]:
        print(f"  FALHA: {f}")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
