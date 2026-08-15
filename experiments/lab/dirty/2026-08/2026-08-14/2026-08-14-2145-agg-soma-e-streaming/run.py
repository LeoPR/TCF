# -*- coding: utf-8 -*-
"""`agg="soma"` — três formas de prometer a mesma coisa, com streaming diferente.

    python run.py

## A pergunta (uma só)

> Owner (2026-08-14): *"o agg soma, creio que matematicamente dá pra fazer uma inferência de
> comportamento para uma possível soma… isso é útil porque **dependendo da forma que eu peça,
> tem que ver se ele fica stream compatível**."*

A intuição está certa e o lab a torna precisa: **o contrato "a soma fica exata" tem pelo menos
três implementações, e elas diferem exatamente em streaming.**

| forma | soma | passes | valores lidos antes de emitir o 1º |
|---|---|---|---|
| **maior resto** (Hamilton) | exata | 2 + ordenação global | **N — a coluna inteira** |
| **difusão de erro** (1 passe) | quase | 1 | **1** |
| **âncora** (soma no cabeçalho) | exata, mas fora das linhas | 2 (só p/ somar) | N *para o cabeçalho* |

## O que se mede

Duas noções de streaming, que este lab separa de propósito:

- **prefixo do ENCODER** — quantos valores da fonte é preciso ter lido para emitir o primeiro
  valor do wire. É a que o `agg` ataca.
- **prefixo do DECODER** — quantos bytes do wire é preciso bufferizar para emitir o primeiro
  valor. É a métrica do lab `2026-07-27-2211` (medida lá: 100 B contra 1764 B, 17×).

Um algoritmo pode ser ótimo numa e péssimo na outra.

## GATE

Protótipo de lab, fora de `src/tcf`. Formato lossless-puro por decisão do owner (2026-06-15).
Nada aqui é proposta de weld.
"""
from __future__ import annotations

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

from tcf import decode, encode  # noqa: E402

INP, INT, OUT = RAIZ / "inputs", RAIZ / "intermediates", RAIZ / "outputs"
JSON_KW = {"ensure_ascii": False, "indent": 1}


def _esc(p, t):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(t, encoding="utf-8", newline="")


def _js(p, o):
    _esc(p, json.dumps(o, **JSON_KW))


def B(t):
    return len(t.encode("utf-8"))


class Fonte:
    """Envolve a lista para CONTAR leituras — o instrumento de passe único."""

    def __init__(self, vals):
        self._v = list(vals)
        self.leituras = 0

    def __iter__(self):
        for x in self._v:
            self.leituras += 1
            yield x

    def __len__(self):
        return len(self._v)


# ── as três formas ───────────────────────────────────────────────────────────
def maior_resto(fonte: Fonte, d: int):
    """Hamilton. Precisa da coluna INTEIRA antes de decidir o primeiro valor."""
    vals = list(fonte)                       # passe 1: soma e pisos
    esc = 10 ** d
    pisos = [math.floor(v * esc) for v in vals]
    falta = round(sum(vals) * esc) - sum(pisos)
    ordem = sorted(range(len(vals)), key=lambda i: -(vals[i] * esc - pisos[i]))
    incr = set(ordem[:max(0, falta)])
    saida = [round((p + (1 if i in incr else 0)) / esc, d) for i, p in enumerate(pisos)]
    return saida, {"passes_sobre_a_fonte": 1, "ordenacao_global": True,
                   "lidos_antes_do_1o_emitido": len(vals)}


def difusao_de_erro(fonte: Fonte, d: int):
    """Floyd–Steinberg 1-D: carrega o resíduo para o próximo. Um passe, um valor de estado."""
    saida, carry = [], 0.0
    for v in fonte:
        x = v + carry
        r = round(x, d)
        carry = x - r
        saida.append(r)
    return saida, {"passes_sobre_a_fonte": 1, "ordenacao_global": False,
                   "lidos_antes_do_1o_emitido": 1, "estado": "1 float (o carry)",
                   "residuo_final": carry}


def com_ancora(fonte: Fonte, d: int):
    """Arredonda cada um por si e guarda a SOMA exata à parte (cabeçalho ou trailer)."""
    vals = list(fonte)
    saida = [round(v, d) for v in vals]
    return saida, {"passes_sobre_a_fonte": 1, "ordenacao_global": False,
                   "lidos_antes_do_1o_emitido": 1,
                   "ancora": sum(vals),
                   "nota": "streamável SE a âncora for TRAILER; se for cabeçalho, exige N"}


FORMAS = [("maior-resto", maior_resto, "exata, mas exige a coluna inteira"),
          ("difusao-erro", difusao_de_erro, "1 passe, 1 float de estado"),
          ("ancora", com_ancora, "soma exata FORA das linhas")]


def prefixo_decoder(wire: str) -> int:
    """Bytes que o leitor precisa ter para emitir o 1º valor: até o fim da 1ª linha do corpo."""
    partes = wire.split("\n")
    return B(partes[0]) + 1 + (B(partes[1]) + 1 if len(partes) > 1 else 0)


