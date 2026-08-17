"""O header do `.8H`, em casos sintéticos MÍNIMOS.

A PERGUNTA
----------
Como o header do `.8H` se escreve, produção por produção? Não "quanto ele custa" —
isso já foi medido. Aqui é para **ler o header**, byte a byte, num caso pequeno o
bastante para caber na cabeça.

A REGRA DESTE LAB
-----------------
Cada caso é MINÚSCULO e REPRESENTATIVO de uma produção da gramática:
2-3 linhas, valores de 1-4 caracteres. Se o wire não couber numa linha de terminal,
o caso está grande demais e foi mal escolhido.

Nada de porcentagem, nada de corpus. Um caso, uma produção, um header legível.

O QUE FICA EM DISCO (por caso)
------------------------------
  inputs/<caso>.json           a entrada exata
  outputs/<caso>.tcf           o wire
  outputs/<caso>.roundtrip.json  o decode
  outputs/<caso>.header.md     o header DECOMPOSTO, campo a campo

O roundtrip é o assert: se `decode(encode(x)) != x`, o caso FALHA e aparece no
relatório. Nenhum byte é reportado sem RT validado (§RT).

`src/tcf` INTOCADO. Nada de rede, nada de corpus externo.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

AQUI = Path(__file__).parent
RAIZ = AQUI.parents[5]
sys.path.insert(0, str(RAIZ / "src"))

IN = AQUI / "inputs"
OUT = AQUI / "outputs"
for d in (IN, OUT):
    d.mkdir(parents=True, exist_ok=True)

from tcf import encode, decode  # noqa: E402


# ── os casos: um por produção da gramática, o menor que a exercita ─────────
CASOS: list[tuple[str, str, object]] = [
    # (id, que produção este caso exercita, entrada)

    # -- a raiz --
    ("raiz_dataset",
     "dataset `list[dict]` — SEM disc de raiz (o caso base)",
     [{"a": "x"}, {"a": "y"}]),

    ("raiz_objeto",
     "`#O` — objeto único na raiz",
     {"a": "x", "b": "y"}),

    ("raiz_valor",
     "`#V` + nome de campo `\\z` — escalar solto na raiz",
     "x"),

    ("raiz_vazio_dict",
     "`#E` — `{}`, sem corpo nenhum",
     {}),

    ("raiz_contagem",
     "`#D<N>` — lista de objetos SEM campo (só a contagem sobrevive)",
     [{}, {}, {}]),

    # -- os campos --
    ("campo_dois",
     "dois campos escalares, separados por `,`",
     [{"a": "x", "b": "y"}, {"a": "z", "b": "w"}]),

    ("campo_nulo",
     "máscara `?:<size>` — vem ANTES da coluna do campo",
     [{"a": "x"}, {"a": None}]),

    ("campo_ausente",
     "ragged: campo que falta numa linha (também usa máscara)",
     [{"a": "x", "b": "y"}, {"a": "z"}]),

    ("campo_aninhado",
     "`{` — objeto dentro de campo, achatado no caminho",
     [{"a": {"b": "x"}}, {"a": {"b": "y"}}]),

    ("campo_array",
     "`#:<size>[` — coluna de contagem + coluna de itens",
     [{"a": ["x", "y"]}, {"a": ["z"]}]),

    # -- os tipos --
    ("tipo_numero",
     "tag `n` na forma do campo",
     [{"a": 1}, {"a": 2}]),

    ("tipo_bool",
     "tag `b` na forma do campo",
     [{"a": True}, {"a": False}]),

    ("tipo_misto_de_campos",
     "campos de tipos DIFERENTES lado a lado (str, n, b)",
     [{"s": "x", "n": 1, "b": True}, {"s": "y", "n": 2, "b": False}]),

    # -- as bordas do NOME --
    ("nome_vazio",
     "`\\z` — chave vazia num objeto",
     {"": "x"}),

    ("nome_com_separador",
     "nome que contém os separadores do meta (`,` `:` `#`)",
     [{"a,b": "x", "c:d": "y"}, {"a,b": "z", "c:d": "w"}]),
]


def decompoe_header(l1: str) -> list[str]:
    """Anota o header em pedaços legíveis. HEURÍSTICO — é leitura, não parser."""
    assert l1.startswith("#TCF.8H")
    meta = l1[7:]
    out = [f"`#TCF.8H`  ({len('#TCF.8H')} B)  assinatura + discriminador H"]
    if not meta:
        out.append("*(meta vazio)*")
        return out
    raiz = ""
    for pref in ("#D", "#E", "#O", "#V"):
        if meta.startswith(pref):
            resto = meta[len(pref):]
            n = ""
            if pref == "#D":
                while resto[:1].isdigit():
                    n, resto = n + resto[0], resto[1:]
            raiz, meta = pref + n, resto
            break
    if raiz:
        rot = {"#D": "lista de N objetos sem campo", "#E": "objeto vazio",
               "#O": "objeto único na raiz", "#V": "valor solto na raiz"}[raiz[:2]]
        out.append(f"`{raiz}`  disc de RAIZ — {rot}")
    if meta:
        out.append(f"`{meta}`  os campos")
    return out


# ── a folha TIPADA: o que a tag `b`/`n` do header realmente carrega ────────
# Achado ao ler o wire de `tipo_bool`: o corpo e' o TEXTO 'true\nfalse', nao um
# denso. O mecanismo esta' em `hierarchical.py:227-229` — a folha STRINGIFICA o
# escalar (`json.dumps` p/ numero, 'true'/'false' p/ bool) ANTES de montar a
# coluna, e o tipo volta no decode pela TAG do header. Entao `_encode_col` nunca
# ve `list[bool]` na rota `.8H`: ve `list[str]`. Os densos `b1`/`b2` nao entram.
#
# Aqui a comparacao minima, lado a lado, so' pra VER o efeito crescer com n.
TIPADOS = [
    ("bool", lambda n: [True, False] * (n // 2)),
    ("int", lambda n: list(range(n))),
    ("float", lambda n: [i + 0.5 for i in range(n)]),
]


def secao_tipada() -> list[dict]:
    print()
    print("=" * 76)
    print("A FOLHA TIPADA — a mesma coluna pelas DUAS rotas")
    print("=" * 76)
    print(f"  {'tipo':>6} {'n':>4}   {'.8H (folha)':<22} {'single-col':<18}  razao")
    linhas = []
    for nome, gera in TIPADOS:
        for n in (2, 24):
            col = gera(n)
            ds = [{"a": v} for v in col]
            wH, wS = encode(ds), encode(col)
            okH, okS = decode(wH) == ds, decode(wS) == col
            bH, bS = len(wH.encode()), len(wS.encode())
            cid = f"tipado_{nome}_n{n}"
            (IN / f"{cid}.json").write_text(
                json.dumps(ds, ensure_ascii=False), encoding="utf-8", newline="")
            (OUT / f"{cid}.8H.tcf").write_text(wH, encoding="utf-8", newline="")
            (OUT / f"{cid}.single.tcf").write_text(wS, encoding="utf-8", newline="")
            (OUT / f"{cid}.roundtrip.json").write_text(
                json.dumps(decode(wH), ensure_ascii=False), encoding="utf-8", newline="")
            if not (okH and okS):
                print(f"  *** RT FALHOU em {cid}")
            print(f"  {nome:>6} {n:>4}   {wH.splitlines()[0]!r:<16}{bH:>4} B   "
                  f"{wS.splitlines()[0]!r:<12}{bS:>4} B  {bH/bS:>5.1f}x")
            linhas.append({"tipo": nome, "n": n, "header_H": wH.splitlines()[0],
                           "bytes_H": bH, "header_single": wS.splitlines()[0],
                           "bytes_single": bS, "razao": round(bH / bS, 2),
                           "rt_H": okH, "rt_single": okS})
    return linhas


def main() -> int:
    print("=" * 76)
    print("O HEADER DO .8H EM CASOS SINTETICOS MINIMOS")
    print("=" * 76)

    tabela, falhas = [], 0
    for cid, producao, entrada in CASOS:
        (IN / f"{cid}.json").write_text(
            json.dumps(entrada, ensure_ascii=False, indent=1),
            encoding="utf-8", newline="")
        try:
            wire = encode(entrada)
            volta = decode(wire)
            rt = volta == entrada
        except Exception as e:
            print(f"  [ERRO] {cid:22} {type(e).__name__}: {str(e)[:46]}")
            falhas += 1
            tabela.append({"id": cid, "producao": producao, "erro":
                           f"{type(e).__name__}: {e}", "rt": False})
            continue

        (OUT / f"{cid}.tcf").write_text(wire, encoding="utf-8", newline="")
        (OUT / f"{cid}.roundtrip.json").write_text(
            json.dumps(volta, ensure_ascii=False, indent=1),
            encoding="utf-8", newline="")

        l1 = wire.split("\n", 1)[0]
        eh_h = l1.startswith("#TCF.8H")
        pedacos = decompoe_header(l1) if eh_h else [f"`{l1}`  — NAO roteou pro .8H"]
        (OUT / f"{cid}.header.md").write_text(
            "\n".join([f"# {cid}", "", f"**Produção**: {producao}", "",
                       "## Entrada", "", "```json",
                       json.dumps(entrada, ensure_ascii=False), "```", "",
                       "## Wire", "", "```", wire, "```", "",
                       f"header = **{len(l1.encode())} B** de "
                       f"**{len(wire.encode())} B** "
                       f"({len(l1.encode())/len(wire.encode())*100:.0f}%)", "",
                       "## Header, pedaço a pedaço", "",
                       *[f"- {p}" for p in pedacos], "",
                       "## Round-trip", "",
                       f"`decode(encode(x)) == x` -> **{rt}**", ""]),
            encoding="utf-8", newline="")

        if not rt:
            falhas += 1
        marca = "  " if rt else " *RT!*"
        rota = "" if eh_h else "  <- NAO e' .8H"
        print(f"  {cid:22}{marca} {l1!r:34} "
              f"{len(l1.encode()):3}/{len(wire.encode()):3} B{rota}")
        tabela.append({"id": cid, "producao": producao, "header": l1,
                       "bytes_header": len(l1.encode()),
                       "bytes_wire": len(wire.encode()),
                       "rota_H": eh_h, "rt": rt})

    print("=" * 76)
    print(f"{len(CASOS)} casos · {len(CASOS)-falhas} com round-trip OK · {falhas} falhas")

    tipados = secao_tipada()

    # relatorio
    L = ["# O header do `.8H` em casos sintéticos mínimos", "",
         "Gerado por `run.py`. Re-rode com `python run.py`.", "",
         f"**{len(CASOS)} casos, {len(CASOS)-falhas} com round-trip OK.**", "",
         "Cada caso é o MENOR que exercita uma produção da gramática do meta.",
         "O detalhe de cada um (entrada, wire, header decomposto, RT) está em",
         "`outputs/<caso>.header.md`.", "",
         "| caso | produção | header | H? | RT | hdr/wire |",
         "|---|---|---|:-:|:-:|---:|"]
    _tip = tipados
    for r in tabela:
        if "erro" in r:
            L.append(f"| `{r['id']}` | {r['producao']} | — | — | **ERRO** | "
                     f"`{r['erro'][:52]}` |")
        else:
            L.append(f"| `{r['id']}` | {r['producao']} | `{r['header']}` | "
                     f"{'sim' if r['rota_H'] else '**NAO**'} | "
                     f"{'ok' if r['rt'] else '**FALHA**'} | "
                     f"{r['bytes_header']}/{r['bytes_wire']} B |")
    (AQUI / "RESULTADO.md").write_text("\n".join(L) + "\n",
                                       encoding="utf-8", newline="")
    (AQUI / "resultado.json").write_text(
        json.dumps({"gramatica": tabela, "tipados": tipados},
                   ensure_ascii=False, indent=1),
        encoding="utf-8", newline="")
    print(f"-> {AQUI / 'RESULTADO.md'}")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
