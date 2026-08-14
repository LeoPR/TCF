"""PROTOTIPO — leitor de PREFIXO das rotas densas. `python prototipo_leitor_prefixo.py`

## Para que serve (enquadramento, nao solucao)

A auditoria de 2026-08-13 mostrou que o criterio do owner — *"so' falha se tiver algo no
final"* — descreve corretamente o WIRE e incorretamente o CODIGO: nenhuma rota emitida hoje
tem trailer, mas o `decode()` publico recusa **100%** dos prefixos das rotas densas. Quem
recusa e' uma guarda de integridade (`valida_payload_b64` exige `len(raw) == ceil(n*w/8)`
EXATO, `composicional/dominio_bn.py:146`), nao o layout.

Este prototipo prova, em codigo executavel, que **os bits estao la'**: le' um prefixo do fio
e entrega os valores que ja' deu pra saber. Serve pra ENQUADRAR a decisao (`T-DECODE-PREFIXO`)
com evidencia, nao pra resolver — a decisao de expor um modo de leitura parcial ao lado do
canonico e' de escopo `.9`/`2.0`, e o `.8` tem outras prioridades (tipos, depois M e H).

**NAO e' candidato a weld**: nao valida integridade, nao cobre todas as rotas, e um leitor
parcial de verdade precisa decidir o que fazer com o guard — que existe por um motivo
(distinguir "chegou 90%" de "wire adulterado" e' justamente o que ele nao consegue).

`src/tcf` NAO e' tocado: o prototipo le' o wire por fora.
"""
from __future__ import annotations

import base64
import json
import pathlib
import random
import sys

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
sys.path.insert(0, str(REPO / "src"))

from tcf import decode, encode  # noqa: E402

B64 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"


def le_prefixo_denso(pedaco: str) -> list | None:
    """`#TCF.8b1<n hex>\\n<b64>` (coluna BOOL densa) -> os valores que o prefixo permite.

    Le' so' grupos base64 COMPLETOS (4 chars = 3 bytes = 24 bits): o ultimo grupo parcial
    e' descartado, porque um char b64 cortado nao carrega byte fechado.
    """
    if not pedaco.startswith("#TCF.8b1"):
        return None
    cab, _, corpo = pedaco.partition("\n")
    n_total = int(cab[len("#TCF.8b1"):], 16)
    corpo = corpo.split("\n")[0]
    inteiros = len(corpo) // 4 * 4          # so' grupos fechados
    if inteiros == 0:
        return []
    raw = base64.b64decode(corpo[:inteiros])
    bits = "".join(format(b, "08b") for b in raw)
    return [b == "1" for b in bits[:n_total]]


def le_prefixo_bn(pedaco: str) -> list | None:
    """`#TCF.8B<w><n hex>\\n<dominio...>\\n=<b64>` -> os valores que o prefixo permite.

    O dominio vem NA FRENTE (e' o modo `B`, escolhido pelo projeto justamente por streamar
    — `encoder.py:484-489`). So' da' pra ler indices depois de o dominio fechar no `=`.
    """
    if not pedaco.startswith("#TCF.8B"):
        return None
    linhas = pedaco.split("\n")
    cab = linhas[0]
    w = int(cab[7])                          # largura em bits do indice
    n_total = int(cab[8:], 16)
    dom_bruto, i = [], 1
    while i < len(linhas) and not linhas[i].startswith("="):
        dom_bruto.append(linhas[i])
        i += 1
    if i >= len(linhas):
        return []                            # o dominio ainda nem fechou
    # ACHADO DO PROTOTIPO (2026-08-13): o dominio do bN e' CORE-COMPRIMIDO, nao
    # literal. Num caso medido ele sai `ativo` / `in1` / `pendente`, onde `in1` e'
    # "in" + referencia ao fragmento 1 (= "inativo") — um digito NU, sem `*` nem
    # `^`. Ler o dominio literalmente devolve valor ERRADO em silencio (foi o que
    # este prototipo fez na 1a versao). Logo: um leitor de prefixo do bN precisa do
    # DECODIFICADOR DO CORE pro dominio; nao basta desempacotar bits. Sao DUAS
    # camadas, e e' por isso que a rota densa `b1` (dominio implicito) e' a facil.
    from tcf.decoder import _decode_column

    dom = _decode_column("\n".join(dom_bruto) + "\n")
    corpo = linhas[i][1:]
    inteiros = len(corpo) // 4 * 4
    if inteiros == 0:
        return []
    raw = base64.b64decode(corpo[:inteiros])
    bits = "".join(format(b, "08b") for b in raw)
    out = []
    for k in range(0, len(bits) - w + 1, w):
        if len(out) >= n_total:
            break
        idx = int(bits[k:k + w], 2)
        if idx >= len(dom):
            break
        out.append(dom[idx])
    return out


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    rnd = random.Random(20260813)
    casos = [
        ("bool 3-ciclo n=600", [bool(i % 3) for i in range(600)], le_prefixo_denso),
        ("bool aleatorio n=600", [rnd.random() < 0.5 for _ in range(600)], le_prefixo_denso),
        ("categoria k=3 n=600",
         [rnd.choice(["ativo", "inativo", "pendente"]) for _ in range(600)], le_prefixo_bn),
    ]
    saida = []
    print("PROTOTIPO — o `decode()` recusa prefixo; os bits estao la'\n")
    for nome, vals, leitor in casos:
        wire = encode(vals)
        assert decode(wire) == vals, "RT do wire inteiro quebrou"
        B = wire.encode("utf-8")
        print(f"{nome}  ({len(B)} B, header {wire.splitlines()[0]!r})")
        print(f"  {'% do fio':>9s} {'decode() publico':>18s} {'prototipo':>12s} {'corretos':>10s}")
        linhas = []
        for frac in (0.10, 0.25, 0.50, 0.75, 0.90, 1.00):
            corte = max(1, int(len(B) * frac))
            pedaco = B[:corte].decode("utf-8", errors="ignore")
            try:
                decode(pedaco)
                oficial = "entregou"
            except Exception:
                oficial = "recusa"
            got = leitor(pedaco)
            if got is None:
                proto, ok = "n/a", "-"
            else:
                proto = f"{len(got)} val"
                ok = "todos" if got == vals[:len(got)] else "*ERRO*"
                if got != vals[:len(got)]:
                    print("    !! prototipo devolveu valor ERRADO — nao usar")
            print(f"  {frac * 100:8.0f}% {oficial:>18s} {proto:>12s} {ok:>10s}")
            linhas.append({"frac": frac, "bytes": corte, "decode_publico": oficial,
                           "prototipo_valores": None if got is None else len(got),
                           "corretos": ok})
        saida.append({"caso": nome, "bytes": len(B), "header": wire.splitlines()[0],
                      "curva": linhas})
        print()
    (RAIZ / "intermediates" / "prototipo-leitor-prefixo.json").write_text(
        json.dumps(saida, ensure_ascii=False, indent=1), encoding="utf-8", newline="")
    print("Curva gravada em intermediates/prototipo-leitor-prefixo.json")
    print("\nLEITURA: onde o `decode()` diz 'recusa' e o prototipo entrega valores CORRETOS,")
    print("a informacao estava no fio — o que falta e' um modo de leitura parcial, nao formato.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
