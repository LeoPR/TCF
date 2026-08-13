"""Entrega incremental do nucleo — as 3 afirmacoes do owner, medidas. `python run.py`

O owner (2026-08-13) descreveu o modelo de streaming em 3 partes:

  (A) *"o nucleo tem maleabilidade para parar a busca e entregar pedacos... enquanto vai
      coletando e fazendo a busca e comparacao, se em algum momento passar um tempo, e'
      possivel pegar o que ja' foi coletado, entregar adiante. obviamente existe o risco
      dele nao conseguir melhores comparacoes"*
  (B) *"depois que ele para pra entregar, ele fica com dicionarios cada vez mais fechados,
      pois ele precisou congelar o que deu pra entregar em cada etapa"*
  (C) *"quando se acha coisas como uma cadeia de true e false, mandar pedacos nao faz
      diferenca, pois o decode fica coletando e descomprimindo de acordo com a demanda.
      Ele so' falha se tiver algo no final."*

Este lab mede (C) — a parte diretamente testavel pela API publica — e o que ela revela
sobre (A) e (B). A auditoria de codigo de (A)/(B) (interrompibilidade da busca, estado
congelado entre pulsos) vive na nota que acompanha.

## O erro de metodo que este lab corrige (do lab das 17h40)

O lab `...-1740-latencia-como-eixo` mediu **p wires INDEPENDENTES** (cada fatia re-encodada
do zero). Isso responde "quanto custa emitir p wires", que NAO e' o modelo do owner. O
modelo dele e' **1 wire entregue em p pedacos**: os bytes ja' existem, o custo de streaming
e' ZERO por construcao, e a pergunta e' *quanto cada pedaco recebido ja' entrega*.

`src/tcf` NAO e' tocado.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import pathlib
import random
import shutil
import sys
import warnings

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
assert (REPO / "src" / "tcf").is_dir(), f"REPO errado: {REPO}"
sys.path.insert(0, str(REPO / "src"))

from tcf import decode, encode  # noqa: E402
from tcf.natures import SPEC_DATA_ISO as S  # noqa: E402

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


def _limpa():
    for d in (INP, INT, OUT):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)


def _uteis(n):
    out, d = [], BASE
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += dt.timedelta(days=1)
    return out


CASOS = [
    ("bool-blocos", ["true"] * 200 + ["false"] * 200 + ["true"] * 200, {},
     "RLE: cada marcador e' uma linha AUTOCONTIDA"),
    ("bool-alternado", ["true", "false"] * (N // 2), {},
     "bN de dominio: dicionario na frente, indices empacotados numa linha densa"),
    ("bool-aleatorio", [rnd.choice(["true", "false"]) for _ in range(N)], {},
     "idem, sem estrutura de bloco"),
    ("bool-tudo-true", ["true"] * N, {}, "RLE total: UMA linha entrega tudo"),
    ("categoria-k5", [rnd.choice(["ativo", "inativo", "pendente", "suspenso", "novo"])
                      for _ in range(N)], {}, "bN com 5 valores de dominio"),
    ("data-spec", [(BASE + dt.timedelta(days=i)).isoformat() for i in range(N)], {"nature": S},
     "seq-RLE: UMA linha — compressao maxima, granularidade minima"),
    ("data-uteis-spec", _uteis(N), {"nature": S}, "seq-RLE periodico: idem, UMA linha"),
    ("texto", [f"registro-{i:04d}" for i in range(N)], {}, "OBAT por afixo: varias linhas"),
    ("email", [f"usuario{i}@empresa.com.br" for i in range(N)], {}, "idem, afixo mais longo"),
]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    _limpa()
    falhas, tabela = [], []

    for nome, vals, kw, ideia in CASOS:
        wire = encode(vals, **kw)
        if decode(wire) != vals:
            falhas.append(f"{nome}: RT do wire inteiro quebrou")
        _js(INP / f"{nome}.entrada.json", vals)
        _js(INP / f"{nome}.fonte.json", {
            "caso": nome, "ideia": ideia, "n": len(vals), "k_unicos": len(set(vals)),
            "spec": "data-iso" if kw else None, "primeiros": vals[:4],
            "hash": hashlib.sha256(json.dumps(vals, **JSON_KW).encode()).hexdigest()[:12],
            "CONSTANTE_na_comparacao": "n=600; o wire e' encodado UMA vez e entregue em "
                                       "prefixos de LINHAS INTEGRAS — zero re-encode, zero "
                                       "custo de bytes. So' o TIPO/regime varia.",
        })
        _esc(OUT / f"{nome}.tcf", wire)
        _js(OUT / f"{nome}.roundtrip.json", decode(wire))

        partes = wire.split("\n")
        cab, corpo = partes[0], [x for x in partes[1:] if x != ""]
        curva, detalhe = [], []
        for k in range(1, len(corpo) + 1):
            frag = cab + "\n" + "\n".join(corpo[:k]) + "\n"
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                try:
                    got = decode(frag)
                    entregue = len(got) if got == vals[:len(got)] else -1
                    if entregue == -1:
                        falhas.append(f"{nome}: prefixo de {k} linha(s) devolveu valor ERRADO "
                                      f"sem erro (classe corrupcao-calada)")
                except Exception as e:
                    entregue = None
                    got = None
            curva.append(entregue)
            detalhe.append({
                "linhas_recebidas": k, "bytes_recebidos": len(frag.encode("utf-8")),
                "valores_entregues": entregue,
                "linha": corpo[k - 1][:60],
            })
        _js(INT / f"{nome}.entrega-incremental.json", {
            "ideia": ideia, "bytes_totais": len(wire.encode("utf-8")),
            "linhas_de_corpo": len(corpo), "curva": curva, "detalhe": detalhe,
        })
        # pontos de entrega = prefixos que JA' respondem algo
        pontos = sum(1 for c in curva if isinstance(c, int) and c > 0)
        primeiro = next((i + 1 for i, c in enumerate(curva) if isinstance(c, int) and c > 0), None)
        tabela.append({
            "caso": nome, "ideia": ideia, "bytes": len(wire.encode("utf-8")),
            "linhas_de_corpo": len(corpo), "pontos_de_entrega": pontos,
            "1a_resposta_na_linha": primeiro, "curva": curva,
            "granularidade": (round(N / pontos) if pontos else None),
        })
        txt = ", ".join("-" if c is None else ("ERRADO" if c == -1 else str(c)) for c in curva[:8])
        print(f"  {nome:18s} {len(wire.encode()):5d} B  {len(corpo):2d} linha(s)  "
              f"{pontos} ponto(s) de entrega   curva: {txt}")

    _js(RAIZ / "resultado.json", {"tabela": tabela, "falhas": falhas})
    _esc(OUT / "INDEX.md", "\n".join([
        "# INDEX", "",
        "| caso | ideia | wire | entrega incremental | contra-prova |", "|---|---|---|---|---|",
        *[f"| `{t['caso']}` | {t['ideia']} | [.tcf](./{t['caso']}.tcf) ({t['bytes']} B, "
          f"{t['linhas_de_corpo']} linha(s)) | [curva](../intermediates/{t['caso']}."
          f"entrega-incremental.json) — {t['pontos_de_entrega']} ponto(s) | "
          f"[roundtrip](./{t['caso']}.roundtrip.json) |" for t in tabela],
        "", "**Pontos de entrega** = quantos prefixos de linhas integras ja' respondem algo "
            "correto. E' a granularidade natural de streaming daquela coluna: o wire e' o "
            "MESMO, so' muda em quantos pedacos uteis ele se deixa cortar.", "",
        "A contra-prova de cada caso e' `diff` entre `outputs/<c>.roundtrip.json` e "
        "`inputs/<c>.entrada.json` (mesma formatacao; tem de dar vazio).", ""]))

    print(f"\n{len(falhas)} falha(s)")
    for f in falhas[:8]:
        print(f"  FALHA: {f}")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
