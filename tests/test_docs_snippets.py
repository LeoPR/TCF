"""Executa os exemplos da documentação, para que nenhum quebre sem alguém saber.

Motivo (2026-08-31): uma varredura manual achou 16 blocos que não rodavam como estavam
escritos, incluindo uma página de referência com 6 de 8 blocos quebrados nos dois idiomas.
Nada no repo pegava isso, embora `T-DOC-L10N-REFERENCE` já liste "o verificador de snippets
segue em 0 falhas" como critério de aceite.

Como funciona, e por que assim:

- **um namespace por PÁGINA, na ordem da página.** As páginas do repo são escritas como o
  guia do polars: um dataset declarado no topo e reusado nos blocos seguintes. Rodar bloco a
  bloco isolado reprovaria a boa prática em vez de proteger contra o defeito.
- **cwd temporário.** Um exemplo que escreve arquivo não suja a árvore, e um que lê arquivo
  falha alto em vez de encontrar um resto de outra execução.
- **opt-out explícito**, com o marcador `<!-- doctest: skip -->` na linha anterior à cerca,
  para o bloco que é pseudo-código por design: assinatura, template com `...`, ou o erro
  demonstrado de propósito. O marcador `<!-- doctest: raises -->` diz que o bloco DEVE
  levantar, e ele falha se rodar limpo.

Cobre a superfície didática (tutoriais, receitas, referência e os READMEs). Não cobre
`docs/theory/`, `docs/adr/` nem `docs/archive/`: lá o código é ilustração de argumento, e
vários trechos descrevem código que não existe mais, de propósito.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# a superfície didática: o que um usuário lê para aprender a usar
PAGINAS_DIDATICAS = [
    "README.md",
    "README.pt-BR.md",
    "README.pypi.md",
    "docs/tutorials",
    "docs/how-to",
    "docs/reference",
]

CERCA = re.compile(r"^(?P<indent> *)```(?P<lang>[A-Za-z0-9+-]*)\s*$")
MARCADOR = re.compile(r"<!--\s*doctest:\s*(?P<acao>skip|raises)\s*-->")


class Bloco:
    __slots__ = ("pagina", "linha", "codigo", "acao")

    def __init__(self, pagina: Path, linha: int, codigo: str, acao: str | None):
        self.pagina, self.linha, self.codigo, self.acao = pagina, linha, codigo, acao

    def __repr__(self) -> str:  # o id do caso de teste, clicável
        return f"{self.pagina.as_posix()}:{self.linha}"


def _paginas() -> list[Path]:
    fora: list[Path] = []
    for alvo in PAGINAS_DIDATICAS:
        p = ROOT / alvo
        if p.is_file():
            fora.append(p)
        elif p.is_dir():
            fora.extend(sorted(p.rglob("*.md")))
    return fora


def _blocos(pagina: Path) -> list[Bloco]:
    """Os blocos ```python da página, na ordem, com o marcador que os precede."""
    linhas = pagina.read_text(encoding="utf-8").splitlines()
    fora: list[Bloco] = []
    i = 0
    while i < len(linhas):
        m = CERCA.match(linhas[i])
        if not m:
            i += 1
            continue
        lang, indent = m.group("lang").lower(), m.group("indent")
        # o marcador vive na linha anterior não vazia
        acao = None
        j = i - 1
        while j >= 0 and not linhas[j].strip():
            j -= 1
        if j >= 0:
            mm = MARCADOR.search(linhas[j])
            if mm:
                acao = mm.group("acao")
        corpo: list[str] = []
        i += 1
        while i < len(linhas) and not CERCA.match(linhas[i]):
            corpo.append(linhas[i][len(indent):] if linhas[i].startswith(indent)
                         else linhas[i])
            i += 1
        i += 1  # a cerca de fechamento
        if lang in ("python", "py"):
            fora.append(Bloco(pagina, i - len(corpo) - 1, "\n".join(corpo), acao))
    return fora


def _casos() -> list[Bloco]:
    return [b for p in _paginas() for b in _blocos(p)]


TODOS = _casos()
POR_PAGINA: dict[Path, list[Bloco]] = {}
for _b in TODOS:
    POR_PAGINA.setdefault(_b.pagina, []).append(_b)


@pytest.mark.parametrize(
    "pagina", sorted(POR_PAGINA, key=lambda p: p.as_posix()),
    ids=lambda p: p.relative_to(ROOT).as_posix(),
)
def test_exemplos_da_pagina_rodam(pagina: Path, tmp_path: Path, monkeypatch):
    """Roda os blocos da página em ordem, num namespace e num cwd só dela."""
    monkeypatch.chdir(tmp_path)
    ns: dict = {"__name__": "__doc_snippet__"}
    for bloco in POR_PAGINA[pagina]:
        if bloco.acao == "skip":
            continue
        try:
            exec(compile(bloco.codigo, str(bloco), "exec"), ns)  # noqa: S102
        except Exception as e:  # noqa: BLE001
            if bloco.acao == "raises":
                continue
            pytest.fail(
                f"{bloco} não roda como está escrito na documentação\n"
                f"  {type(e).__name__}: {e}\n"
                f"  Conserte o exemplo, ou marque o bloco com "
                f"`<!-- doctest: skip -->` se ele for pseudo-código por design."
            )
        else:
            if bloco.acao == "raises":
                pytest.fail(f"{bloco} está marcado `doctest: raises` e rodou sem erro")


@pytest.mark.parametrize(
    "pagina", sorted(_paginas(), key=lambda p: p.as_posix()),
    ids=lambda p: p.relative_to(ROOT).as_posix(),
)
def test_crases_pareadas_fora_dos_blocos(pagina: Path):
    """Crase ímpar em prosa engole o texto até a próxima, e some com o exemplo.

    Aconteceu duas vezes: um `\\n` virou quebra de linha literal dentro de código inline, e
    uma conjugação escrita com crase no meio da palavra deixou quatro linhas desbalanceadas.
    """
    ruins = []
    dentro = False
    for i, ln in enumerate(pagina.read_text(encoding="utf-8").splitlines(), 1):
        if ln.strip().startswith("```"):
            dentro = not dentro
            continue
        if not dentro and ln.count("`") % 2:
            ruins.append(f"    linha {i}: {ln.strip()[:90]}")
    assert not ruins, (
        f"{pagina.relative_to(ROOT).as_posix()} tem crase ímpar fora de bloco de código:\n"
        + "\n".join(ruins)
    )


def test_a_varredura_encontra_o_que_deveria():
    """Guarda do próprio verificador: se o extrator quebrar, ele passa vazio e mente."""
    assert len(_paginas()) >= 20, "a lista de páginas didáticas encolheu"
    assert len(TODOS) >= 80, f"só {len(TODOS)} blocos python encontrados; o extrator quebrou?"
    tutorial = ROOT / "docs" / "tutorials" / "getting-started.md"
    assert tutorial in POR_PAGINA, "o tutorial saiu da varredura"
