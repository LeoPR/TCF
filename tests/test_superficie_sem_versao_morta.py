"""A superfície carrega só o presente: nenhum wire morto na documentação de leitura.

Invariante I1 do `AGENTS.md`. O owner precisou apontar o mesmo defeito três vezes (a última
em 2026-08-31, um `#TCF.7` no `datasets/coverage-matrix.md`), então ele vira teste em vez de
disciplina.

A regra: a **versão vigente do wire sai do código**, não de uma constante escrita aqui. No dia
em que o formato virar `.9`, este teste passa a recusar `#TCF.8` sozinho, sem ninguém editar
nada. É a mesma ideia do verificador de snippets: o documento tem de acompanhar o código.

**O que NÃO é varrido**, e por quê:
  - `docs/adr/`: ADR aceito nunca é editado (AGENTS §"o que não se apaga");
  - `docs/archive/`, `docs/findings/`, `docs/workbench/`, `experiments/`, `old/`: traço,
    append-only, e é onde a versão antiga é o assunto;
  - `CHANGELOG.md`: registrar a história é a função dele;
  - `src/`: o decoder precisa nomear o que ele recusa, e I5 proíbe mexer sem aprovação;
  - `tickets/`: um ticket sobre remover legado tem de poder nomear o legado;
  - `tests/`: este arquivo, entre outros, cita as grafias de propósito.

Onde nomear o wire morto é a **função** da linha (a lista de "não usar" do vocabulário, e a
linha da spec que documenta o erro nomeado), a linha carrega o marcador
`<!-- legado-ok: motivo -->`.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tcf.view import MAGIC_MULTI_V3  # noqa: E402

# a versão vigente, lida do código: '#TCF.8M' -> 8
VIGENTE = int(re.search(rb"#TCF\.(\d+)", MAGIC_MULTI_V3).group(1))

# qualquer `#TCF.<n>` com n < vigente é wire morto
MORTO = re.compile(r"#TCF\.(\d+)")
MARCADOR_OK = "legado-ok:"

SUPERFICIE = [
    "README.md", "README.pt-BR.md", "README.pypi.md", "MAP.md", "INDEX.md",
    "ROADMAP.md", "STATUS.md", "CONTRIBUTING.md", "CONTRIBUTING.pt-BR.md",
    "docs", "datasets",
]
FORA = {"adr", "archive", "findings", "workbench", "_archive"}


def _paginas() -> list[Path]:
    fora: list[Path] = []
    for alvo in SUPERFICIE:
        p = ROOT / alvo
        if p.is_file():
            fora.append(p)
            continue
        if not p.is_dir():
            continue
        for f in sorted(p.rglob("*.md")):
            if FORA & set(x.name for x in f.parents):
                continue
            fora.append(f)
    return fora


@pytest.mark.parametrize("pagina", _paginas(), ids=lambda p: p.relative_to(ROOT).as_posix())
def test_pagina_nao_cita_wire_morto(pagina: Path):
    """O marcador cobre o parágrafo que ele abre, até a próxima linha em branco.

    É como o markdown se escreve: o comentário vem antes do bloco que ele qualifica, e o
    bloco acaba na linha vazia.
    """
    ruins = []
    marcado = False
    for i, ln in enumerate(pagina.read_text(encoding="utf-8").splitlines(), 1):
        if MARCADOR_OK in ln:
            marcado = True
            continue
        if not ln.strip():
            marcado = False
            continue
        if marcado:
            continue
        for n in MORTO.findall(ln):
            if int(n) < VIGENTE:
                ruins.append(f"    linha {i}: {ln.strip()[:100]}")
                break
    assert not ruins, (
        f"{pagina.relative_to(ROOT).as_posix()} cita wire anterior ao `#TCF.{VIGENTE}`, que "
        f"hoje só existe no git:\n" + "\n".join(ruins) + "\n"
        "  Reveja: refaça a medição sob o formato vigente, apague, ou (se nomear o morto for "
        "a função da linha) marque com `<!-- legado-ok: motivo -->`."
    )


def test_a_varredura_encontra_o_que_deveria():
    """Se o extrator quebrar, ele passa vazio e mente."""
    assert VIGENTE >= 8, f"versao vigente lida do codigo veio {VIGENTE!r}"
    assert len(_paginas()) >= 30, f"so' {len(_paginas())} paginas varridas; a lista encolheu?"
