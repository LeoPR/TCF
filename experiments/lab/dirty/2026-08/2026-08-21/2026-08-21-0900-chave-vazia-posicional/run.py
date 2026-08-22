"""BUG-CHAVE-VAZIA-POSICIONAL — o unico caso em que o TCF ALTERA o dado.

O BUG
-----
    decode(encode({"": ["a","b"]}))  ->  {"0": ["a","b"]}    (com UserWarning)

O TCF ou PRESERVA ou FALHA ALTO. Este caso foge do contrato: muta a chave.

A CAUSA RAIZ (medida aqui)
--------------------------
`encode({"": [...]})` produz EXATAMENTE o mesmo wire que
`encode({"x": [...]}, drop_names=True)`. O formato nao distingue "nome VAZIO"
de "SEM nome" — e no decode o vazio vira posicional.

A SOLUCAO JA' EXISTE NO PROJETO
-------------------------------
O `.8H` resolveu isto com o sentinela `\\z` (`hierarchical.py:114`) e preserva
`{"": ...}` com RT=True. A rota flat/multi nao adotou. Nao ha' o que inventar:
e' adotar a MESMA grafia.

  G1  o bug, reproduzido, e a COLISAO que o causa
  G2  o `.8H` de fato preserva? (a rota vizinha como prova de conceito)
  G3  o slot `\\z` esta' LIVRE no multi? algum nome real colide?
  G4  PROTOTIPO da correcao (no lab, `src/tcf` INTOCADO) + custo em bytes
  G5  MOTIVACAO: de onde vem uma coluna sem nome no mundo real
"""

from __future__ import annotations

import csv
import io
import json
import sys
import warnings
from pathlib import Path

AQUI = Path(__file__).parent
RAIZ = AQUI.parents[5]
sys.path.insert(0, str(RAIZ / "src"))

IN, OUT = AQUI / "inputs", AQUI / "outputs"
for d in (IN, OUT):
    d.mkdir(parents=True, exist_ok=True)

from tcf import encode, decode                                       # noqa: E402
from tcf.multi.core import _ESC_OK                                   # noqa: E402

LF = chr(10)
_arquivos: set[Path] = set()


def grava(pasta: Path, nome: str, texto: str) -> None:
    q = pasta / nome
    q.write_text(texto, encoding="utf-8", newline="")
    _arquivos.add(q.resolve())


