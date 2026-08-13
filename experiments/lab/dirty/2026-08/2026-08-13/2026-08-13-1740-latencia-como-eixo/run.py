"""Latencia e' o eixo; o periodo e' acessorio. `python run.py`

## Por que este lab existe

Correcao do owner (2026-08-13): *"a questao do periodo e' acessorio para relacionar com a
latencia... a rigor o que existe e' tentar responder por slices de tempo, ou menor
latencia. e isso vale pra virtualmente qualquer tipo... nao e' so' pegar a data e picotar,
e' sobre como transmitir em pequenos slices de tempo... ela [a fatia] tem que derivar da
latencia"*.

O registro anterior (`notas/2026-08/2026-08-10-nomes-lazy-e-pulsos-revisao.md`) concluiu o
INVERSO, e a frase esta' la': *"Um modo de baixa latencia nao pode cortar em qualquer
lugar"* — a latencia submetida a' estrutura do dado. Este lab mede quem manda.

## As 4 perguntas

1. **O custo de fatiar e' propriedade da DATA?** (se for, o periodo importa; se nao,
   e' propriedade de outra coisa)
2. **Cortar "fora de fase" e' realmente ilegal?** (a afirmacao que fechou a nota anterior)
3. **O que governa o preco de uma fatia?**
4. **Onde esta' o penhasco** — o menor slice antes do custo explodir?

`src/tcf` NAO e' tocado: o lab so' chama a API publica.
"""
from __future__ import annotations

import datetime as dt
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

from tcf import decode, encode  # noqa: E402
from tcf.natures import SPEC_CPF, SPEC_DATA_ISO as S  # noqa: E402

INP, INT, OUT = RAIZ / "inputs", RAIZ / "intermediates", RAIZ / "outputs"
JSON_KW = {"ensure_ascii": False, "indent": 1}
N = 600
BASE = dt.date(2026, 1, 1)
rnd = random.Random(20260813)


def _esc(p, t):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(t, encoding="utf-8", newline="")


def _js(p, o):
    _esc(p, json.dumps(o, **JSON_KW))


def _B(t):
    return len(t.encode("utf-8"))


def _limpa():
    for d in (INP, INT, OUT):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)


def _cpf(i):
    corpo = [(i * 7 + j) % 10 for j in range(9)]
    for _ in range(2):
        s = sum((len(corpo) + 1 - k) * d for k, d in enumerate(corpo))
        r = s % 11
        corpo.append(0 if r < 2 else 11 - r)
    d = "".join(map(str, corpo))
    return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"


def _uteis(n, base=BASE):
    out, d = [], base
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += dt.timedelta(days=1)
    return out