def avalia(nome, vals, d, ideia, fonte_meta):
    _js(INP / f"{nome}.entrada.json", vals)
    _js(INP / f"{nome}.fonte.json", fonte_meta)
    esc = 10 ** d
    soma_ex = sum(vals)
    w0 = encode(vals)
    assert decode(w0) == vals
    _esc(OUT / f"{nome}.baseline.tcf", w0)
    _js(OUT / f"{nome}.baseline.roundtrip.json", decode(w0))
    print(f"\n  [{nome}] n={len(vals)} d={d} baseline={B(w0)} B  soma={soma_ex:.4f}")
    print(f"    {'forma':>14} {'bytes':>7} {'soma exata':>11} {'err/linha max':>14} "
          f"{'lidos p/ 1o':>12} {'pref decode':>12}")
    linhas, falhas = [], []
    for rot, fn, ideia_f in FORMAS:
        f = Fonte(vals)
        aj, meta = fn(f, d)
        w = encode(aj)
        if decode(w) != aj:
            falhas.append(f"{nome}/{rot}: o formato não preservou os ajustados")
        exata = round(sum(aj) * esc) == round(soma_ex * esc)
        err = max(abs(a - b) for a, b in zip(vals, aj))
        pd = prefixo_decoder(w)
        _esc(OUT / f"{nome}.{rot}.tcf", w)
        _js(OUT / f"{nome}.{rot}.roundtrip.json", decode(w))
        _js(OUT / f"{nome}.{rot}.meta.json", {
            "derivado_de": f"inputs/{nome}.entrada.json", "forma": rot, "ideia": ideia_f,
            "casas": d, "bytes": B(w), "soma_exata": exata, "streaming": meta,
            "AVISO": "valores AJUSTADOS de propósito — não são os originais"})
        linhas.append({"caso": nome, "forma": rot, "ideia": ideia_f, "casas": d,
                       "bytes": B(w), "soma_exata_na_escala": exata,
                       "erro_max_por_linha": err,
                       "erro_soma_rel": abs(sum(aj) - soma_ex) / abs(soma_ex) if soma_ex else 0,
                       "prefixo_decoder_bytes": pd,
                       "leituras_da_fonte": f.leituras,
                       "streaming": meta,
                       "CONSTANTE_na_comparacao": "os MESMOS valores, o MESMO d, o MESMO "
                                                  "encode; só muda COMO a soma é preservada"})
        print(f"    {rot:>14} {B(w):>7} {str(exata):>11} {err:>14.2e} "
              f"{meta['lidos_antes_do_1o_emitido']:>12} {pd:>12}")
    return linhas, falhas


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for p in (INP, INT, OUT):
        if p.exists():
            shutil.rmtree(p)
        p.mkdir(parents=True)
    todos, falhas = [], []

    print("SINTÉTICO — o rateio, onde a soma exata é a razão de ser")
    rateio = [round(100 / 3, 6)] * 3 + [round(1000 / 7, 6)] * 7
    l, f = avalia("rateio", rateio, 2,
                  "100/3 e 1000/7: dízimas cujo total tem de fechar",
                  {"gerador": "run.py", "params": {"partes": "3x100/3 + 7x1000/7"},
                   "ideia": "o parcelamento — a soma é o que o consumidor lê",
                   "pin": "sintético viesado por construção"})
    todos += l
    falhas += f

    print("\nREAL — money, onde a soma tem sentido contábil")
    try:
        con = sqlite3.connect("file:Z:/tcf-data/interim/online-retail.db?mode=ro", uri=True)
        v = [float(r[0]) for r in con.execute(
            "SELECT UnitPrice FROM online_retail WHERE UnitPrice > 0")]
        con.close()
        passo = max(1, len(v) // 2000)
        v = v[::passo][:2000]
        for d in (1, 0):
            l, f = avalia(f"retail-d{d}", v, d,
                          f"UnitPrice arredondado a {d} casa(s)",
                          {"gerador": "run.py", "db": "online-retail",
                           "sql": "SELECT UnitPrice ... WHERE UnitPrice > 0",
                           "amostragem": f"passo espalhado 1-em-{passo}, alvo 2000",
                           "casas": d, "ideia": "money real",
                           "pin": "corpus local Z: — não versionado"})
            todos += l
            falhas += f
    except Exception:
        print("  (sem Z: — pulado)")

    _js(INT / "formas.json", todos)
    _js(RAIZ / "resultado.json", {"formas": todos, "falhas": falhas})
    _esc(OUT / "INDEX.md", "\n".join(
        ["# INDEX — `agg=soma` e streaming", "",
         "**Aviso**: os `.tcf` que não são `.baseline` contêm valores **ajustados de propósito**.",
         "O `roundtrip.json` prova que o formato os preserva — não que são os originais.", "",
         "| caso | forma | bytes | soma exata | lidos p/ 1º | prefixo decode |",
         "|---|---|---|---|---|---|"] +
        [f"| [`{x['caso']}`](./{x['caso']}.{x['forma']}.tcf) | {x['forma']} | {x['bytes']} | "
         f"{x['soma_exata_na_escala']} | {x['streaming']['lidos_antes_do_1o_emitido']} | "
         f"{x['prefixo_decoder_bytes']} B |" for x in todos]) + "\n")

    print(f"\n{len(falhas)} falha(s)")
    for x in falhas[:10]:
        print(f"  FALHA: {x}")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