def main() -> int:
    res = {}
    warnings.simplefilter("ignore")
    print("=" * 96)
    print("BUG-CHAVE-VAZIA-POSICIONAL — o unico caso em que o TCF ALTERA o dado")
    print("=" * 96)

    # ── G1 ───────────────────────────────────────────────────────────────
    print(LF + "G1) O BUG, e a COLISAO que o causa")
    d = {"": ["a", "b"]}
    w = encode(d)
    r = decode(w)
    print(f"  entrada {d}")
    print(f"  wire    {w!r}")
    print(f"  decode  {r}     RT={r == d}")
    colide = encode({"x": ["a", "b"]}, drop_names=True)
    print(f"{LF}  e o wire de `drop_names=True`: {colide!r}")
    print(f"  IDENTICO ao do nome vazio? {w == colide}")
    print("  => a causa e' essa: o formato nao distingue VAZIO de SEM-NOME.")
    assert r != d and w == colide
    grava(IN, "chave-vazia.json", json.dumps(d, ensure_ascii=False))
    grava(OUT, "chave-vazia-HOJE.tcf", w)
    grava(OUT, "chave-vazia-HOJE.decode-errado.json", json.dumps(r, ensure_ascii=False))
    res["G1"] = {"entrada": d, "wire": w, "decode": r,
                 "colide_com_drop_names": w == colide}

    # ── G2 ───────────────────────────────────────────────────────────────
    print(LF + "=" * 96)
    print("G2) A ROTA VIZINHA JA' RESOLVEU — o `.8H` preserva com `\\z`")
    print("=" * 96)
    for dh in ({"": {"x": 1}}, [{"": 1, "a": 2}]):
        wh = encode(dh)
        rh = decode(wh)
        print(f"  {str(dh):<22} -> {wh!r:<34} RT={rh == dh}")
        assert rh == dh
    grava(OUT, "chave-vazia-8H-funciona.tcf", encode([{"": 1, "a": 2}]))
    grava(OUT, "chave-vazia-8H-funciona.roundtrip.json",
          json.dumps(decode(encode([{"": 1, "a": 2}])), ensure_ascii=False))
    print("  => nao ha' o que inventar: a grafia existe e esta' provada na rota ao lado.")
    res["G2"] = {"h_preserva": True, "sentinela": "\\z"}

    # ── G3 ───────────────────────────────────────────────────────────────
    print(LF + "=" * 96)
    print("G3) O SLOT ESTA' LIVRE? — `z` na whitelist do multi, e colisao real")
    print("=" * 96)
    print(f"  whitelist de escape do multi: {_ESC_OK!r}")
    print(f"  'z' esta nela? {'z' in _ESC_OK}   -> {'COLIDE' if 'z' in _ESC_OK else 'LIVRE'}")
    assert "z" not in _ESC_OK
    print(f"{LF}  algum nome REAL emite `\\z` no header?")
    colisoes = []
    for nome in ("z", "\\z", "az", "z ", "\\", "\\\\z", "Z"):
        h = encode({nome: ["1"]}).splitlines()[0]
        marca = "  <-- COLIDIRIA" if h.endswith("!\\z") else ""
        if marca:
            colisoes.append(nome)
        print(f"    {nome!r:8} -> {h!r}{marca}")
    print(f"  colisoes: {len(colisoes)}")
    assert not colisoes
    res["G3"] = {"z_na_whitelist": "z" in _ESC_OK, "colisoes": colisoes}

    # ── G4 ───────────────────────────────────────────────────────────────
    print(LF + "=" * 96)
    print("G4) PROTOTIPO da correcao (src/tcf INTOCADO) + custo")
    print("=" * 96)
    print("  A correcao e' de UMA REGRA, nos dois lados:")
    print("    encode: nome == ''  ->  emite `\\z` (em vez de nao emitir nada)")
    print("    decode: token `\\z`  ->  nome ''   (em vez de posicional)")
    print("  Exatamente o que `hierarchical.py:114` ja' faz.")

    def encode_corrigido(tab: dict) -> str:
        """Mock: reescreve o header trocando o nome vazio por `\\z`."""
        w = encode(tab)
        cab, corpo = w.split(LF, 1)
        # o header de nome vazio termina em '!' (sem nome apos o discriminador)
        toks = list(tab)
        if "" in toks and len(toks) == 1:
            cab = cab + "\\z"
        return cab + LF + corpo

    def decode_corrigido(wire: str) -> dict:
        cab, corpo = wire.split(LF, 1)
        if cab.endswith("!\\z"):
            base = decode(cab[:-2] + LF + corpo)
            return {"": next(iter(base.values()))}
        return decode(wire)

    wc = encode_corrigido(d)
    rc = decode_corrigido(wc)
    print(f"{LF}  hoje      {w!r:<26} -> {decode(w)}   RT=False")
    print(f"  corrigido {wc!r:<26} -> {rc}   RT={rc == d}")
    print(f"  custo: {len(wc.encode()) - len(w.encode())} bytes (o `\\z`)")
    assert rc == d
    grava(OUT, "chave-vazia-CORRIGIDO.tcf", wc)
    grava(OUT, "chave-vazia-CORRIGIDO.roundtrip.json", json.dumps(rc, ensure_ascii=False))
    res["G4"] = {"wire_corrigido": wc, "rt": rc == d,
                 "custo_bytes": len(wc.encode()) - len(w.encode())}

    # nenhum wire EXISTENTE muda
    print(f"{LF}  e nenhum wire de nome NAO-vazio muda:")
    iguais = 0
    for nome in ("a", "col_1", "a,b", "a=b", "z", "\\z", "nome longo"):
        t = {nome: ["1", "2"]}
        if encode(t) == encode_corrigido(t):
            iguais += 1
        else:
            print(f"    MUDOU: {nome!r}")
    print(f"    {iguais}/7 identicos ao de hoje")
    assert iguais == 7
    res["G4"]["wires_inalterados"] = iguais

    # ── G5 ───────────────────────────────────────────────────────────────
    print(LF + "=" * 96)
    print("G5) MOTIVACAO — de onde vem coluna sem nome no mundo real")
    print("=" * 96)
    # O nome vazio nasce do PROPRIO CSV (RFC 4180): campo vazio e' campo legal,
    # e no header vira nome de coluna vazio. Nao depende de ferramenta nenhuma.
    exemplos_csv = {
        "virgula sobrando no header": "a,b," + LF + "1,2,3" + LF,
        "coluna sem titulo no meio": "a,,b" + LF + "1,2,3" + LF,
        "primeira coluna sem titulo": ",a,b" + LF + "0,1,2" + LF,
    }
    print("  O nome vazio nasce do PROPRIO CSV (RFC 4180): campo vazio e' campo")
    print("  legal, e no header ele vira nome de coluna vazio.")
    quebram = 0
    for rot, texto in exemplos_csv.items():
        rd = csv.reader(io.StringIO(texto))
        h = next(rd)
        cols = {k: [] for k in h}
        for row in rd:
            for k, v in zip(h, row):
                cols[k].append(v)
        back = decode(encode(cols))
        ok = back == cols
        quebram += (not ok)
        print(f"    {rot:<28} header={h}  RT={ok}")
    print(f"{LF}  quebram o RT: {quebram}/{len(exemplos_csv)}")
    assert quebram == len(exemplos_csv)
    texto = exemplos_csv["virgula sobrando no header"]
    rd = csv.reader(io.StringIO(texto))
    h = next(rd)
    cols = {k: [] for k in h}
    for row in rd:
        for k, v in zip(h, row):
            cols[k].append(v)
    back = decode(encode(cols))
    grava(IN, "csv-header-com-virgula-sobrando.csv", texto)
    grava(OUT, "csv-header-HOJE.tcf", encode(cols))
    grava(OUT, "csv-header-HOJE.decode-errado.json", json.dumps(back, ensure_ascii=False))
    print(f"{LF}  => e' propriedade do CSV, nao de ferramenta. `fail-loud` (opcao 1 do")
    print("     ticket) recusaria CSV valido por RFC 4180.")
    res["G5"] = {"exemplos": list(exemplos_csv), "quebram": quebram,
                 "cols": cols, "decode": back}

    (AQUI / "resultado.json").write_text(json.dumps(res, ensure_ascii=False, indent=1),
                                         encoding="utf-8", newline="")
    achados = {q.resolve() for pasta in (IN, OUT) for q in pasta.rglob("*") if q.is_file()}
    assert not (_arquivos - achados) and not (achados - _arquivos)
    print(f"{LF}-> {len(achados)} arquivos, portao anti-orfao verde")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
