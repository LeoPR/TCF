"""Um spec de INTEIRO faz sentido? `python run.py`

Pergunta do owner (2026-08-13): *"vamos ver o número, e mais especificamente inteiros de
início, ver se um spec faz sentido, provavelmente sim… fazendo o ritual clássico, com os
sintéticos controlados, e até vendo que o percurso de revisão desde a bN, bool, date e tudo
mais pode generalizar otimizações que já podem ser usadas em int."*

## O que este lab responde

1. Onde o núcleo JÁ resolve inteiro sozinho (e o spec deve recusar).
2. Onde ele deixa folga, e QUAL das três ideias herdadas a cobre.
3. Se as três ideias juntas fecham, ou se sobra regime descoberto.

Os 3 alvos são generalizações do que o projeto já soldou (ver `specs.py`):
PAD (do IP) · B94 (do CPF) · OFFPAD (do ordinal de data).

## O ritual

Cada caso: input em disco, o wire de cada rota, o vencedor, o round-trip como
contra-prova diffável, e o PIN do que se espera. `src/tcf` NÃO é tocado — os alvos entram
pela API pública (`encode(vals, nature=alvo)`), então o FLOOR real decide.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import random
import shutil
import sys

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
assert (REPO / "src" / "tcf").is_dir(), f"REPO errado: {REPO}"
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(RAIZ))

from specs import alvos_para  # noqa: E402
from tcf import decode, encode  # noqa: E402

INP, INT, OUT = RAIZ / "inputs", RAIZ / "intermediates", RAIZ / "outputs"
JSON_KW = {"ensure_ascii": False, "indent": 1}
N = 600
rnd = random.Random(20260813)


def _esc(p, t):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(t, encoding="utf-8", newline="")


def _js(p, o):
    _esc(p, json.dumps(o, **JSON_KW))


def B(t):
    return len(t.encode("utf-8"))


def _limpa():
    for d in (INP, INT, OUT):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)


# (nome, valores, ideia, espera: 'core' = o nucleo ja' resolve / 'spec' = ha' folga)
CASOS = [
    # --- progressão: onde o seq-RLE quer entrar ---
    ("prog-passo1-largura-varia", [str(i) for i in range(1, N + 1)],
     "1..600: o run QUEBRA em 9->10 e 99->100 (3 marcadores)", "spec"),
    ("prog-passo7", [str(i * 7) for i in range(N)],
     "passo 7, largura varia de 1 a 4 digitos", "spec"),
    ("prog-largura-fixa", [str(100000 + i) for i in range(N)],
     "mesma progressao com largura JA' constante — o nucleo resolve sozinho", "core"),
    ("prog-epoch", [str(1750000000 + i * 60) for i in range(N)],
     "timestamp de 10 digitos, passo 60: o OBAT fragmenta antes do seq-RLE ver", "spec"),
    ("prog-descendente", [str(1000 - i) for i in range(N)],
     "descendente: o core JA' resolve em 25 B — PIN CORRIGIDO 2026-08-13 (eu esperava spec)", "core"),
    ("prog-base-alta", [str(10**9 + i) for i in range(N)],
     "1e9+i: 10 digitos onde so' os 3 ultimos variam", "spec"),
    # --- sem progressão ---
    ("id-largura-fixa-6", [str(rnd.randrange(100000, 999999)) for _ in range(N)],
     "ids aleatorios de 6 digitos: hoje o TCF nao ganha nada", "spec"),
    ("id-largura-fixa-11", [f"{rnd.randrange(10**10, 10**11):011d}" for _ in range(N)],
     "ids de 11 digitos (o regime do CPF, sem mascara)", "spec"),
    ("faixa-pequena-0-100", [str(rnd.randrange(101)) for _ in range(N)],
     "0..100 aleatorio: cardinalidade baixa, o bN ja' morde", "core"),
    ("cardinalidade-5", [str(rnd.choice([10, 20, 30, 40, 50])) for _ in range(N)],
     "k=5: territorio do bN de dominio", "core"),
    ("quase-constante", ["42"] * (N - 3) + ["43", "44", "45"],
     "k=4 desbalanceado: RLE do nucleo", "core"),
    # --- bordas e sujeira ---
    ("negativos", [str(rnd.randrange(-500, 501)) for _ in range(N)],
     "com sinal: offset+pad PIORA (0,89x) — o pad custa mais que o '-'. PIN CORRIGIDO", "core"),
    ("com-nulos", [None if i % 37 == 0 else str(i) for i in range(1, N + 1)],
     "slots nulos no meio da progressao", "spec"),
    ("sujo-10pct", None,
     "10% nao-inteiros: cada literal quebra o run E paga marcador; o FLOOR recusa. PIN CORRIGIDO", "core"),
    ("zeros-a-esquerda", [f"{i:06d}" for i in range(1, N + 1)],
     "ARMADILHA: '000001' NAO e' o inteiro 1 — o RT exige recusar", "core"),
    ("misto-largura", [str(rnd.choice([5, 50, 500, 5000, 50000])) for _ in range(N)],
     "larguras misturadas SEM progressao: o pad so' paga se houver run. PIN CORRIGIDO", "core"),
]


def _sujo():
    v = [str(i) for i in range(1, N + 1)]
    for k in range(N // 10):
        v[(k * 7) % N] = rnd.choice(["n/a", "", "12.5", "-", "1e3"])
    return v


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    _limpa()
    falhas, tabela = [], []

    for nome, vals, ideia, espera in CASOS:
        if vals is None:
            vals = _sujo()
        _js(INP / f"{nome}.entrada.json", vals)
        _js(INP / f"{nome}.fonte.json", {
            "caso": nome, "ideia": ideia, "espera": espera, "n": len(vals),
            "k_unicos": len(set(map(str, vals))), "primeiros": vals[:5],
            "hash": hashlib.sha256(json.dumps(vals, **JSON_KW).encode()).hexdigest()[:12],
            "CONSTANTE_na_comparacao": "n=600; TODOS os candidatos passam pelo MESMO "
                                       "`encode()` publico (o FLOOR real decide); so' o "
                                       "alvo varia. Alvos dimensionados pela coluna.",
        })

        w_core = encode(vals)
        if decode(w_core) != vals:
            falhas.append(f"{nome}: RT do core quebrou")
        cands = {"core": (B(w_core), w_core, "encode(vals)")}
        _specs = {}

        strs = [v for v in vals if v is not None]
        for alvo in alvos_para(strs):
            try:
                w = encode(vals, nature=alvo)
                # spec de TERCEIRO (fora do registry core) tem de ser fornecido
                # out-of-band no decode — resolucao ESTRITA do ADR-0041. Se o wire
                # nao carrega `:id` (o FLOOR recusou o alvo), o `nature=` e' ignorado.
                if decode(w, nature=alvo) != vals:
                    falhas.append(f"{nome}/{alvo.name}: RT quebrou")
                    continue
                cands[alvo.name] = (B(w), w, f"encode(vals, nature={alvo!r})")
                _specs[alvo.name] = alvo
            except Exception as e:
                falhas.append(f"{nome}/{alvo.name}: {type(e).__name__}: {str(e)[:60]}")

        venc = min(cands, key=lambda k: cands[k][0])
        b_core, b_venc = cands["core"][0], cands[venc][0]
        _esc(OUT / f"{nome}.tcf", cands[venc][1])
        _js(OUT / f"{nome}.roundtrip.json", decode(cands[venc][1], nature=_specs.get(venc)))
        _js(INT / f"{nome}.candidatos.json", {
            "ideia": ideia, "espera": espera, "vencedor": venc,
            "candidatos": {k: {"bytes": b, "como": c, "header": w.split("\n")[0][:40]}
                           for k, (b, w, c) in cands.items()},
        })
        # PIN: o nunca-pior e' garantido pelo FLOOR do encode; aqui checo a EXPECTATIVA
        bateu = (venc == "core") == (espera == "core")
        tabela.append({"caso": nome, "ideia": ideia, "espera": espera, "vencedor": venc,
                       "core": b_core, "melhor": b_venc,
                       "ganho": round(b_core / b_venc, 2), "pin_bateu": bateu})
        marca = "ok " if bateu else "DIVERGIU"
        print(f"  {nome:26s} core {b_core:6d} -> {venc:10s} {b_venc:6d} "
              f"({b_core / b_venc:5.2f}x)  pin {marca}")

    _js(RAIZ / "resultado.json", {"tabela": tabela, "falhas": falhas})
    idx = ["# INDEX", "", "| caso | ideia | espera | venceu | core | melhor | ganho |",
           "|---|---|---|---|---:|---:|---:|"]
    for t in tabela:
        idx.append(f"| [`{t['caso']}`](./{t['caso']}.tcf) | {t['ideia']} | {t['espera']} "
                   f"| **{t['vencedor']}** | {t['core']} | {t['melhor']} | {t['ganho']}x |")
    idx += ["", "Candidatos por caso em `../intermediates/<c>.candidatos.json`; contra-prova "
                "em `<c>.roundtrip.json` (diff contra `../inputs/<c>.entrada.json`).", ""]
    _esc(OUT / "INDEX.md", "\n".join(idx))

    div = [t for t in tabela if not t["pin_bateu"]]
    print(f"\n{len(tabela)} casos · {len(falhas)} falha(s) de RT · {len(div)} pin(s) divergente(s)")
    for t in div:
        print(f"  PIN: {t['caso']} esperava {t['espera']}, venceu {t['vencedor']}")
    for f in falhas[:8]:
        print(f"  FALHA: {f}")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
