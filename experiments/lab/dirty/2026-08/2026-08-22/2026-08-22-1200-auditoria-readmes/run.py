"""Auditoria dos READMEs de capa (git + PyPI) — pedido do owner 2026-08-22.

POR QUE ISTO EXISTE (e nao e' o varre_snippets)
-----------------------------------------------
O `varre_snippets.py` (2026-08-16) EXECUTA todo bloco python dos docs e declara, no proprio
docstring, o que NAO faz: *"nao verifica prosa, nao verifica numero solto no texto, e nao sabe
conferir a 'saida esperada' quando ela nao esta' num bloco imediatamente adjacente"*.

O README de capa e' feito exatamente do que ele nao cobre: blocos de WIRE (nao-python, entao
nao executam) com contagem de bytes afirmada na PROSA ao lado. Um wire que envelhece nao
quebra teste nenhum — so' mente pro leitor, e e' a primeira coisa que alguem le no GitHub e
no PyPI.

A REGUA: nao hardcoda o esperado. Le' o numero AFIRMADO no proprio README (`*(NNN B...)*`),
reconstroi o exemplo a partir dos dados que o proprio README mostra (o CSV, o JSON), roda o
`encode` de verdade e compara BYTES e WIRE LITERAL.

RESSALVA de metodo (declarada): um bloco cercado em markdown SEMPRE termina com LF antes do
fence, entao a comparacao de wire e' feita modulo UM LF final — o wire multi-col real NAO
termina em LF, e isso e' inrepresentavel em bloco cercado. Confirmado a mao:
`encode(tabela).endswith(chr(10))` e' False.

G1  exemplo de capa flat: CSV / TCF / TCF+nature — bytes e wire
G2  exemplo aninhado .8H: JSON / TCF+nature — bytes e wire
G3  bloco da secao de natures (single-col) — bytes e reducao %
G4  exemplo do view() — todos os valores dos comentarios
G5  numeros soltos da prosa (suite) e caminhos citados
G6  paridade EN x pt-BR dos numeros de capa
G7  README.pypi.md (long-description): ZERO link relativo, links do repo que
    existem, e os exemplos rodando — a pagina do PyPI nao tem arvore de repo
"""

from __future__ import annotations

import csv as _csv
import io
import json
import re
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).parent
RAIZ = AQUI.parents[5]
sys.path.insert(0, str(RAIZ / "src"))

IN, OUT = AQUI / "inputs", AQUI / "outputs"
for _d in (IN, OUT):
    _d.mkdir(parents=True, exist_ok=True)

from tcf import SPEC_CPF, decode, encode, view  # noqa: E402

LF = chr(10)
_arquivos: set[Path] = set()
falhas: list[str] = []


def grava(pasta: Path, nome: str, texto: str) -> None:
    q = pasta / nome
    q.write_text(texto, encoding="utf-8", newline="")
    _arquivos.add(q.resolve())


def nb(s: str) -> int:
    return len(s.encode("utf-8"))


def check(rot: str, doc, real) -> bool:
    ok = doc == real
    print(f"   {'OK   ' if ok else 'FALHA'} {rot:<46} doc={doc!r}  real={real!r}")
    if not ok:
        falhas.append(f"{rot}: doc={doc!r} real={real!r}")
    return ok


def blocos_apos(texto: str, marcador: str) -> list[str]:
    return re.findall(r"```[a-z]*\n(.*?)```", texto[texto.index(marcador):], re.S)


def bytes_afirmados(texto: str, marcador: str) -> int:
    """Le' o `NNN B` que o proprio README afirma no rotulo do bloco."""
    m = re.search(r"\((\d+)\s*B", texto[texto.index(marcador):][:120])
    assert m, f"nao achei bytes afirmados apos {marcador!r}"
    return int(m.group(1))


def mesmo_wire(doc: str, real: str) -> bool:
    """Compara modulo UM LF final (o fence sempre acrescenta um)."""
    return doc.rstrip(LF) == real.rstrip(LF)