# (rotulo, valores, spec, o que representa)
TIPOS = [
    ("data-diaria-spec", [(BASE + dt.timedelta(days=i)).isoformat() for i in range(N)], S,
     "progressao perfeita + spec: o MAIOR ganho do projeto (26 B p/ 600 valores)"),
    ("data-uteis-spec", _uteis(N), S,
     "delta CICLICO (periodo 5) + spec: o caso que motivou o ADR-0040"),
    ("data-diaria-core", [(BASE + dt.timedelta(days=i)).isoformat() for i in range(N)], None,
     "a MESMA data sem spec: isola o efeito do spec do efeito do tipo"),
    ("cpf-spec", [_cpf(i) for i in range(N)], SPEC_CPF,
     "spec sem progressao (Unique-Discrete): comprime por valor, nao por sequencia"),
    ("inteiro-sequencial", [str(1000 + i) for i in range(N)], None,
     "progressao SEM spec e SEM periodo: controle do eixo 'periodo'"),
    ("email-afixo", [f"usuario{i}@empresa.com.br" for i in range(N)], None,
     "ganho por AFIXO compartilhado (OBAT), nao por sequencia"),
    ("categoria-k5", [rnd.choice(["ativo", "inativo", "pendente", "suspenso", "novo"])
                      for _ in range(N)], None,
     "ganho por DICIONARIO (baixa cardinalidade)"),
    ("texto-aleatorio", ["".join(rnd.choice("abcdefghijklmnop") for _ in range(12))
                         for _ in range(N)], None,
     "quase incompressivel: o controle de baixo"),
]
CORTES = [1, 2, 4, 6, 8, 12, 20, 60]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    _limpa()
    falhas = []

    # ── P1/P3/P4: a regua do fatiamento, por tipo ────────────────────────────
    regua = []
    for rotulo, vals, spec, ideia in TIPOS:
        kw = {"nature": spec} if spec else {}
        _js(INP / f"{rotulo}.entrada.json", vals)
        _js(INP / f"{rotulo}.fonte.json", {
            "rotulo": rotulo, "ideia": ideia, "n": len(vals),
            "k_unicos": len(set(vals)), "spec": spec.name if spec else None,
            "primeiros": vals[:3],
            "hash": hashlib.sha256(json.dumps(vals, **JSON_KW).encode()).hexdigest()[:12],
            "CONSTANTE_na_comparacao": "n=600, mesmos cortes, cada fatia e' um wire "
                                       "INDEPENDENTE (decodificavel sozinha) — so' o TIPO varia",
        })
        linha = {"tipo": rotulo, "ideia": ideia, "cortes": {}}
        for p in CORTES:
            tam = N // p
            fatias, total = [], 0
            for i in range(p):
                f = vals[i * tam:(i + 1) * tam] if i < p - 1 else vals[i * tam:]
                w = encode(f, **kw)
                if decode(w) != f:
                    falhas.append(f"{rotulo} p={p} fatia {i}: RT quebrou")
                fatias.append(w)
                total += _B(w)
            linha["cortes"][p] = {
                "bytes_total": total, "bytes_1a_fatia": _B(fatias[0]),
                "valores_por_fatia": tam,
                "grafia_1a_fatia": fatias[0].split("\n")[1][:24] if "\n" in fatias[0] else "",
            }
            if p == 1:
                _esc(OUT / f"{rotulo}.inteiro.tcf", fatias[0])
                _js(OUT / f"{rotulo}.inteiro.roundtrip.json", decode(fatias[0]))
            if p == 8:
                _esc(OUT / f"{rotulo}.8fatias.tcf", "\n=== FATIA ===\n".join(fatias))
                volta = []
                for w in fatias:
                    volta += decode(w)
                _js(OUT / f"{rotulo}.8fatias.roundtrip.json", volta)
                if volta != vals:
                    falhas.append(f"{rotulo}: concatenacao das 8 fatias != entrada")
        base = linha["cortes"][1]["bytes_total"]
        linha["multiplicador"] = {p: round(linha["cortes"][p]["bytes_total"] / base, 2)
                                  for p in CORTES}
        linha["preco_por_fatia_p8"] = round(linha["cortes"][8]["bytes_total"] / 8, 1)
        regua.append(linha)
        print(f"  {rotulo:20s} p=1 {base:6d} B  ->  p=8 {linha['cortes'][8]['bytes_total']:6d} B "
              f"({linha['multiplicador'][8]:5.2f}x)  preco/fatia {linha['preco_por_fatia_p8']:6.1f} B")

    # ── P2: "cortar fora de fase e' ilegal"? ────────────────────────────────
    # A nota de 2026-08-10 concluiu que sim (pulso periodico exige 2p+1 e pad rotacionado).
    # Aqui: cortar dias uteis (periodo 5) em TODOS os tamanhos de 1 a 40, inclusive
    # primos e fora de fase. Se a latencia manda, TODA fatia tem de ser emissivel.
    uteis = _uteis(N)
    fora_de_fase = []
    for tam in range(1, 41):
        fatias, total, ok = [], 0, True
        for i in range(0, N, tam):
            f = uteis[i:i + tam]
            w = encode(f, nature=S)
            if decode(w) != f:
                ok = False
                falhas.append(f"corte fora-de-fase tam={tam}: RT quebrou")
            fatias.append(w)
            total += _B(w)
        fora_de_fase.append({
            "tamanho_da_fatia": tam, "n_fatias": len(fatias), "bytes_total": total,
            "fora_de_fase": tam % 5 != 0, "rt_ok": ok,
            "grafia": fatias[0].split("\n")[1][:20] if "\n" in fatias[0] else "",
        })
    _js(INT / "corte-fora-de-fase.json", fora_de_fase)
    ilegais = [r for r in fora_de_fase if not r["rt_ok"]]
    print(f"\n  corte fora de fase: {len(fora_de_fase)} tamanhos testados (1..40), "
          f"{len(ilegais)} ilegais")

    # ── P4: o penhasco — custo por VALOR em funcao do tamanho da fatia ──────
    penhasco = []
    diarias = [(BASE + dt.timedelta(days=i)).isoformat() for i in range(N)]
    for tam in [600, 400, 300, 200, 150, 120, 100, 90, 80, 75, 60, 50, 30, 20, 12, 10, 8, 5, 3, 2, 1]:
        w = encode(diarias[:tam], nature=S)
        if decode(w) != diarias[:tam]:
            falhas.append(f"penhasco tam={tam}: RT quebrou")
        corpo = w.split("\n")[1] if "\n" in w else ""
        penhasco.append({
            "valores_na_fatia": tam, "bytes": _B(w), "bytes_por_valor": round(_B(w) / tam, 3),
            "grafia": corpo[:24],
            "usa_marcador_seq_rle": corpo.startswith("*"),
        })
    _js(INT / "penhasco-por-tamanho-de-fatia.json", penhasco)
    ativa = [r for r in penhasco if r["usa_marcador_seq_rle"]]
    limiar = min(r["valores_na_fatia"] for r in ativa) if ativa else None
    print(f"  penhasco: o marcador seq-RLE ativa a partir de {limiar} valores/fatia")

    # ── P5: o TEMPO — sem ele "200 ms" nao vira numero de valores ───────────
    # Mede o custo de encodar UMA fatia, por tamanho, e converte um deadline em N.
    # Nao e' benchmark de performance (maquina nao-quiescente, K pequeno): e' a ORDEM
    # DE GRANDEZA que a conversao deadline->N precisa. Numero probatorio = bench_perf.
    import statistics
    import time

    K = 7
    tempo = []
    for rotulo, vals, spec, _ideia in TIPOS:
        kw = {"nature": spec} if spec else {}
        for tam in (600, 300, 100, 50, 10):
            f = vals[:tam]
            xs = []
            for _ in range(K):
                t0 = time.perf_counter()
                encode(f, **kw)
                xs.append((time.perf_counter() - t0) * 1e3)
            ms = statistics.median(xs)
            tempo.append({"tipo": rotulo, "valores_na_fatia": tam, "ms_mediana": round(ms, 3),
                          "us_por_valor": round(ms * 1000 / tam, 1),
                          "valores_em_200ms": int(200 / ms * tam) if ms > 0 else None})
    _js(INT / "tempo-por-fatia.json", tempo)
    d100 = [t for t in tempo if t["valores_na_fatia"] == 100]
    print("\n  tempo p/ encodar UMA fatia de 100 valores (mediana de 7; ordem de grandeza):")
    for t in sorted(d100, key=lambda x: x["ms_mediana"]):
        print(f"    {t['tipo']:20s} {t['ms_mediana']:7.3f} ms  "
              f"-> em 200 ms caberiam ~{t['valores_em_200ms']:,} valores")

    _js(RAIZ / "resultado.json", {
        "regua_por_tipo": regua, "corte_fora_de_fase": fora_de_fase,
        "penhasco": penhasco, "limiar_seq_rle": limiar, "tempo": tempo, "falhas": falhas,
    })

    # ── INDEX ──
    idx = ["# INDEX", "", "| arquivo | o que e' |", "|---|---|",
           "| `intermediates/corte-fora-de-fase.json` | os 40 tamanhos de fatia (1..40) em dias "
           "uteis (periodo 5), com RT por tamanho — a prova da pergunta 2 |",
           "| `intermediates/penhasco-por-tamanho-de-fatia.json` | bytes/valor por tamanho de "
           "fatia + se o marcador seq-RLE ativou — a prova da pergunta 4 |",
           "| `outputs/<tipo>.inteiro.tcf` | o wire de 600 valores em UMA fatia |",
           "| `outputs/<tipo>.8fatias.tcf` | os mesmos 600 em 8 fatias independentes "
           "(separadas por `=== FATIA ===`, que NAO faz parte do wire) |",
           "| `outputs/<tipo>.*.roundtrip.json` | contra-prova: diff contra `inputs/<tipo>.entrada.json` |",
           "", "Cada fatia de `*.8fatias.tcf` e' um wire COMPLETO e decodificavel sozinho — e' "
               "isso que 'responder em slices' quer dizer.", ""]
    _esc(OUT / "INDEX.md", "\n".join(idx))

    print(f"\n{len(falhas)} falha(s)")
    for f in falhas[:10]:
        print(f"  FALHA: {f}")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