def main() -> int:
    READ = (RAIZ / "README.md").read_text(encoding="utf-8")
    PT = (RAIZ / "README.pt-BR.md").read_text(encoding="utf-8")
    res: dict = {}

    print("=" * 92)
    print("G1) EXEMPLO DE CAPA (flat) — dados lidos do PROPRIO CSV do README")
    print("=" * 92)
    csv_txt = blocos_apos(READ, "**CSV** *(")[0]
    linhas = list(_csv.reader(io.StringIO(csv_txt.strip())))
    hdr, corpo = linhas[0], linhas[1:]
    tab = {h: [r[i] for r in corpo] for i, h in enumerate(hdr)}
    grava(IN, "cadastro.csv", csv_txt)

    check("CSV bytes (sem LF final)", bytes_afirmados(READ, "**CSV** *("), nb(csv_txt.rstrip(LF)))

    w_flat = encode(tab)
    m_flat = "**TCF** *("
    check("TCF flat bytes", bytes_afirmados(READ, m_flat), nb(w_flat))
    check("TCF flat wire", True, mesmo_wire(blocos_apos(READ, m_flat)[0], w_flat))
    assert decode(w_flat) == tab, "RT flat"
    grava(OUT, "capa-flat.tcf", w_flat)

    w_nat = encode(tab, schema={"cpf": SPEC_CPF})
    m_nat = "**TCF + CPF nature** *("
    check("TCF+nature bytes", bytes_afirmados(READ, m_nat), nb(w_nat))
    check("TCF+nature wire", True, mesmo_wire(blocos_apos(READ, m_nat)[0], w_nat))
    assert decode(w_nat) == tab, "RT nature"
    grava(OUT, "capa-flat-nature.tcf", w_nat)
    res["G1"] = {"csv_B": nb(csv_txt.rstrip(LF)), "tcf_B": nb(w_flat), "nature_B": nb(w_nat)}

    print()
    print("=" * 92)
    print("G2) EXEMPLO ANINHADO (.8H)")
    print("=" * 92)
    m_js = "**JSON** *(184"
    recs = json.loads(blocos_apos(READ, m_js)[0])
    grava(IN, "registros-aninhados.json", json.dumps(recs, ensure_ascii=False, indent=1))
    check("JSON aninhado bytes (compacto)", bytes_afirmados(READ, m_js),
          nb(json.dumps(recs, ensure_ascii=False, separators=(",", ":"))))
    w_h = encode(recs, schema={"cpf": SPEC_CPF})
    m_h = "**TCF + CPF nature** *(" + str(nb(w_h))
    check("TCF .8H bytes", bytes_afirmados(READ, m_h), nb(w_h))
    check("TCF .8H wire", True, mesmo_wire(blocos_apos(READ, m_h)[0], w_h))
    assert decode(w_h) == recs, "RT .8H"
    grava(OUT, "capa-aninhado.tcf", w_h)
    res["G2"] = {"json_B": nb(json.dumps(recs, ensure_ascii=False, separators=(",", ":"))),
                 "tcf8h_B": nb(w_h)}

    print()
    print("=" * 92)
    print("G3) SECAO DE NATURES (single-col)")
    print("=" * 92)
    cpfs = tab["cpf"]
    sem, com = encode(cpfs), encode(cpfs, schema=SPEC_CPF)
    m = re.search(r"# Same 4 CPFs: (\d+) B single-col without the nature -> (\d+) B with it \((-?\d+)%\)", READ)
    check("nature: sem nature B", int(m.group(1)), nb(sem))
    check("nature: com nature B", int(m.group(2)), nb(com))
    check("nature: reducao %", int(m.group(3)), round(100 * (nb(com) - nb(sem)) / nb(sem)))
    assert decode(com) == cpfs, "RT nature solo"
    grava(OUT, "natures-single-col.tcf", com)
    res["G3"] = {"sem_B": nb(sem), "com_B": nb(com)}

    print()
    print("=" * 92)
    print("G4) EXEMPLO DO view()")
    print("=" * 92)
    tabela = {
        "cliente": ["Ana Souza", "Bruno Lima", "Carla Nunes", "Diego Rocha", "Eva Martins", "Ana Souza"],
        "cidade": ["Sao Paulo", "Sao Paulo", "Sao Paulo", "Rio de Janeiro", "Sao Paulo", "Rio de Janeiro"],
        "plano": ["Premium", "Premium", "Basic", "Premium", "Basic", "Premium"],
        "valor": ["120", "100", "170", "200", "80", "80"],
    }
    blob = encode(tabela)
    v = view(blob)
    for rot, doc, real in (
        ("view: blob B", int(re.search(r"# (\d+) B of ASCII text", READ).group(1)), nb(blob)),
        ("view: count()", 6, v.count()),
        ("view: sum(valor)", 750, int(v.sum("valor"))),
        ("view: avg(valor)", 125, int(v.avg("valor"))),
        ("view: max/min", (200, 80), (int(v.max("valor")), int(v.min("valor")))),
        ("view: where.count()", 4, v.where("cidade", "Sao Paulo").count()),
        ("view: where.sum()", 470, int(v.where("cidade", "Sao Paulo").sum("valor"))),
    ):
        check(rot, doc, real)
    assert decode(blob) == tabela, "RT view"
    grava(OUT, "view-vendas.tcf", blob)
    res["G4"] = {"blob_B": nb(blob)}

    print()
    print("=" * 92)
    print("G5) PROSA E CAMINHOS")
    print("=" * 92)
    r = subprocess.run([sys.executable, "-X", "utf8", "-m", "pytest", "-q"],
                       cwd=RAIZ, capture_output=True, text=True)
    ms = re.search(r"(\d+) passed, (\d+) skipped", r.stdout)
    suite = f"{ms.group(1)} passed, {ms.group(2)} skipped"
    for arq, t in (("README.md", READ), ("README.pt-BR.md", PT)):
        md = re.search(r"\*\*(\d+ passed, \d+ skipped)\*\*", t)
        check(f"{arq}: suite afirmada", md.group(1) if md else None, suite)
    # README.pypi.md e' a long-description do PyPI: pagina UNICA, sem arvore
    # de repo — link relativo e imagem local nao resolvem la'. Isto guarda isso.
    PYPI = (RAIZ / "README.pypi.md").read_text(encoding="utf-8")
    _links = re.findall(r"\]\(([^)]+)\)", PYPI)
    _rel = [x for x in _links if not x.startswith(("http", "#", "mailto"))]
    check("PyPI: links relativos (quebram la')", 0, len(_rel))
    _faltam = [x for _u, x in re.findall(
        r"\]\((https://github\.com/LeoPR/TCF/blob/main/([^)]+))\)", PYPI)
        if not (RAIZ / x).exists()]
    check("PyPI: links pro repo inexistentes", [], _faltam)
    _n = 0
    for _n, _b in enumerate(re.findall(r"```python\n(.*?)```", PYPI, re.S), 1):
        exec(compile(_b, f"<README.pypi bloco {_n}>", "exec"), {})
    print(f"   [info] {_n} bloco(s) python do README.pypi executado(s) com seus asserts")
    res["PyPI"] = {"links": len(_links), "relativos": len(_rel), "blocos": _n}

    caminhos = sorted(set(re.findall(r"\(`([a-z][\w./-]+/)`\)", READ)))
    for c in caminhos:
        if not (RAIZ / c).exists():
            check(f"caminho citado {c}", True, False)
    print(f"   [info] {len(caminhos)} caminhos em backtick conferidos")
    res["G5"] = {"suite": suite, "caminhos": len(caminhos)}

    print()
    print("=" * 92)
    print("G6) PARIDADE EN x pt-BR (numeros de capa)")
    print("=" * 92)
    for rot, mk_en, mk_pt in (("CSV", "**CSV** *(", "**CSV** *("),
                              ("TCF flat", "**TCF** *(", "**TCF** *("),
                              ("TCF+nature", "**TCF + CPF nature** *(", "**TCF + nature CPF** *(")):
        check(f"paridade {rot}", bytes_afirmados(READ, mk_en), bytes_afirmados(PT, mk_pt))
    res["G6"] = "ok" if not falhas else "ver falhas"

    (AQUI / "resultado.json").write_text(
        json.dumps({"resultados": res, "falhas": falhas}, ensure_ascii=False, indent=1),
        encoding="utf-8", newline="")

    achados = {q.resolve() for p in (IN, OUT) for q in p.rglob("*") if q.is_file()}
    assert not (_arquivos - achados) and not (achados - _arquivos), "portao anti-orfao"
    print()
    print("=" * 92)
    print(f"-> {len(achados)} arquivos gravados, portao anti-orfao verde")
    print(f"-> DIVERGENCIAS: {len(falhas)}")
    for f in falhas:
        print(f"   - {f}")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
